"""Tests for app/schemas/common.py and other schema modules."""
from __future__ import annotations
from datetime import datetime

from app.schemas.common import StatusResponse, PageMeta


def test_status_response_defaults():
    sr = StatusResponse()
    assert sr.status == "ok"
    assert isinstance(sr.timestamp, datetime)


def test_status_response_custom():
    sr = StatusResponse(status="error")
    assert sr.status == "error"


def test_page_meta_defaults():
    pm = PageMeta()
    assert pm.page == 1
    assert pm.size == 20
    assert pm.total == 0


def test_page_meta_custom():
    pm = PageMeta(page=3, size=50, total=200)
    assert pm.page == 3
    assert pm.size == 50
    assert pm.total == 200
