"""Notification endpoints — trigger and test email alerts."""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import get_current_user
from app.models.users import User
from app.services.email_service import get_email_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


# ── Schemas ──────────────────────────────────────────────────

class NotificationStatus(BaseModel):
    enabled: bool
    has_api_key: bool
    recipients: List[str]


class TestEmailRequest(BaseModel):
    subject: str = "WakaAgent AI — Test Notification"
    message: str = "This is a test notification from WakaAgent AI."


class LowStockAlertRequest(BaseModel):
    items: List[dict] = Field(..., min_length=1)


class FraudAlertRequest(BaseModel):
    order_id: int
    risk_score: float = Field(..., ge=0, le=1)
    risk_level: str = "high"
    factors: List[str] = []
    customer_name: Optional[str] = None
    amount: Optional[float] = None


class OverdueDebtsRequest(BaseModel):
    debts: List[dict] = Field(..., min_length=1)


# ── Endpoints ────────────────────────────────────────────────

@router.get("/status", response_model=NotificationStatus)
async def notification_status(user: User = Depends(get_current_user)):
    """Check email notification configuration status."""
    svc = get_email_service()
    return NotificationStatus(
        enabled=svc.enabled,
        has_api_key=bool(svc.api_key),
        recipients=svc.to_addresses,
    )


@router.post("/test")
async def send_test_email(body: TestEmailRequest, user: User = Depends(get_current_user)):
    """Send a test notification email."""
    svc = get_email_service()
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
        <h2 style="color:#2ecc71">✅ Test Notification</h2>
        <p>{body.message}</p>
        <p style="color:#7f8c8d;font-size:12px">Triggered by {user.email}</p>
    </div>
    """
    result = await svc.send(subject=body.subject, html=html)
    return result


@router.post("/alert/low-stock")
async def trigger_low_stock_alert(body: LowStockAlertRequest, user: User = Depends(get_current_user)):
    """Manually trigger a low-stock email alert."""
    svc = get_email_service()
    return await svc.alert_low_stock(body.items)


@router.post("/alert/fraud")
async def trigger_fraud_alert(body: FraudAlertRequest, user: User = Depends(get_current_user)):
    """Manually trigger a fraud detection email alert."""
    svc = get_email_service()
    return await svc.alert_fraud_detected(
        order_id=body.order_id,
        risk_score=body.risk_score,
        risk_level=body.risk_level,
        factors=body.factors,
        customer_name=body.customer_name,
        amount=body.amount,
    )


@router.post("/alert/overdue-debts")
async def trigger_overdue_debts_alert(body: OverdueDebtsRequest, user: User = Depends(get_current_user)):
    """Manually trigger an overdue debts email alert."""
    svc = get_email_service()
    return await svc.alert_overdue_debts(body.debts)
