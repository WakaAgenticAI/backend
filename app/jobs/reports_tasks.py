from __future__ import annotations
from datetime import date, datetime

from app.celery_app import celery_app
from app.services.reports_service import build_daily_sales_report, build_monthly_audit_report


@celery_app.task(name="reports.build_daily_sales")
def task_build_daily_sales(run_date_str: str | None = None) -> dict:
    """Build daily sales report for a given date (YYYY-MM-DD). Defaults to today (UTC)."""
    run_date = (
        date.fromisoformat(run_date_str) if run_date_str else datetime.utcnow().date()
    )
    return build_daily_sales_report(run_date)


@celery_app.task(name="reports.build_monthly_audit")
def task_build_monthly_audit(month_str: str | None = None) -> dict:
    """Build monthly audit report for a given month (YYYY-MM). Defaults to current month (UTC)."""
    if month_str:
        d = date.fromisoformat(month_str + "-01")
    else:
        today = datetime.utcnow().date()
        d = today.replace(day=1)
    return build_monthly_audit_report(d)
