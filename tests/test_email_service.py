"""Comprehensive tests for app/services/email_service.py."""
from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.email_service import EmailService, get_email_service


def _make_service(api_key="re_test_key", to="admin@example.com", enabled=True):
    """Create an EmailService with mocked settings."""
    mock_settings = MagicMock()
    mock_settings.RESEND_API_KEY = api_key
    mock_settings.ALERT_EMAIL_FROM = "WakaAgent AI <alerts@resend.dev>"
    mock_settings.ALERT_EMAIL_TO = to
    mock_settings.EMAIL_NOTIFICATIONS_ENABLED = enabled
    with patch("app.services.email_service.get_settings", return_value=mock_settings):
        return EmailService()


# ── Init ─────────────────────────────────────────────────────

def test_init_enabled():
    svc = _make_service()
    assert svc.enabled is True
    assert svc.api_key == "re_test_key"
    assert svc.to_addresses == ["admin@example.com"]


def test_init_disabled_no_key():
    svc = _make_service(api_key="")
    assert svc.enabled is False


def test_init_disabled_no_recipients():
    svc = _make_service(to="")
    assert svc.enabled is False


def test_init_disabled_flag():
    svc = _make_service(enabled=False)
    assert svc.enabled is False


def test_init_multiple_recipients():
    svc = _make_service(to="a@test.com, b@test.com, c@test.com")
    assert len(svc.to_addresses) == 3


# ── send() ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_skips_when_disabled():
    svc = _make_service(api_key="")
    result = await svc.send("Test", "<p>Test</p>")
    assert result["skipped"] is True


@pytest.mark.asyncio
async def test_send_success():
    svc = _make_service()
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "email_123"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=mock_response)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await svc.send("Test Subject", "<p>Body</p>")
        assert result["id"] == "email_123"
        instance.post.assert_called_once()
        call_kwargs = instance.post.call_args
        assert "Bearer re_test_key" in str(call_kwargs)


@pytest.mark.asyncio
async def test_send_with_custom_recipients():
    svc = _make_service()
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "email_456"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=mock_response)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await svc.send("Test", "<p>Body</p>", to=["custom@test.com"])
        assert result["id"] == "email_456"
        body = instance.post.call_args[1]["json"]
        assert body["to"] == ["custom@test.com"]


@pytest.mark.asyncio
async def test_send_with_tags():
    svc = _make_service()
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "email_789"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=mock_response)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        tags = [{"name": "category", "value": "test"}]
        result = await svc.send("Test", "<p>Body</p>", tags=tags)
        body = instance.post.call_args[1]["json"]
        assert body["tags"] == tags


@pytest.mark.asyncio
async def test_send_api_error():
    svc = _make_service()
    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(side_effect=Exception("API error"))
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await svc.send("Test", "<p>Body</p>")
        assert "error" in result


# ── alert_low_stock() ────────────────────────────────────────

@pytest.mark.asyncio
async def test_alert_low_stock_empty():
    svc = _make_service()
    result = await svc.alert_low_stock([])
    assert result["skipped"] is True


@pytest.mark.asyncio
async def test_alert_low_stock_sends():
    svc = _make_service()
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "ls_001"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=mock_response)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        items = [
            {"sku": "SKU-001", "product_name": "Apple", "on_hand": 3, "reorder_point": 20, "warehouse_id": 1},
            {"sku": "SKU-002", "product_name": "Bread", "on_hand": 0, "reorder_point": 10, "warehouse_id": 1},
        ]
        result = await svc.alert_low_stock(items)
        assert result["id"] == "ls_001"
        body = instance.post.call_args[1]["json"]
        assert "Low Stock Alert" in body["subject"]
        assert "Apple" in body["html"]
        assert "Bread" in body["html"]


# ── alert_fraud_detected() ───────────────────────────────────

@pytest.mark.asyncio
async def test_alert_fraud_sends():
    svc = _make_service()
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "fr_001"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=mock_response)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await svc.alert_fraud_detected(
            order_id=42,
            risk_score=0.85,
            risk_level="high",
            factors=["Velocity check failed", "High value order"],
            customer_name="Test Customer",
            amount=500000.0,
        )
        assert result["id"] == "fr_001"
        body = instance.post.call_args[1]["json"]
        assert "Fraud" in body["subject"]
        assert "#42" in body["html"]
        assert "Test Customer" in body["html"]
        assert "₦500,000.00" in body["html"]


@pytest.mark.asyncio
async def test_alert_fraud_no_customer():
    svc = _make_service()
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "fr_002"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=mock_response)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await svc.alert_fraud_detected(
            order_id=99, risk_score=0.6, risk_level="medium", factors=["Unusual amount"],
        )
        body = instance.post.call_args[1]["json"]
        assert "Unknown" in body["html"]


# ── alert_overdue_debts() ────────────────────────────────────

@pytest.mark.asyncio
async def test_alert_overdue_debts_empty():
    svc = _make_service()
    result = await svc.alert_overdue_debts([])
    assert result["skipped"] is True


@pytest.mark.asyncio
async def test_alert_overdue_debts_sends():
    svc = _make_service()
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "od_001"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=mock_response)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        debts = [
            {"id": 1, "type": "receivable", "entity_type": "customer", "amount_ngn": 50000, "due_date": "2025-01-01"},
            {"id": 2, "type": "payable", "entity_type": "supplier", "amount_ngn": 30000, "due_date": "2025-01-15"},
        ]
        result = await svc.alert_overdue_debts(debts)
        assert result["id"] == "od_001"
        body = instance.post.call_args[1]["json"]
        assert "Overdue" in body["subject"]
        assert "₦80,000.00" in body["subject"]


# ── alert_order_failure() ────────────────────────────────────

@pytest.mark.asyncio
async def test_alert_order_failure_sends():
    svc = _make_service()
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "of_001"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=mock_response)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await svc.alert_order_failure(
            order_id=77, error="Insufficient stock for product 5", customer_name="Adebayo",
        )
        assert result["id"] == "of_001"
        body = instance.post.call_args[1]["json"]
        assert "Failed" in body["subject"]
        assert "Adebayo" in body["html"]


@pytest.mark.asyncio
async def test_alert_order_failure_no_order_id():
    svc = _make_service()
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "of_002"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=mock_response)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await svc.alert_order_failure(order_id=None, error="Unknown error")
        body = instance.post.call_args[1]["json"]
        assert "N/A" in body["html"]


# ── alert_system_health() ────────────────────────────────────

@pytest.mark.asyncio
async def test_alert_system_health_critical():
    svc = _make_service()
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "sh_001"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=mock_response)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await svc.alert_system_health(
            component="Database", status="critical", details="Connection pool exhausted",
        )
        assert result["id"] == "sh_001"
        body = instance.post.call_args[1]["json"]
        assert "CRITICAL" in body["subject"]
        assert "Database" in body["html"]


@pytest.mark.asyncio
async def test_alert_system_health_warning():
    svc = _make_service()
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "sh_002"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=mock_response)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await svc.alert_system_health(
            component="Redis", status="warning", details="High memory usage",
        )
        body = instance.post.call_args[1]["json"]
        assert "WARNING" in body["subject"]


# ── Singleton ────────────────────────────────────────────────

def test_get_email_service_singleton():
    svc1 = get_email_service()
    svc2 = get_email_service()
    assert svc1 is svc2
