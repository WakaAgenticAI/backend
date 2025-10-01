from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from app.agents.orchestrator import Agent, AgentState
from app.schemas.orders import OrderCreate, OrderOut
from app.services import orders_service
from app.db.session import SessionLocal
from app.models.orders import Order, OrderItem
from app.models.products import Product
from app.models.inventory import Inventory
from app.services.llm_client import get_llm_client


class OrdersAgent:
    """Enhanced Orders Agent with comprehensive order management capabilities"""
    
    name = "orders.management"
    description = "AI-powered order management and processing"
    tools = [
        "create_order",
        "lookup_order",
        "update_order_status",
        "cancel_order",
        "process_payment",
        "generate_invoice",
        "track_shipment"
    ]

    async def can_handle(self, intent: str, payload: Dict[str, Any]) -> bool:
        """Check if agent can handle the intent"""
        return intent.startswith("order.") or intent.startswith("orders.")

    async def handle(self, state: AgentState) -> AgentState:
        """Handle order-related requests"""
        try:
            intent = state["intent"]
            payload = state["payload"]
            
            if intent == "order.create":
                result = await self._create_order(payload)
            elif intent == "order.lookup":
                result = await self._lookup_order(payload)
            elif intent == "order.update_status":
                result = await self._update_order_status(payload)
            elif intent == "order.cancel":
                result = await self._cancel_order(payload)
            elif intent == "order.process_payment":
                result = await self._process_payment(payload)
            elif intent == "order.generate_invoice":
                result = await self._generate_invoice(payload)
            else:
                result = await self._general_order_query(payload)
            
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

    async def _create_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new order"""
        try:
            data = OrderCreate(**payload)
            db = SessionLocal()
            try:
                order_id, out = orders_service.create_order(db, data)
                return {
                    "success": True,
                    "order_id": order_id,
                    "order": out.model_dump(),
                    "message": "Order created successfully"
                }
            finally:
                db.close()
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create order"
            }

    async def _lookup_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Lookup order information"""
        order_id = payload.get("order_id")
        order_number = payload.get("order_number")
        customer_id = payload.get("customer_id")
        
        if not any([order_id, order_number, customer_id]):
            return {
                "success": False,
                "message": "order_id, order_number, or customer_id is required"
            }
        
        db = SessionLocal()
        try:
            query = db.query(Order)
            
            if order_id:
                query = query.filter(Order.id == order_id)
            elif order_number:
                query = query.filter(Order.order_number == order_number)
            elif customer_id:
                query = query.filter(Order.customer_id == customer_id)
            
            orders = query.all()
            
            if not orders:
                return {
                    "success": False,
                    "message": "No orders found"
                }
            
            # Format order data
            order_data = []
            for order in orders:
                order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
                items = []
                for item in order_items:
                    product = db.query(Product).filter(Product.id == item.product_id).first()
                    items.append({
                        "product_id": item.product_id,
                        "product_name": product.name if product else "Unknown",
                        "quantity": item.quantity,
                        "price": float(item.price),
                        "line_total": float(item.line_total)
                    })
                
                order_data.append({
                    "id": order.id,
                    "order_number": order.order_number,
                    "customer_id": order.customer_id,
                    "status": order.status,
                    "total": float(order.total or 0),
                    "currency": order.currency,
                    "created_at": order.created_at.isoformat(),
                    "items": items
                })
            
            return {
                "success": True,
                "orders": order_data,
                "count": len(order_data)
            }
            
        finally:
            db.close()

    async def _update_order_status(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Update order status"""
        order_id = payload.get("order_id")
        new_status = payload.get("status")
        
        if not order_id or not new_status:
            return {
                "success": False,
                "message": "order_id and status are required"
            }
        
        db = SessionLocal()
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                return {
                    "success": False,
                    "message": "Order not found"
                }
            
            old_status = order.status
            order.status = new_status
            order.updated_at = datetime.utcnow()
            
            db.commit()
            
            return {
                "success": True,
                "order_id": order_id,
                "old_status": old_status,
                "new_status": new_status,
                "message": "Order status updated successfully"
            }
            
        finally:
            db.close()

    async def _cancel_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Cancel an order"""
        order_id = payload.get("order_id")
        reason = payload.get("reason", "Customer request")
        
        if not order_id:
            return {
                "success": False,
                "message": "order_id is required"
            }
        
        db = SessionLocal()
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                return {
                    "success": False,
                    "message": "Order not found"
                }
            
            if order.status in ["cancelled", "shipped", "delivered"]:
                return {
                    "success": False,
                    "message": f"Cannot cancel order with status: {order.status}"
                }
            
            # Cancel order
            order.status = "cancelled"
            order.updated_at = datetime.utcnow()
            
            # Release reserved inventory
            order_items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
            for item in order_items:
                inventory = db.query(Inventory).filter(
                    Inventory.product_id == item.product_id
                ).first()
                if inventory:
                    inventory.reserved = max(0, inventory.reserved - item.quantity)
            
            db.commit()
            
            return {
                "success": True,
                "order_id": order_id,
                "status": "cancelled",
                "reason": reason,
                "message": "Order cancelled successfully"
            }
            
        finally:
            db.close()

    async def _process_payment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment for an order"""
        order_id = payload.get("order_id")
        payment_method = payload.get("payment_method")
        amount = payload.get("amount")
        
        if not all([order_id, payment_method, amount]):
            return {
                "success": False,
                "message": "order_id, payment_method, and amount are required"
            }
        
        db = SessionLocal()
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                return {
                    "success": False,
                    "message": "Order not found"
                }
            
            # Validate payment amount
            if float(amount) != float(order.total or 0):
                return {
                    "success": False,
                    "message": "Payment amount does not match order total"
                }
            
            # Update order status to paid
            order.status = "paid"
            order.updated_at = datetime.utcnow()
            
            db.commit()
            
            return {
                "success": True,
                "order_id": order_id,
                "payment_method": payment_method,
                "amount": float(amount),
                "status": "paid",
                "message": "Payment processed successfully"
            }
            
        finally:
            db.close()

    async def _generate_invoice(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate invoice for an order"""
        order_id = payload.get("order_id")
        
        if not order_id:
            return {
                "success": False,
                "message": "order_id is required"
            }
        
        db = SessionLocal()
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                return {
                    "success": False,
                    "message": "Order not found"
                }
            
            # Get order items
            order_items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
            items = []
            for item in order_items:
                product = db.query(Product).filter(Product.id == item.product_id).first()
                items.append({
                    "product_name": product.name if product else "Unknown",
                    "quantity": item.quantity,
                    "unit_price": float(item.price),
                    "line_total": float(item.line_total)
                })
            
            invoice_data = {
                "invoice_number": f"INV-{order_id:06d}",
                "order_id": order_id,
                "order_number": order.order_number,
                "customer_id": order.customer_id,
                "issue_date": datetime.utcnow().date().isoformat(),
                "due_date": (datetime.utcnow().date() + timedelta(days=30)).isoformat(),
                "subtotal": float(order.total or 0),
                "tax": float(order.tax or 0),
                "discount": float(order.discount or 0),
                "total": float(order.total or 0),
                "items": items
            }
            
            return {
                "success": True,
                "invoice": invoice_data,
                "message": "Invoice generated successfully"
            }
            
        finally:
            db.close()

    async def _general_order_query(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general order queries using LLM"""
        query = payload.get("message", "")
        
        # Use LLM to generate response
        llm_client = get_llm_client()
        response = await llm_client.complete(
            prompt=f"User query about orders: {query}",
            system="You are an order management expert. Help users with order-related questions and operations.",
            temperature=0.3
        )
        
        return {
            "success": True,
            "response": response,
            "type": "llm_response"
        }


# Create global instance
orders_agent = OrdersAgent()
