from __future__ import annotations
import csv
import io
import json
import os
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.audit import audit_log
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.ai.groq_client import GroqClient, GroqCompletionRequest

_settings = get_settings()


def _ensure_export_dir() -> Path:
    p = Path(_settings.REPORTS_EXPORT_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _insert_report(db: Session, rtype: str, params: Dict[str, Any], file_url: str) -> int:
    res = db.execute(
        text(
            """
            INSERT INTO reports (type, params, file_url)
            VALUES (:type, CAST(:params AS JSONB), :file_url)
            RETURNING id
            """
        ),
        {"type": rtype, "params": json.dumps(params), "file_url": file_url},
    )
    rid = res.scalar_one()
    db.commit()
    audit_log("REPORT_GENERATE", "reports", rid, data={"type": rtype, "params": params, "file_url": file_url})
    return int(rid)


def _update_report_insights(db: Session, report_id: int, insights: Dict[str, Any]) -> None:
    db.execute(
        text("UPDATE reports SET insights_json = :ins WHERE id = :id"),
        {"ins": json.dumps(insights), "id": report_id},
    )
    db.commit()


def _generate_ai_insights(metrics: Dict[str, Any], report_type: str) -> Dict[str, Any]:
    if not _settings.AI_REPORTS_ENABLED:
        return {}
    try:
        client = GroqClient()
        prompt = (
            "Analyze this {rtype} report and respond with JSON only with keys: "
            "summary (2-3 sentences), anomalies (array), forecast (object). Data: \n".format(rtype=report_type)
            + json.dumps(metrics, indent=2)
        )
        text_resp = client.complete(
            GroqCompletionRequest(prompt=prompt, temperature=0.2, max_tokens=500)
        )
        try:
            data = json.loads(text_resp)
            audit_log("REPORT_AI_SUMMARY", "reports", None, data={"ok": True})
            return data
        except Exception:
            audit_log("REPORT_AI_SUMMARY", "reports", None, data={"ok": False, "raw": text_resp[:500]})
            return {"summary": text_resp, "anomalies": [], "forecast": {}}
    except Exception as e:  # GROQ not configured or failed
        audit_log("REPORT_AI_SUMMARY", "reports", None, data={"ok": False, "error": str(e)})
        return {}


def _write_csv(rows: list[dict[str, Any]], filename: str) -> str:
    export_dir = _ensure_export_dir()
    path = export_dir / filename
    if not rows:
        # ensure at least headerless file
        path.write_text("")
        return str(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    return str(path)


def _zip_files(file_paths: list[str], zip_name: str) -> str:
    export_dir = _ensure_export_dir()
    zip_path = export_dir / zip_name
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for fp in file_paths:
            zf.write(fp, arcname=os.path.basename(fp))
    return str(zip_path)


def query_daily_sales_for_date(db: Session, run_date: date) -> Tuple[Dict[str, Any], list[dict[str, Any]]]:
    # Aggregate row
    agg = db.execute(
        text(
            "SELECT * FROM mv_daily_sales WHERE sales_date = :d"
        ),
        {"d": run_date},
    ).mappings().all()

    # By product
    by_prod = db.execute(
        text(
            "SELECT * FROM mv_daily_sales_by_product WHERE sales_date = :d ORDER BY product_id"
        ),
        {"d": run_date},
    ).mappings().all()

    metrics = agg[0] if agg else {}
    return dict(metrics), [dict(r) for r in by_prod]


def query_monthly_audit_for_month(db: Session, month: date) -> Dict[str, Any]:
    row = db.execute(
        text("SELECT * FROM mv_monthly_audit WHERE month = :m"),
        {"m": month.replace(day=1)},
    ).mappings().first()
    return dict(row) if row else {}


def build_daily_sales_report(run_date: date) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        agg, by_prod = query_daily_sales_for_date(db, run_date)
        # Export
        file_name = f"daily_sales_{run_date.isoformat()}.csv"
        file_url = _write_csv([agg] if agg else [], file_name)
        # Insert report
        report_id = _insert_report(db, "daily_sales", {"date": run_date.isoformat()}, file_url)
        # AI insights
        insights = _generate_ai_insights({"aggregate": agg, "by_product": by_prod}, "daily_sales")
        if insights:
            _update_report_insights(db, report_id, insights)
        return {"report_id": report_id, "file_url": file_url}
    finally:
        db.close()


def build_monthly_audit_report(month: date) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        metrics = query_monthly_audit_for_month(db, month)
        # Export: write metrics JSON and CSV in a zip
        csv_path = _write_csv([metrics] if metrics else [], f"monthly_audit_{month.strftime('%Y-%m')}.csv")
        json_path = _ensure_export_dir() / f"monthly_audit_{month.strftime('%Y-%m')}.json"
        json_path.write_text(json.dumps(metrics, indent=2))
        zip_url = _zip_files([csv_path, str(json_path)], f"monthly_audit_{month.strftime('%Y-%m')}.zip")
        report_id = _insert_report(db, "monthly_audit", {"month": month.strftime('%Y-%m')}, zip_url)
        insights = _generate_ai_insights(metrics, "monthly_audit")
        if insights:
            _update_report_insights(db, report_id, insights)
        return {"report_id": report_id, "file_url": zip_url}
    finally:
        db.close()
