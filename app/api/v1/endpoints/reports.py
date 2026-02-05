from __future__ import annotations
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.deps import require_roles
from app.db.session import get_db
from app.jobs.reports_tasks import task_build_daily_sales, task_build_monthly_audit

router = APIRouter()


@router.post("/admin/reports/daily-sales", tags=["reports"]) 
def trigger_daily_sales(
    run_date: str | None = None,
    _user=Depends(require_roles("Admin", "Finance")),
) -> dict[str, Any]:
    """Trigger daily sales report build. Returns Celery task id and accepted params."""
    if run_date:
        try:
            date.fromisoformat(run_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="run_date must be YYYY-MM-DD")
    async_result = task_build_daily_sales.delay(run_date)
    return {"task_id": async_result.id, "run_date": run_date}


@router.post("/admin/reports/monthly-audit", tags=["reports"]) 
def trigger_monthly_audit(
    month: str | None = None,
    _user=Depends(require_roles("Admin", "Finance")),
) -> dict[str, Any]:
    """Trigger monthly audit report build. Returns Celery task id and accepted params."""
    if month:
        try:
            datetime.strptime(month + "-01", "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="month must be YYYY-MM")
    async_result = task_build_monthly_audit.delay(month)
    return {"task_id": async_result.id, "month": month}


@router.get("/reports/{report_id}", tags=["reports"]) 
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_roles("Admin", "Finance")),
) -> dict[str, Any]:
    row = db.execute(
        text("SELECT id, type, params, file_url, insights_json, created_at FROM reports WHERE id=:id"),
        {"id": report_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    return dict(row)


@router.get("/admin/reports/daily-sales/latest", tags=["reports"]) 
def get_latest_daily_sales(
    db: Session = Depends(get_db),
    _user=Depends(require_roles("Admin", "Finance")),
) -> dict[str, Any]:
    row = db.execute(
        text("SELECT * FROM reports WHERE type='daily_sales' ORDER BY created_at DESC LIMIT 1"),
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="No daily sales report yet")
    return dict(row)


@router.get("/admin/reports/monthly-audit/latest", tags=["reports"]) 
def get_latest_monthly_audit(
    db: Session = Depends(get_db),
    _user=Depends(require_roles("Admin", "Finance")),
) -> dict[str, Any]:
    row = db.execute(
        text("SELECT * FROM reports WHERE type='monthly_audit' ORDER BY created_at DESC LIMIT 1"),
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="No monthly audit report yet")
    return dict(row)


@router.get("/admin/reports/sales", tags=["reports"])
def get_sales_report(
    period: str,
    db: Session = Depends(get_db),
    _user=Depends(require_roles("Admin", "Finance")),
) -> dict[str, Any]:
    """
    Get sales report for a specific period (YYYY-MM format).
    Returns report data or triggers async generation if not available.
    """
    # Validate period format
    try:
        datetime.strptime(period + "-01", "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="period must be YYYY-MM format")
    
    # Check if report exists for this period
    row = db.execute(
        text("SELECT * FROM reports WHERE type='daily_sales' AND params LIKE :period ORDER BY created_at DESC LIMIT 1"),
        {"period": f"%{period}%"}
    ).mappings().first()
    
    if row:
        return {
            "status": "completed",
            "report_id": row["id"],
            "period": period,
            "file_url": row.get("file_url"),
            "insights": row.get("insights_json"),
            "created_at": row["created_at"].isoformat() if row.get("created_at") else None
        }
    
    # If no report exists, trigger async generation
    async_result = task_build_daily_sales.delay(period)
    return {
        "status": "processing",
        "task_id": async_result.id,
        "period": period,
        "message": f"Report generation started for period {period}"
    }
