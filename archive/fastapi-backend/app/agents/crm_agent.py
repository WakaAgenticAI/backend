"""
AI-powered CRM Agent

This agent handles customer relationship management tasks including customer segmentation,
interaction analysis, and personalized recommendations.
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_

from app.agents.orchestrator import Agent, AgentState
from app.db.session import SessionLocal
from app.models.customers import Customer
from app.models.orders import Order, OrderItem
from app.models.products import Product
from app.models.chat import ChatSession, ChatMessage
from app.services.llm_client import get_llm_client


class CRMAgent:
    """AI-powered CRM agent"""
    
    name = "crm.management"
    description = "AI-powered customer relationship management and segmentation"
    tools = [
        "segment_customers",
        "analyze_customer_behavior",
        "generate_recommendations",
        "update_customer_profile",
        "track_interactions",
        "predict_churn"
    ]
    
    def __init__(self):
        self.llm_client = get_llm_client()
        
        # Customer segments
        self.segments = {
            "vip": {"min_orders": 20, "min_value": 500000},
            "loyal": {"min_orders": 10, "min_value": 200000},
            "regular": {"min_orders": 5, "min_value": 50000},
            "new": {"max_orders": 2, "max_days": 30},
            "at_risk": {"last_order_days": 90, "min_orders": 3}
        }
    
    async def can_handle(self, intent: str, payload: Dict[str, Any]) -> bool:
        """Check if agent can handle the intent"""
        return intent.startswith("customer.") or intent.startswith("crm.")
    
    async def handle(self, state: AgentState) -> AgentState:
        """Handle CRM requests"""
        try:
            intent = state["intent"]
            payload = state["payload"]
            
            if intent == "customer.segment":
                result = await self._segment_customers(payload)
            elif intent == "customer.analyze":
                result = await self._analyze_customer_behavior(payload)
            elif intent == "customer.recommend":
                result = await self._generate_recommendations(payload)
            elif intent == "customer.update":
                result = await self._update_customer_profile(payload)
            elif intent == "customer.track":
                result = await self._track_customer_interactions(payload)
            elif intent == "customer.predict_churn":
                result = await self._predict_customer_churn(payload)
            else:
                result = await self._general_crm_query(payload)
            
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
    
    async def _segment_customers(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Segment customers based on behavior and value"""
        db = SessionLocal()
        try:
            # Get all customers with their order statistics
            customers = db.query(Customer).all()
            
            segments = {
                "vip": [],
                "loyal": [],
                "regular": [],
                "new": [],
                "at_risk": []
            }
            
            current_date = datetime.utcnow()
            
            for customer in customers:
                # Get customer order statistics
                orders = db.query(Order).filter(Order.customer_id == customer.id).all()
                
                if not orders:
                    segments["new"].append(customer.id)
                    continue
                
                total_orders = len(orders)
                total_value = sum(float(o.total or 0) for o in orders)
                last_order_date = max(o.created_at for o in orders)
                days_since_last_order = (current_date - last_order_date).days
                customer_age_days = (current_date - customer.created_at).days
                
                # Determine segment
                if (total_orders >= self.segments["vip"]["min_orders"] and 
                    total_value >= self.segments["vip"]["min_value"]):
                    segments["vip"].append(customer.id)
                elif (total_orders >= self.segments["loyal"]["min_orders"] and 
                      total_value >= self.segments["loyal"]["min_value"]):
                    segments["loyal"].append(customer.id)
                elif (total_orders >= self.segments["regular"]["min_orders"] and 
                      total_value >= self.segments["regular"]["min_value"]):
                    segments["regular"].append(customer.id)
                elif (total_orders <= self.segments["new"]["max_orders"] and 
                      customer_age_days <= self.segments["new"]["max_days"]):
                    segments["new"].append(customer.id)
                elif (days_since_last_order >= self.segments["at_risk"]["last_order_days"] and 
                      total_orders >= self.segments["at_risk"]["min_orders"]):
                    segments["at_risk"].append(customer.id)
                else:
                    segments["regular"].append(customer.id)
            
            # Update customer segments in database
            for segment_name, customer_ids in segments.items():
                for customer_id in customer_ids:
                    customer = db.query(Customer).filter(Customer.id == customer_id).first()
                    if customer:
                        # Assuming there's a segment field in Customer model
                        # customer.segment = segment_name
                        pass  # Placeholder for segment update
            
            db.commit()
            
            return {
                "success": True,
                "segments": {k: len(v) for k, v in segments.items()},
                "total_customers": len(customers),
                "message": "Customer segmentation completed successfully"
            }
            
        finally:
            db.close()
    
    async def _analyze_customer_behavior(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze customer behavior patterns"""
        customer_id = payload.get("customer_id")
        
        if not customer_id:
            return {
                "success": False,
                "message": "customer_id is required"
            }
        
        db = SessionLocal()
        try:
            customer = db.query(Customer).filter(Customer.id == customer_id).first()
            if not customer:
                return {
                    "success": False,
                    "message": "Customer not found"
                }
            
            # Get customer orders
            orders = db.query(Order).filter(Order.customer_id == customer_id).all()
            
            if not orders:
                return {
                    "success": True,
                    "customer_id": customer_id,
                    "analysis": {
                        "total_orders": 0,
                        "total_value": 0,
                        "behavior_patterns": [],
                        "recommendations": ["Encourage first purchase with promotional offers"]
                    }
                }
            
            # Analyze behavior patterns
            total_orders = len(orders)
            total_value = sum(float(o.total or 0) for o in orders)
            avg_order_value = total_value / total_orders
            
            # Analyze order frequency
            order_dates = [o.created_at for o in orders]
            order_dates.sort()
            
            if len(order_dates) > 1:
                intervals = [(order_dates[i+1] - order_dates[i]).days for i in range(len(order_dates)-1)]
                avg_interval = sum(intervals) / len(intervals)
            else:
                avg_interval = 0
            
            # Analyze product preferences
            product_counts = {}
            for order in orders:
                order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
                for item in order_items:
                    product = db.query(Product).filter(Product.id == item.product_id).first()
                    if product:
                        product_counts[product.name] = product_counts.get(product.name, 0) + item.quantity
            
            # Get chat interactions
            chat_sessions = db.query(ChatSession).filter(ChatSession.user_id == customer_id).all()
            total_interactions = len(chat_sessions)
            
            # Generate behavior insights
            behavior_patterns = []
            
            if avg_order_value > 100000:
                behavior_patterns.append("High-value customer")
            
            if avg_interval < 30:
                behavior_patterns.append("Frequent purchaser")
            elif avg_interval > 90:
                behavior_patterns.append("Infrequent purchaser")
            
            if total_interactions > 5:
                behavior_patterns.append("Engaged customer")
            
            # Generate AI-powered insights
            insights = await self._generate_customer_insights(
                customer, orders, product_counts, behavior_patterns
            )
            
            return {
                "success": True,
                "customer_id": customer_id,
                "analysis": {
                    "total_orders": total_orders,
                    "total_value": total_value,
                    "avg_order_value": round(avg_order_value, 2),
                    "avg_order_interval_days": round(avg_interval, 1),
                    "total_interactions": total_interactions,
                    "top_products": dict(sorted(product_counts.items(), key=lambda x: x[1], reverse=True)[:5]),
                    "behavior_patterns": behavior_patterns,
                    "insights": insights
                }
            }
            
        finally:
            db.close()
    
    async def _generate_recommendations(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate personalized recommendations for customers"""
        customer_id = payload.get("customer_id")
        
        if not customer_id:
            return {
                "success": False,
                "message": "customer_id is required"
            }
        
        db = SessionLocal()
        try:
            customer = db.query(Customer).filter(Customer.id == customer_id).first()
            if not customer:
                return {
                    "success": False,
                    "message": "Customer not found"
                }
            
            # Get customer's order history
            orders = db.query(Order).filter(Order.customer_id == customer_id).all()
            
            if not orders:
                # New customer recommendations
                recommendations = await self._get_new_customer_recommendations(db)
            else:
                # Personalized recommendations based on history
                recommendations = await self._get_personalized_recommendations(db, customer_id, orders)
            
            return {
                "success": True,
                "customer_id": customer_id,
                "recommendations": recommendations
            }
            
        finally:
            db.close()
    
    async def _get_new_customer_recommendations(self, db: Session) -> List[Dict[str, Any]]:
        """Get recommendations for new customers"""
        # Get popular products
        popular_products = db.query(
            Product.id,
            Product.name,
            Product.price_ngn,
            func.sum(OrderItem.quantity).label('total_sold')
        ).join(OrderItem, Product.id == OrderItem.product_id)\
         .group_by(Product.id)\
         .order_by(func.sum(OrderItem.quantity).desc())\
         .limit(5).all()
        
        recommendations = []
        for product in popular_products:
            recommendations.append({
                "type": "product",
                "product_id": product.id,
                "name": product.name,
                "price": float(product.price_ngn),
                "reason": "Popular choice among customers"
            })
        
        return recommendations
    
    async def _get_personalized_recommendations(self, db: Session, customer_id: int, orders: List[Order]) -> List[Dict[str, Any]]:
        """Get personalized recommendations based on customer history"""
        # Get customer's purchased products
        purchased_products = set()
        for order in orders:
            order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
            for item in order_items:
                purchased_products.add(item.product_id)
        
        # Find similar products (simplified - in production, use collaborative filtering)
        recommendations = []
        
        # Get products from same categories
        if purchased_products:
            # This is a simplified approach - in production, you'd use more sophisticated algorithms
            similar_products = db.query(Product).filter(
                Product.id.notin_(purchased_products)
            ).limit(5).all()
            
            for product in similar_products:
                recommendations.append({
                    "type": "product",
                    "product_id": product.id,
                    "name": product.name,
                    "price": float(product.price_ngn),
                    "reason": "Based on your purchase history"
                })
        
        return recommendations
    
    async def _update_customer_profile(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Update customer profile information"""
        customer_id = payload.get("customer_id")
        updates = payload.get("updates", {})
        
        if not customer_id:
            return {
                "success": False,
                "message": "customer_id is required"
            }
        
        db = SessionLocal()
        try:
            customer = db.query(Customer).filter(Customer.id == customer_id).first()
            if not customer:
                return {
                    "success": False,
                    "message": "Customer not found"
                }
            
            # Update allowed fields
            allowed_fields = ["full_name", "phone", "email", "language"]
            updated_fields = []
            
            for field, value in updates.items():
                if field in allowed_fields and hasattr(customer, field):
                    setattr(customer, field, value)
                    updated_fields.append(field)
            
            if updated_fields:
                db.commit()
                return {
                    "success": True,
                    "customer_id": customer_id,
                    "updated_fields": updated_fields,
                    "message": f"Updated {len(updated_fields)} fields successfully"
                }
            else:
                return {
                    "success": False,
                    "message": "No valid fields to update"
                }
            
        finally:
            db.close()
    
    async def _track_customer_interactions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Track customer interactions across channels"""
        customer_id = payload.get("customer_id")
        
        if not customer_id:
            return {
                "success": False,
                "message": "customer_id is required"
            }
        
        db = SessionLocal()
        try:
            # Get chat interactions
            chat_sessions = db.query(ChatSession).filter(ChatSession.user_id == customer_id).all()
            
            # Get order interactions
            orders = db.query(Order).filter(Order.customer_id == customer_id).all()
            
            # Analyze interaction patterns
            total_chat_sessions = len(chat_sessions)
            total_orders = len(orders)
            
            # Get recent interactions
            recent_chats = [s for s in chat_sessions if (datetime.utcnow() - s.created_at).days <= 30]
            recent_orders = [o for o in orders if (datetime.utcnow() - o.created_at).days <= 30]
            
            interaction_summary = {
                "total_chat_sessions": total_chat_sessions,
                "total_orders": total_orders,
                "recent_chats_30d": len(recent_chats),
                "recent_orders_30d": len(recent_orders),
                "engagement_score": self._calculate_engagement_score(total_chat_sessions, total_orders)
            }
            
            return {
                "success": True,
                "customer_id": customer_id,
                "interaction_summary": interaction_summary
            }
            
        finally:
            db.close()
    
    def _calculate_engagement_score(self, chat_sessions: int, orders: int) -> float:
        """Calculate customer engagement score"""
        # Simple scoring algorithm
        chat_score = min(chat_sessions * 0.1, 1.0)
        order_score = min(orders * 0.05, 1.0)
        return round((chat_score + order_score) / 2, 2)
    
    async def _predict_customer_churn(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Predict customer churn risk"""
        customer_id = payload.get("customer_id")
        
        if not customer_id:
            return {
                "success": False,
                "message": "customer_id is required"
            }
        
        db = SessionLocal()
        try:
            customer = db.query(Customer).filter(Customer.id == customer_id).first()
            if not customer:
                return {
                    "success": False,
                    "message": "Customer not found"
                }
            
            # Get customer's order history
            orders = db.query(Order).filter(Order.customer_id == customer_id).all()
            
            if not orders:
                return {
                    "success": True,
                    "customer_id": customer_id,
                    "churn_risk": "unknown",
                    "risk_score": 0.0,
                    "factors": ["No purchase history"]
                }
            
            # Calculate churn risk factors
            current_date = datetime.utcnow()
            last_order_date = max(o.created_at for o in orders)
            days_since_last_order = (current_date - last_order_date).days
            
            total_orders = len(orders)
            total_value = sum(float(o.total or 0) for o in orders)
            
            # Simple churn prediction model
            risk_factors = []
            risk_score = 0.0
            
            if days_since_last_order > 90:
                risk_factors.append("No recent orders")
                risk_score += 0.4
            
            if total_orders < 3:
                risk_factors.append("Low order frequency")
                risk_score += 0.3
            
            if total_value < 50000:
                risk_factors.append("Low lifetime value")
                risk_score += 0.2
            
            # Get chat engagement
            chat_sessions = db.query(ChatSession).filter(ChatSession.user_id == customer_id).all()
            if len(chat_sessions) == 0:
                risk_factors.append("No customer service interactions")
                risk_score += 0.1
            
            # Determine risk level
            if risk_score >= 0.7:
                churn_risk = "high"
            elif risk_score >= 0.4:
                churn_risk = "medium"
            else:
                churn_risk = "low"
            
            return {
                "success": True,
                "customer_id": customer_id,
                "churn_risk": churn_risk,
                "risk_score": round(risk_score, 2),
                "factors": risk_factors,
                "days_since_last_order": days_since_last_order,
                "total_orders": total_orders,
                "total_value": total_value
            }
            
        finally:
            db.close()
    
    async def _generate_customer_insights(self, customer: Customer, orders: List[Order], 
                                        product_counts: Dict[str, int], 
                                        behavior_patterns: List[str]) -> str:
        """Generate AI-powered customer insights"""
        try:
            prompt = f"""
            Analyze this customer data and provide insights:
            
            Customer: {customer.full_name}
            Total Orders: {len(orders)}
            Total Value: {sum(float(o.total or 0) for o in orders):,.2f} NGN
            Top Products: {list(product_counts.keys())[:3]}
            Behavior Patterns: {behavior_patterns}
            
            Provide 2-3 key insights about this customer's behavior and preferences.
            """
            
            response = await self.llm_client.complete(
                prompt=prompt,
                system="You are a customer analytics expert. Provide clear, actionable insights about customer behavior.",
                temperature=0.3,
                max_tokens=150
            )
            
            return response
            
        except Exception:
            return f"Customer shows {', '.join(behavior_patterns)} patterns with {len(orders)} total orders."
    
    async def _general_crm_query(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general CRM queries using LLM"""
        query = payload.get("message", "")
        
        # Use LLM to generate response
        response = await self.llm_client.complete(
            prompt=f"User query about CRM: {query}",
            system="You are a CRM expert. Help users understand customer management, segmentation, and analytics.",
            temperature=0.3
        )
        
        return {
            "success": True,
            "response": response,
            "type": "llm_response"
        }


# Create global instance
crm_agent = CRMAgent()
