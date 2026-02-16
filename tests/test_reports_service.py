"""Comprehensive tests for app/services/reports_service.py."""
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
)


# ── _ensure_export_dir ───────────────────────────────────────

def test_ensure_export_dir_creates(tmp_path):
    target = tmp_path / "exports"
    mock_settings = MagicMock()
    mock_settings.REPORTS_EXPORT_DIR = str(target)
    with patch("app.services.reports_service._settings", mock_settings):
        result = _ensure_export_dir()
        assert result.exists()
        assert result == target


def test_ensure_export_dir_already_exists(tmp_path):
    target = tmp_path / "exports"
    target.mkdir()
    mock_settings = MagicMock()
    mock_settings.REPORTS_EXPORT_DIR = str(target)
    with patch("app.services.reports_service._settings", mock_settings):
        result = _ensure_export_dir()
        assert result.exists()


# ── _write_csv ───────────────────────────────────────────────

def test_write_csv_with_data(tmp_path):
    mock_settings = MagicMock()
    mock_settings.REPORTS_EXPORT_DIR = str(tmp_path)
    with patch("app.services.reports_service._settings", mock_settings):
        rows = [
            {"name": "Apple", "qty": 10, "price": 200},
            {"name": "Bread", "qty": 5, "price": 850},
        ]
        path = _write_csv(rows, "test_report.csv")
        assert os.path.exists(path)
        content = open(path).read()
        assert "Apple" in content
        assert "Bread" in content
        assert "name,qty,price" in content


def test_write_csv_empty_rows(tmp_path):
    mock_settings = MagicMock()
    mock_settings.REPORTS_EXPORT_DIR = str(tmp_path)
    with patch("app.services.reports_service._settings", mock_settings):
        path = _write_csv([], "empty.csv")
        assert os.path.exists(path)
        content = open(path).read()
        assert content == ""


# ── _zip_files ───────────────────────────────────────────────

def test_zip_files(tmp_path):
    # Create some files to zip
    f1 = tmp_path / "file1.csv"
    f1.write_text("a,b\n1,2")
    f2 = tmp_path / "file2.json"
    f2.write_text('{"key": "val"}')

    mock_settings = MagicMock()
    mock_settings.REPORTS_EXPORT_DIR = str(tmp_path)
    with patch("app.services.reports_service._settings", mock_settings):
        zip_path = _zip_files([str(f1), str(f2)], "archive.zip")
        assert os.path.exists(zip_path)
        assert zip_path.endswith(".zip")

        import zipfile
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            assert "file1.csv" in names
            assert "file2.json" in names


# ── _generate_ai_insights ────────────────────────────────────

def test_generate_ai_insights_disabled():
    mock_settings = MagicMock()
    mock_settings.AI_REPORTS_ENABLED = False
    with patch("app.services.reports_service._settings", mock_settings):
        result = _generate_ai_insights({"total": 1000}, "daily_sales")
        assert result == {}


def test_generate_ai_insights_groq_returns_json():
    mock_settings = MagicMock()
    mock_settings.AI_REPORTS_ENABLED = True
    mock_groq = MagicMock()
    mock_groq.complete.return_value = json.dumps({
        "summary": "Sales are up",
        "anomalies": [],
        "forecast": {"next_week": 1200},
    })

    with patch("app.services.reports_service._settings", mock_settings), \
         patch("app.services.reports_service.GroqClient", return_value=mock_groq), \
         patch("app.services.reports_service.audit_log"):
        result = _generate_ai_insights({"total": 1000}, "daily_sales")
        assert result["summary"] == "Sales are up"
        assert result["anomalies"] == []


def test_generate_ai_insights_groq_returns_text():
    mock_settings = MagicMock()
    mock_settings.AI_REPORTS_ENABLED = True
    mock_groq = MagicMock()
    mock_groq.complete.return_value = "Plain text summary of the report"

    with patch("app.services.reports_service._settings", mock_settings), \
         patch("app.services.reports_service.GroqClient", return_value=mock_groq), \
         patch("app.services.reports_service.audit_log"):
        result = _generate_ai_insights({"total": 1000}, "daily_sales")
        assert result["summary"] == "Plain text summary of the report"
        assert result["anomalies"] == []


def test_generate_ai_insights_groq_exception():
    mock_settings = MagicMock()
    mock_settings.AI_REPORTS_ENABLED = True

    with patch("app.services.reports_service._settings", mock_settings), \
         patch("app.services.reports_service.GroqClient", side_effect=Exception("API down")), \
         patch("app.services.reports_service.audit_log"):
        result = _generate_ai_insights({"total": 1000}, "daily_sales")
        assert result == {}
