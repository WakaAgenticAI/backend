"""Tests for reports_service.py — query functions, build functions, insert/update."""
from __future__ import annotations
import json
import os
import pytest
from datetime import date
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.services.reports_service import (
    _ensure_export_dir,
    _write_csv,
    _zip_files,
    _generate_ai_insights,
    _insert_report,
    _update_report_insights,
    query_daily_sales_for_date,
    query_monthly_audit_for_month,
    build_daily_sales_report,
    build_monthly_audit_report,
)


# ── _insert_report ───────────────────────────────────────────

def test_insert_report():
    mock_db = MagicMock()
    mock_db.execute.return_value.scalar_one.return_value = 42

    with patch("app.services.reports_service.audit_log"):
        rid = _insert_report(mock_db, "daily_sales", {"date": "2025-01-01"}, "/exports/test.csv")
        assert rid == 42
        mock_db.commit.assert_called_once()


# ── _update_report_insights ──────────────────────────────────

def test_update_report_insights():
    mock_db = MagicMock()
    _update_report_insights(mock_db, 42, {"summary": "Good day"})
    mock_db.execute.assert_called_once()
    mock_db.commit.assert_called_once()


# ── query_daily_sales_for_date ───────────────────────────────

def test_query_daily_sales_with_data():
    mock_db = MagicMock()
    mock_agg = MagicMock()
    mock_agg.mappings.return_value.all.return_value = [{"total": 1000, "count": 5}]
    mock_prod = MagicMock()
    mock_prod.mappings.return_value.all.return_value = [
        {"product_id": 1, "total": 500},
        {"product_id": 2, "total": 500},
    ]
    mock_db.execute.side_effect = [mock_agg, mock_prod]

    metrics, by_prod = query_daily_sales_for_date(mock_db, date(2025, 1, 15))
    assert metrics["total"] == 1000
    assert len(by_prod) == 2


def test_query_daily_sales_empty():
    mock_db = MagicMock()
    mock_agg = MagicMock()
    mock_agg.mappings.return_value.all.return_value = []
    mock_prod = MagicMock()
    mock_prod.mappings.return_value.all.return_value = []
    mock_db.execute.side_effect = [mock_agg, mock_prod]

    metrics, by_prod = query_daily_sales_for_date(mock_db, date(2025, 1, 15))
    assert metrics == {}
    assert by_prod == []


# ── query_monthly_audit_for_month ────────────────────────────

def test_query_monthly_audit_with_data():
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.mappings.return_value.first.return_value = {"month": "2025-01", "revenue": 50000}
    mock_db.execute.return_value = mock_result

    result = query_monthly_audit_for_month(mock_db, date(2025, 1, 1))
    assert result["revenue"] == 50000


def test_query_monthly_audit_empty():
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.mappings.return_value.first.return_value = None
    mock_db.execute.return_value = mock_result

    result = query_monthly_audit_for_month(mock_db, date(2025, 1, 1))
    assert result == {}


# ── build_daily_sales_report ─────────────────────────────────

def test_build_daily_sales_report(tmp_path):
    mock_db = MagicMock()
    mock_agg = MagicMock()
    mock_agg.mappings.return_value.all.return_value = [{"total": 1000}]
    mock_prod = MagicMock()
    mock_prod.mappings.return_value.all.return_value = []
    mock_db.execute.side_effect = [mock_agg, mock_prod, MagicMock(scalar_one=MagicMock(return_value=1))]
    mock_db.execute.return_value.scalar_one.return_value = 1

    mock_settings = MagicMock()
    mock_settings.REPORTS_EXPORT_DIR = str(tmp_path)
    mock_settings.AI_REPORTS_ENABLED = False

    with patch("app.services.reports_service.SessionLocal", return_value=mock_db), \
         patch("app.services.reports_service._settings", mock_settings), \
         patch("app.services.reports_service.query_daily_sales_for_date", return_value=({"total": 1000}, [])), \
         patch("app.services.reports_service._insert_report", return_value=1), \
         patch("app.services.reports_service._generate_ai_insights", return_value={}), \
         patch("app.services.reports_service.audit_log"):
        result = build_daily_sales_report(date(2025, 1, 15))
        assert "report_id" in result
        assert "file_url" in result


# ── build_monthly_audit_report ───────────────────────────────

def test_build_monthly_audit_report(tmp_path):
    mock_db = MagicMock()

    mock_settings = MagicMock()
    mock_settings.REPORTS_EXPORT_DIR = str(tmp_path)
    mock_settings.AI_REPORTS_ENABLED = False

    with patch("app.services.reports_service.SessionLocal", return_value=mock_db), \
         patch("app.services.reports_service._settings", mock_settings), \
         patch("app.services.reports_service.query_monthly_audit_for_month", return_value={"revenue": 50000}), \
         patch("app.services.reports_service._insert_report", return_value=2), \
         patch("app.services.reports_service._generate_ai_insights", return_value={}), \
         patch("app.services.reports_service.audit_log"):
        result = build_monthly_audit_report(date(2025, 1, 1))
        assert "report_id" in result
        assert "file_url" in result


def test_build_monthly_audit_report_with_insights(tmp_path):
    mock_db = MagicMock()

    mock_settings = MagicMock()
    mock_settings.REPORTS_EXPORT_DIR = str(tmp_path)
    mock_settings.AI_REPORTS_ENABLED = True

    insights = {"summary": "Good month", "anomalies": [], "forecast": {}}

    with patch("app.services.reports_service.SessionLocal", return_value=mock_db), \
         patch("app.services.reports_service._settings", mock_settings), \
         patch("app.services.reports_service.query_monthly_audit_for_month", return_value={"revenue": 50000}), \
         patch("app.services.reports_service._insert_report", return_value=3), \
         patch("app.services.reports_service._generate_ai_insights", return_value=insights), \
         patch("app.services.reports_service._update_report_insights") as mock_update, \
         patch("app.services.reports_service.audit_log"):
        result = build_monthly_audit_report(date(2025, 2, 1))
        mock_update.assert_called_once_with(mock_db, 3, insights)
