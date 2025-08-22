from __future__ import annotations
from typing import Any, Optional
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.agents.orchestrator import Agent
from app.db.session import SessionLocal
from app.models.products import Product
from app.models.inventory import Inventory, Warehouse


class InventoryAgent:
    name = "inventory.check"

    async def handle(self, intent: str, payload: dict) -> dict:
        product_id: Optional[int] = payload.get("product_id")
        sku: Optional[str] = payload.get("sku")
        warehouse_id: Optional[int] = payload.get("warehouse_id")

        db: Session = SessionLocal()
        try:
            # Resolve product
            product: Optional[Product] = None
            if product_id:
                product = db.query(Product).filter(Product.id == int(product_id)).first()
            elif sku:
                product = db.query(Product).filter(Product.sku == sku).first()
            if not product:
                return {"handled": False, "reason": "product_not_found"}

            if warehouse_id:
                # Specific warehouse
                inv = (
                    db.query(Inventory)
                    .filter(Inventory.product_id == product.id, Inventory.warehouse_id == int(warehouse_id))
                    .first()
                )
                on_hand = float(inv.on_hand) if inv and inv.on_hand is not None else 0.0
                reserved = float(inv.reserved) if inv and inv.reserved is not None else 0.0
                return {
                    "handled": True,
                    "result": {
                        "product": {"id": product.id, "sku": product.sku, "name": product.name},
                        "warehouse": int(warehouse_id),
                        "on_hand": on_hand,
                        "reserved": reserved,
                        "available": round(on_hand - reserved, 2),
                    },
                }
            else:
                # Aggregate across warehouses
                agg = (
                    db.query(
                        func.coalesce(func.sum(Inventory.on_hand), 0),
                        func.coalesce(func.sum(Inventory.reserved), 0),
                    )
                    .filter(Inventory.product_id == product.id)
                    .one()
                )
                on_hand = float(agg[0] or 0)
                reserved = float(agg[1] or 0)
                by_wh = (
                    db.query(Inventory.warehouse_id, Inventory.on_hand, Inventory.reserved)
                    .filter(Inventory.product_id == product.id)
                    .all()
                )
                return {
                    "handled": True,
                    "result": {
                        "product": {"id": product.id, "sku": product.sku, "name": product.name},
                        "on_hand": on_hand,
                        "reserved": reserved,
                        "available": round(on_hand - reserved, 2),
                        "by_warehouse": [
                            {
                                "warehouse_id": int(wid),
                                "on_hand": float(oh or 0),
                                "reserved": float(rv or 0),
                                "available": round(float(oh or 0) - float(rv or 0), 2),
                            }
                            for (wid, oh, rv) in by_wh
                        ],
                    },
                }
        finally:
            db.close()
