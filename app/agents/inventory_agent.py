from __future__ import annotations
from typing import Any, Optional, Dict, List
from decimal import Decimal
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_

from app.agents.orchestrator import Agent, AgentState
from app.db.session import SessionLocal
from app.models.products import Product
from app.models.inventory import Inventory, Warehouse
from app.models.orders import Order, OrderItem
from app.services.llm_client import get_llm_client


class InventoryAgent:
    """Enhanced Inventory Agent with comprehensive inventory management capabilities"""
    
    name = "inventory.management"
    description = "AI-powered inventory management and stock control"
    tools = [
        "check_stock",
        "reserve_inventory",
        "adjust_inventory",
        "get_low_stock_alerts",
        "update_reorder_points",
        "track_movements",
        "generate_inventory_report"
    ]

    async def can_handle(self, intent: str, payload: Dict[str, Any]) -> bool:
        """Check if agent can handle the intent"""
        return intent.startswith("inventory.") or intent.startswith("stock.")

    async def handle(self, state: AgentState) -> AgentState:
        """Handle inventory-related requests"""
        try:
            intent = state["intent"]
            payload = state["payload"]
            
            if intent == "inventory.check":
                result = await self._check_stock(payload)
            elif intent == "inventory.reserve":
                result = await self._reserve_inventory(payload)
            elif intent == "inventory.adjust":
                result = await self._adjust_inventory(payload)
            elif intent == "inventory.low_stock":
                result = await self._get_low_stock_alerts(payload)
            elif intent == "inventory.update_reorder":
                result = await self._update_reorder_points(payload)
            elif intent == "inventory.movements":
                result = await self._track_movements(payload)
            elif intent == "inventory.report":
                result = await self._generate_inventory_report(payload)
            else:
                result = await self._general_inventory_query(payload)
            
            return {
                **state,
                "result": result,
                "error": None
            }
            
        except Exception as e:
            return {
                **state,
                "result": None,
                "error": str(e)
            }

    async def _check_stock(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Check stock levels for products"""
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
                return {
                    "success": False,
                    "message": "Product not found"
                }

            if warehouse_id:
                # Specific warehouse
                inv = (
                    db.query(Inventory)
                    .filter(Inventory.product_id == product.id, Inventory.warehouse_id == int(warehouse_id))
                    .first()
                )
                on_hand = float(inv.on_hand) if inv and inv.on_hand is not None else 0.0
                reserved = float(inv.reserved) if inv and inv.reserved is not None else 0.0
                reorder_point = float(inv.reorder_point) if inv and inv.reorder_point is not None else 0.0
                
                return {
                    "success": True,
                    "result": {
                        "product": {"id": product.id, "sku": product.sku, "name": product.name},
                        "warehouse": int(warehouse_id),
                        "on_hand": on_hand,
                        "reserved": reserved,
                        "available": round(on_hand - reserved, 2),
                        "reorder_point": reorder_point,
                        "status": "low_stock" if on_hand <= reorder_point else "in_stock"
                    },
                }
            else:
                # Aggregate across warehouses
                agg = (
                    db.query(
                        func.coalesce(func.sum(Inventory.on_hand), 0),
                        func.coalesce(func.sum(Inventory.reserved), 0),
                        func.coalesce(func.sum(Inventory.reorder_point), 0),
                    )
                    .filter(Inventory.product_id == product.id)
                    .one()
                )
                on_hand = float(agg[0] or 0)
                reserved = float(agg[1] or 0)
                total_reorder_point = float(agg[2] or 0)
                
                by_wh = (
                    db.query(Inventory.warehouse_id, Inventory.on_hand, Inventory.reserved, Inventory.reorder_point)
                    .filter(Inventory.product_id == product.id)
                    .all()
                )
                
                return {
                    "success": True,
                    "result": {
                        "product": {"id": product.id, "sku": product.sku, "name": product.name},
                        "on_hand": on_hand,
                        "reserved": reserved,
                        "available": round(on_hand - reserved, 2),
                        "total_reorder_point": total_reorder_point,
                        "status": "low_stock" if on_hand <= total_reorder_point else "in_stock",
                        "by_warehouse": [
                            {
                                "warehouse_id": int(wid),
                                "on_hand": float(oh or 0),
                                "reserved": float(rv or 0),
                                "available": round(float(oh or 0) - float(rv or 0), 2),
                                "reorder_point": float(rp or 0),
                                "status": "low_stock" if (oh or 0) <= (rp or 0) else "in_stock"
                            }
                            for (wid, oh, rv, rp) in by_wh
                        ],
                    },
                }
        finally:
            db.close()

    async def _reserve_inventory(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Reserve inventory for an order"""
        product_id = payload.get("product_id")
        warehouse_id = payload.get("warehouse_id")
        quantity = payload.get("quantity")
        order_id = payload.get("order_id")
        
        if not all([product_id, warehouse_id, quantity]):
            return {
                "success": False,
                "message": "product_id, warehouse_id, and quantity are required"
            }
        
        db = SessionLocal()
        try:
            # Check current inventory
            inventory = db.query(Inventory).filter(
                Inventory.product_id == product_id,
                Inventory.warehouse_id == warehouse_id
            ).first()
            
            if not inventory:
                return {
                    "success": False,
                    "message": "Inventory record not found"
                }
            
            available = float(inventory.on_hand or 0) - float(inventory.reserved or 0)
            
            if available < quantity:
                return {
                    "success": False,
                    "message": f"Insufficient stock. Available: {available}, Requested: {quantity}"
                }
            
            # Reserve inventory
            inventory.reserved = float(inventory.reserved or 0) + quantity
            db.commit()
            
            return {
                "success": True,
                "product_id": product_id,
                "warehouse_id": warehouse_id,
                "reserved_quantity": quantity,
                "remaining_available": available - quantity,
                "order_id": order_id,
                "message": "Inventory reserved successfully"
            }
            
        finally:
            db.close()

    async def _adjust_inventory(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Adjust inventory levels"""
        product_id = payload.get("product_id")
        warehouse_id = payload.get("warehouse_id")
        adjustment = payload.get("adjustment")  # Positive for increase, negative for decrease
        reason = payload.get("reason", "Manual adjustment")
        
        if not all([product_id, warehouse_id, adjustment is not None]):
            return {
                "success": False,
                "message": "product_id, warehouse_id, and adjustment are required"
            }
        
        db = SessionLocal()
        try:
            inventory = db.query(Inventory).filter(
                Inventory.product_id == product_id,
                Inventory.warehouse_id == warehouse_id
            ).first()
            
            if not inventory:
                return {
                    "success": False,
                    "message": "Inventory record not found"
                }
            
            old_on_hand = float(inventory.on_hand or 0)
            new_on_hand = old_on_hand + adjustment
            
            if new_on_hand < 0:
                return {
                    "success": False,
                    "message": "Adjustment would result in negative inventory"
                }
            
            inventory.on_hand = new_on_hand
            db.commit()
            
            return {
                "success": True,
                "product_id": product_id,
                "warehouse_id": warehouse_id,
                "old_quantity": old_on_hand,
                "adjustment": adjustment,
                "new_quantity": new_on_hand,
                "reason": reason,
                "message": "Inventory adjusted successfully"
            }
            
        finally:
            db.close()

    async def _get_low_stock_alerts(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Get low stock alerts"""
        warehouse_id = payload.get("warehouse_id")
        threshold_multiplier = payload.get("threshold_multiplier", 1.0)
        
        db = SessionLocal()
        try:
            query = db.query(Inventory, Product).join(Product, Inventory.product_id == Product.id)
            
            if warehouse_id:
                query = query.filter(Inventory.warehouse_id == warehouse_id)
            
            # Filter for low stock items
            low_stock_items = []
            for inventory, product in query.all():
                on_hand = float(inventory.on_hand or 0)
                reorder_point = float(inventory.reorder_point or 0) * threshold_multiplier
                
                if on_hand <= reorder_point:
                    low_stock_items.append({
                        "product_id": product.id,
                        "product_name": product.name,
                        "sku": product.sku,
                        "warehouse_id": inventory.warehouse_id,
                        "on_hand": on_hand,
                        "reorder_point": float(inventory.reorder_point or 0),
                        "shortage": max(0, float(inventory.reorder_point or 0) - on_hand),
                        "status": "critical" if on_hand == 0 else "low"
                    })
            
            return {
                "success": True,
                "low_stock_items": low_stock_items,
                "count": len(low_stock_items),
                "warehouse_id": warehouse_id,
                "message": f"Found {len(low_stock_items)} items with low stock"
            }
            
        finally:
            db.close()

    async def _update_reorder_points(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Update reorder points for products"""
        product_id = payload.get("product_id")
        warehouse_id = payload.get("warehouse_id")
        new_reorder_point = payload.get("reorder_point")
        
        if not all([product_id, warehouse_id, new_reorder_point is not None]):
            return {
                "success": False,
                "message": "product_id, warehouse_id, and reorder_point are required"
            }
        
        db = SessionLocal()
        try:
            inventory = db.query(Inventory).filter(
                Inventory.product_id == product_id,
                Inventory.warehouse_id == warehouse_id
            ).first()
            
            if not inventory:
                return {
                    "success": False,
                    "message": "Inventory record not found"
                }
            
            old_reorder_point = float(inventory.reorder_point or 0)
            inventory.reorder_point = new_reorder_point
            db.commit()
            
            return {
                "success": True,
                "product_id": product_id,
                "warehouse_id": warehouse_id,
                "old_reorder_point": old_reorder_point,
                "new_reorder_point": new_reorder_point,
                "message": "Reorder point updated successfully"
            }
            
        finally:
            db.close()

    async def _track_movements(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Track inventory movements"""
        product_id = payload.get("product_id")
        warehouse_id = payload.get("warehouse_id")
        days = payload.get("days", 30)
        
        db = SessionLocal()
        try:
            # Get recent orders with this product
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            query = db.query(Order, OrderItem).join(OrderItem, Order.id == OrderItem.order_id)
            query = query.filter(OrderItem.product_id == product_id)
            query = query.filter(Order.created_at >= cutoff_date)
            
            if warehouse_id:
                # This would need warehouse information in orders
                pass
            
            movements = []
            for order, order_item in query.all():
                movements.append({
                    "date": order.created_at.isoformat(),
                    "order_id": order.id,
                    "type": "outbound",
                    "quantity": order_item.quantity,
                    "reason": f"Order #{order.id}"
                })
            
            return {
                "success": True,
                "product_id": product_id,
                "warehouse_id": warehouse_id,
                "period_days": days,
                "movements": movements,
                "total_outbound": sum(m["quantity"] for m in movements),
                "message": f"Found {len(movements)} movements in the last {days} days"
            }
            
        finally:
            db.close()

    async def _generate_inventory_report(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive inventory report"""
        warehouse_id = payload.get("warehouse_id")
        
        db = SessionLocal()
        try:
            query = db.query(Inventory, Product).join(Product, Inventory.product_id == Product.id)
            
            if warehouse_id:
                query = query.filter(Inventory.warehouse_id == warehouse_id)
            
            inventory_data = []
            total_value = 0.0
            low_stock_count = 0
            
            for inventory, product in query.all():
                on_hand = float(inventory.on_hand or 0)
                reserved = float(inventory.reserved or 0)
                available = on_hand - reserved
                reorder_point = float(inventory.reorder_point or 0)
                item_value = on_hand * float(product.price_ngn or 0)
                total_value += item_value
                
                if on_hand <= reorder_point:
                    low_stock_count += 1
                
                inventory_data.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "sku": product.sku,
                    "warehouse_id": inventory.warehouse_id,
                    "on_hand": on_hand,
                    "reserved": reserved,
                    "available": available,
                    "reorder_point": reorder_point,
                    "unit_price": float(product.price_ngn or 0),
                    "total_value": item_value,
                    "status": "critical" if on_hand == 0 else ("low" if on_hand <= reorder_point else "good")
                })
            
            # Sort by total value descending
            inventory_data.sort(key=lambda x: x["total_value"], reverse=True)
            
            return {
                "success": True,
                "warehouse_id": warehouse_id,
                "total_products": len(inventory_data),
                "total_value": total_value,
                "low_stock_count": low_stock_count,
                "inventory_data": inventory_data,
                "generated_at": datetime.utcnow().isoformat(),
                "message": f"Inventory report generated for {len(inventory_data)} products"
            }
            
        finally:
            db.close()

    async def _general_inventory_query(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general inventory queries using LLM"""
        query = payload.get("message", "")
        
        # Use LLM to generate response
        llm_client = get_llm_client()
        response = await llm_client.complete(
            prompt=f"User query about inventory: {query}",
            system="You are an inventory management expert. Help users with stock-related questions and operations.",
            temperature=0.3
        )
        
        return {
            "success": True,
            "response": response,
            "type": "llm_response"
        }


# Create global instance
inventory_agent = InventoryAgent()
