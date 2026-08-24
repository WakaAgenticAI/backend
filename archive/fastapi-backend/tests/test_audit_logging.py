"""Tests for app/core/audit.py and app/core/logging.py."""
from __future__ import annotations
import json
import logging
import pytest
from unittest.mock import patch, MagicMock

from app.core.audit import audit_log
from app.core.logging import JsonFormatter, setup_json_logging


# ── JsonFormatter ────────────────────────────────────────────

def test_json_formatter_basic():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="hello", args=(), exc_info=None,
    )
    output = formatter.format(record)
    data = json.loads(output)
    assert data["level"] == "INFO"
    assert data["logger"] == "test"
    assert data["msg"] == "hello"
    assert "time" in data


def test_json_formatter_with_extras():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="audit", args=(), exc_info=None,
    )
    record.request_id = "req-123"
    record.path = "/api/v1/orders"
    record.method = "POST"
    record.action = "ORDER_CREATE"
    record.entity = "orders"
    record.entity_id = "42"
    record.data = {"total": 1000}
    record.actor_id = 1

    output = formatter.format(record)
    data = json.loads(output)
    assert data["request_id"] == "req-123"
    assert data["path"] == "/api/v1/orders"
    assert data["method"] == "POST"
    assert data["action"] == "ORDER_CREATE"
    assert data["entity"] == "orders"
    assert data["entity_id"] == "42"
    assert data["data"]["total"] == 1000
    assert data["actor_id"] == 1


def test_json_formatter_no_extras():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test", level=logging.WARNING, pathname="", lineno=0,
        msg="warning msg", args=(), exc_info=None,
    )
    output = formatter.format(record)
    data = json.loads(output)
    assert "request_id" not in data
    assert data["level"] == "WARNING"


# ── setup_json_logging ───────────────────────────────────────

def test_setup_json_logging():
    setup_json_logging()
    root = logging.getLogger()
    assert len(root.handlers) >= 1
    # The handler should use JsonFormatter
    has_json = any(isinstance(h.formatter, JsonFormatter) for h in root.handlers)
    assert has_json

    audit = logging.getLogger("audit")
    assert audit.level == logging.INFO


def test_setup_json_logging_idempotent():
    """Calling setup twice should not double handlers."""
    setup_json_logging()
    count1 = len(logging.getLogger().handlers)
    setup_json_logging()
    count2 = len(logging.getLogger().handlers)
    assert count2 == count1


# ── audit_log ────────────────────────────────────────────────

def test_audit_log_basic():
    """audit_log should not raise even with DB issues."""
    audit_log("TEST_ACTION", "test_entity", entity_id=1, actor_id=10, data={"key": "val"})


def test_audit_log_no_entity_id():
    audit_log("TEST_ACTION", "test_entity")


def test_audit_log_string_entity_id():
    audit_log("TEST_ACTION", "test_entity", entity_id="abc-123")


def test_audit_log_with_data():
    audit_log("TEST_ACTION", "test_entity", data={"complex": {"nested": True}})


def test_audit_log_db_error_swallowed():
    """Even if DB fails, audit_log should not raise."""
    with patch("app.core.audit.SessionLocal", side_effect=Exception("DB down")):
        # Should not raise
        audit_log("TEST_ACTION", "test_entity", entity_id=1)


def test_audit_log_logger_error_swallowed():
    """Even if logger fails, audit_log should not raise."""
    with patch("app.core.audit._audit_logger") as mock_logger:
        mock_logger.info.side_effect = Exception("logger broken")
        # Should not raise
        audit_log("TEST_ACTION", "test_entity")
