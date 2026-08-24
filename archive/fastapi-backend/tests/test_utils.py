"""Tests for app/utils/helpers.py and app/utils/tools_path.py."""
from __future__ import annotations
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.utils.helpers import utc_now_iso
from app.utils.tools_path import get_tools_dir, require_tools_dir


# ── utc_now_iso ──────────────────────────────────────────────

def test_utc_now_iso_format():
    result = utc_now_iso()
    assert result.endswith("Z")
    # Should be parseable as ISO8601
    ts = result.rstrip("Z")
    dt = datetime.fromisoformat(ts)
    assert isinstance(dt, datetime)


def test_utc_now_iso_recent():
    result = utc_now_iso()
    ts = result.rstrip("Z")
    dt = datetime.fromisoformat(ts)
    now = datetime.utcnow()
    diff = abs((now - dt).total_seconds())
    assert diff < 5  # within 5 seconds


# ── get_tools_dir ────────────────────────────────────────────

def test_get_tools_dir_explicit_absolute(tmp_path):
    p = get_tools_dir(explicit=str(tmp_path / "my_tools"))
    assert p == (tmp_path / "my_tools").resolve()


def test_get_tools_dir_explicit_relative():
    p = get_tools_dir(explicit="relative/tools")
    assert p.is_absolute()
    assert str(p).endswith("relative/tools")


def test_get_tools_dir_from_settings():
    mock_settings = MagicMock()
    mock_settings.TOOLS_DIR = "/custom/tools"
    with patch("app.utils.tools_path.get_settings", return_value=mock_settings):
        p = get_tools_dir()
        assert str(p) == "/custom/tools"


def test_get_tools_dir_settings_relative():
    mock_settings = MagicMock()
    mock_settings.TOOLS_DIR = "tools"
    with patch("app.utils.tools_path.get_settings", return_value=mock_settings):
        p = get_tools_dir()
        assert p.is_absolute()
        assert str(p).endswith("tools")


def test_get_tools_dir_fallback():
    mock_settings = MagicMock()
    mock_settings.TOOLS_DIR = ""
    with patch("app.utils.tools_path.get_settings", return_value=mock_settings):
        p = get_tools_dir()
        assert p.is_absolute()
        assert "tools" in str(p)


# ── require_tools_dir ────────────────────────────────────────

def test_require_tools_dir_exists(tmp_path):
    tools = tmp_path / "tools"
    tools.mkdir()
    with patch("app.utils.tools_path.get_tools_dir", return_value=tools):
        result = require_tools_dir()
        assert result == tools


def test_require_tools_dir_not_exists(tmp_path):
    missing = tmp_path / "nonexistent_tools"
    with patch("app.utils.tools_path.get_tools_dir", return_value=missing):
        with pytest.raises(FileNotFoundError, match="tools directory not found"):
            require_tools_dir()
