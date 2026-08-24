from __future__ import annotations
from typing import Any

from sqlalchemy.orm import Session

from app.agents.orchestrator import Agent
from app.db.session import SessionLocal
from app.models.orders import Order
from app.schemas.orders import OrderOut


class OrdersLookupAgent:
    name = "orders.lookup"

    async def handle(self, intent: str, payload: dict) -> dict:
        order_id = int(payload.get("order_id", 0))
        if not order_id:
            return {"handled": False, "reason": "missing_order_id"}
        db: Session = SessionLocal()
        try:
            o = db.query(Order).filter(Order.id == order_id).first()
            if not o:
                return {"handled": False, "reason": "not_found"}
            out = OrderOut(id=o.id, status=o.status, total=float(o.total), currency=o.currency)
            return {"handled": True, "result": out.model_dump()}
        finally:
            db.close()
