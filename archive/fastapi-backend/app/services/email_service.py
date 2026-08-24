"""Email notification service using Resend (free tier: 100 emails/day).

Sends alerts for critical business events:
- Low stock warnings
- Fraud detection alerts
- Overdue debt notifications
- Order failure alerts
- System health warnings
"""
from __future__ import annotations
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


class EmailService:
    """Lightweight email client backed by Resend REST API."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.api_key = self.settings.RESEND_API_KEY or ""
        self.from_address = self.settings.ALERT_EMAIL_FROM
        self.to_addresses = [
            e.strip() for e in (self.settings.ALERT_EMAIL_TO or "").split(",") if e.strip()
        ]
        self.enabled = bool(
            self.settings.EMAIL_NOTIFICATIONS_ENABLED
            and self.api_key
            and self.to_addresses
        )

    # ── Core send ────────────────────────────────────────────

    async def send(
        self,
        subject: str,
        html: str,
        to: Optional[List[str]] = None,
        tags: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Send an email via Resend. Returns {"id": "..."} on success."""
        if not self.enabled:
            logger.info("email_skip", extra={"reason": "disabled or missing config", "subject": subject})
            return {"skipped": True, "reason": "notifications disabled"}

        recipients = to or self.to_addresses
        payload: Dict[str, Any] = {
            "from": self.from_address,
            "to": recipients,
            "subject": subject,
            "html": html,
        }
        if tags:
            payload["tags"] = tags

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    RESEND_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                resp.raise_for_status()
                result = resp.json()
                logger.info("email_sent", extra={"subject": subject, "to": recipients, "id": result.get("id")})
                return result
        except Exception as e:
            logger.error("email_send_failed", extra={"error": str(e), "subject": subject})
            return {"error": str(e)}

    # ── Alert templates ──────────────────────────────────────

    async def alert_low_stock(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Send low-stock alert for one or more products."""
        if not items:
            return {"skipped": True, "reason": "no items"}

        rows = "".join(
            f"<tr><td style='padding:8px;border:1px solid #ddd'>{it.get('sku', 'N/A')}</td>"
            f"<td style='padding:8px;border:1px solid #ddd'>{it.get('product_name', 'Unknown')}</td>"
            f"<td style='padding:8px;border:1px solid #ddd;color:#c0392b;font-weight:bold'>{it.get('on_hand', 0)}</td>"
            f"<td style='padding:8px;border:1px solid #ddd'>{it.get('reorder_point', 0)}</td>"
            f"<td style='padding:8px;border:1px solid #ddd'>{it.get('warehouse_id', '-')}</td></tr>"
            for it in items
        )

        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
            <h2 style="color:#e74c3c">⚠️ Low Stock Alert</h2>
            <p>{len(items)} product(s) are below reorder point and need restocking.</p>
            <table style="border-collapse:collapse;width:100%">
                <tr style="background:#f8f9fa">
                    <th style="padding:8px;border:1px solid #ddd;text-align:left">SKU</th>
                    <th style="padding:8px;border:1px solid #ddd;text-align:left">Product</th>
                    <th style="padding:8px;border:1px solid #ddd;text-align:left">On Hand</th>
                    <th style="padding:8px;border:1px solid #ddd;text-align:left">Reorder Point</th>
                    <th style="padding:8px;border:1px solid #ddd;text-align:left">Warehouse</th>
                </tr>
                {rows}
            </table>
            <p style="color:#7f8c8d;font-size:12px;margin-top:16px">
                Sent by WakaAgent AI at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
            </p>
        </div>
        """
        return await self.send(
            subject=f"🚨 Low Stock Alert — {len(items)} product(s) need restocking",
            html=html,
            tags=[{"name": "category", "value": "low_stock"}],
        )

    async def alert_fraud_detected(
        self,
        order_id: int,
        risk_score: float,
        risk_level: str,
        factors: List[str],
        customer_name: Optional[str] = None,
        amount: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Send fraud detection alert for a suspicious order."""
        color = "#c0392b" if risk_level == "high" else "#e67e22" if risk_level == "medium" else "#f39c12"
        factor_list = "".join(f"<li>{f}</li>" for f in factors)
        amount_str = f"₦{amount:,.2f}" if amount else "N/A"

        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
            <h2 style="color:{color}">🛡️ Fraud Detection Alert</h2>
            <table style="border-collapse:collapse;width:100%">
                <tr><td style="padding:8px;font-weight:bold">Order ID</td><td style="padding:8px">#{order_id}</td></tr>
                <tr><td style="padding:8px;font-weight:bold">Customer</td><td style="padding:8px">{customer_name or 'Unknown'}</td></tr>
                <tr><td style="padding:8px;font-weight:bold">Amount</td><td style="padding:8px">{amount_str}</td></tr>
                <tr><td style="padding:8px;font-weight:bold">Risk Score</td>
                    <td style="padding:8px;color:{color};font-weight:bold">{risk_score:.0%} ({risk_level.upper()})</td></tr>
            </table>
            <h3>Risk Factors</h3>
            <ul>{factor_list}</ul>
            <p><strong>Action required:</strong> Review this order in the admin panel before processing.</p>
            <p style="color:#7f8c8d;font-size:12px;margin-top:16px">
                Sent by WakaAgent AI at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
            </p>
        </div>
        """
        return await self.send(
            subject=f"🛡️ Fraud Alert — Order #{order_id} flagged as {risk_level.upper()} risk",
            html=html,
            tags=[{"name": "category", "value": "fraud_detection"}],
        )

    async def alert_overdue_debts(self, debts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Send overdue debt notification."""
        if not debts:
            return {"skipped": True, "reason": "no debts"}

        total = sum(float(d.get("amount_ngn", 0)) for d in debts)
        rows = "".join(
            f"<tr><td style='padding:8px;border:1px solid #ddd'>#{d.get('id', '')}</td>"
            f"<td style='padding:8px;border:1px solid #ddd'>{d.get('type', '')}</td>"
            f"<td style='padding:8px;border:1px solid #ddd'>{d.get('entity_type', '')}</td>"
            f"<td style='padding:8px;border:1px solid #ddd;font-weight:bold'>₦{float(d.get('amount_ngn', 0)):,.2f}</td>"
            f"<td style='padding:8px;border:1px solid #ddd;color:#c0392b'>{d.get('due_date', 'N/A')}</td></tr>"
            for d in debts
        )

        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
            <h2 style="color:#e67e22">📋 Overdue Debts Alert</h2>
            <p><strong>{len(debts)}</strong> debt(s) totalling <strong>₦{total:,.2f}</strong> are overdue.</p>
            <table style="border-collapse:collapse;width:100%">
                <tr style="background:#f8f9fa">
                    <th style="padding:8px;border:1px solid #ddd;text-align:left">ID</th>
                    <th style="padding:8px;border:1px solid #ddd;text-align:left">Type</th>
                    <th style="padding:8px;border:1px solid #ddd;text-align:left">Entity</th>
                    <th style="padding:8px;border:1px solid #ddd;text-align:left">Amount</th>
                    <th style="padding:8px;border:1px solid #ddd;text-align:left">Due Date</th>
                </tr>
                {rows}
            </table>
            <p style="color:#7f8c8d;font-size:12px;margin-top:16px">
                Sent by WakaAgent AI at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
            </p>
        </div>
        """
        return await self.send(
            subject=f"📋 {len(debts)} Overdue Debt(s) — ₦{total:,.2f} outstanding",
            html=html,
            tags=[{"name": "category", "value": "overdue_debts"}],
        )

    async def alert_order_failure(
        self,
        order_id: Optional[int],
        error: str,
        customer_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send order processing failure alert."""
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
            <h2 style="color:#c0392b">❌ Order Processing Failed</h2>
            <table style="border-collapse:collapse;width:100%">
                <tr><td style="padding:8px;font-weight:bold">Order ID</td><td style="padding:8px">#{order_id or 'N/A'}</td></tr>
                <tr><td style="padding:8px;font-weight:bold">Customer</td><td style="padding:8px">{customer_name or 'Unknown'}</td></tr>
                <tr><td style="padding:8px;font-weight:bold">Error</td><td style="padding:8px;color:#c0392b">{error}</td></tr>
            </table>
            <p>Please investigate and retry or contact the customer.</p>
            <p style="color:#7f8c8d;font-size:12px;margin-top:16px">
                Sent by WakaAgent AI at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
            </p>
        </div>
        """
        return await self.send(
            subject=f"❌ Order #{order_id or 'N/A'} Failed — {error[:60]}",
            html=html,
            tags=[{"name": "category", "value": "order_failure"}],
        )

    async def alert_system_health(
        self,
        component: str,
        status: str,
        details: str,
    ) -> Dict[str, Any]:
        """Send system health warning."""
        color = "#c0392b" if status == "critical" else "#e67e22"
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
            <h2 style="color:{color}">🔧 System Health Warning</h2>
            <table style="border-collapse:collapse;width:100%">
                <tr><td style="padding:8px;font-weight:bold">Component</td><td style="padding:8px">{component}</td></tr>
                <tr><td style="padding:8px;font-weight:bold">Status</td>
                    <td style="padding:8px;color:{color};font-weight:bold">{status.upper()}</td></tr>
                <tr><td style="padding:8px;font-weight:bold">Details</td><td style="padding:8px">{details}</td></tr>
            </table>
            <p style="color:#7f8c8d;font-size:12px;margin-top:16px">
                Sent by WakaAgent AI at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
            </p>
        </div>
        """
        return await self.send(
            subject=f"🔧 [{status.upper()}] {component} — {details[:60]}",
            html=html,
            tags=[{"name": "category", "value": "system_health"}],
        )


# ── Singleton ────────────────────────────────────────────────

_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
