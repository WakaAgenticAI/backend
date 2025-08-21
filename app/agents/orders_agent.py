from __future__ import annotations
from typing import Any

from app.agents.orchestrator import Agent
from app.schemas.orders import OrderCreate, OrderOut
from app.services import orders_service
from app.db.session import SessionLocal


class OrdersAgent:
    name = "orders.create"

    async def handle(self, intent: str, payload: dict) -> dict:  # pragma: no cover - thin shim
        data = OrderCreate(**payload)
        db = SessionLocal()
        try:
            _order_id, out = orders_service.create_order(db, data)
            return {"handled": True, "result": out.model_dump()}
        finally:
            db.close()
