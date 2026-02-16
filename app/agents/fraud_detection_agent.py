"""
AI-powered Fraud Detection Agent

This agent implements fraud detection for orders using rule-based and ML approaches.
It analyzes order patterns, customer behavior, and payment information to detect suspicious activities.
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_

from app.agents.orchestrator import Agent, AgentState
from app.db.session import SessionLocal
from app.models.orders import Order, OrderItem
from app.models.customers import Customer
from app.models.products import Product
from app.services.llm_client import get_llm_client


class FraudDetectionAgent:
    """AI-powered fraud detection agent"""
    
    name = "fraud.detection"
    description = "AI-powered fraud detection and risk assessment for orders"
    tools = [
        "analyze_order_risk",
        "check_customer_history",
        "validate_payment",
        "generate_fraud_report",
        "update_fraud_rules"
    ]
    
    def __init__(self):
        self.llm_client = get_llm_client()
        self.risk_thresholds = {
            "low": 0.3,
            "medium": 0.6,
            "high": 0.8
        }
        
        # Fraud detection rules
        self.fraud_rules = {
            "velocity_check": {
                "max_orders_per_hour": 3,
                "max_orders_per_day": 10,
                "weight": 0.3
            },
            "amount_check": {
                "high_value_threshold": 100000,  # 100k NGN
                "unusual_amount_multiplier": 5,
                "weight": 0.25
            },
            "location_check": {
                "max_distance_km": 1000,
                "weight": 0.2
            },
            "payment_check": {
                "suspicious_payment_methods": ["cash_on_delivery_large"],
                "weight": 0.15
            },
            "customer_check": {
                "new_customer_threshold_days": 7,
                "weight": 0.1
            }
        }
    
    async def can_handle(self, intent: str, payload: Dict[str, Any]) -> bool:
        """Check if agent can handle the intent"""
        return intent.startswith("fraud.") or intent.startswith("payment.validate")
    
    async def handle(self, state: AgentState) -> AgentState:
        """Handle fraud detection requests"""
        try:
            intent = state["intent"]
            payload = state["payload"]
            
            if intent == "fraud.analyze_order":
                result = await self._analyze_order_risk(payload)
            elif intent == "fraud.check_customer":
                result = await self._check_customer_history(payload)
            elif intent == "payment.validate":
                result = await self._validate_payment(payload)
            elif intent == "fraud.generate_report":
                result = await self._generate_fraud_report(payload)
            else:
                result = await self._general_fraud_query(payload)
            
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
    
    async def _analyze_order_risk(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze order for fraud risk"""
        order_id = payload.get("order_id")
        order_data = payload.get("order_data")
        
        if not order_id and not order_data:
            return {
                "success": False,
                "message": "order_id or order_data is required"
            }
        
        db = SessionLocal()
        try:
            # Get order data
            if order_id:
                order = db.query(Order).filter(Order.id == order_id).first()
                if not order:
                    return {
                        "success": False,
                        "message": "Order not found"
                    }
            else:
                order = order_data
            
            # Run fraud checks
            risk_scores = {}
            triggered_rules = []
            
            # Velocity check
            velocity_score, velocity_rules = await self._check_velocity(db, order)
            risk_scores["velocity"] = velocity_score
            triggered_rules.extend(velocity_rules)
            
            # Amount check
            amount_score, amount_rules = await self._check_amount(db, order)
            risk_scores["amount"] = amount_score
            triggered_rules.extend(amount_rules)
            
            # Location check
            location_score, location_rules = await self._check_location(db, order)
            risk_scores["location"] = location_score
            triggered_rules.extend(location_rules)
            
            # Payment check
            payment_score, payment_rules = await self._check_payment(db, order)
            risk_scores["payment"] = payment_score
            triggered_rules.extend(payment_rules)
            
            # Customer check
            customer_score, customer_rules = await self._check_customer(db, order)
            risk_scores["customer"] = customer_score
            triggered_rules.extend(customer_rules)
            
            # Calculate overall risk score
            overall_score = self._calculate_overall_score(risk_scores)
            risk_level = self._determine_risk_level(overall_score)
            
            # Generate AI explanation
            explanation = await self._generate_risk_explanation(risk_scores, triggered_rules, overall_score)
            
            result_order_id = order.id if hasattr(order, 'id') else order_id
            result_amount = float(order.total) if hasattr(order, 'total') else None
            customer_name = None
            if hasattr(order, 'customer') and order.customer:
                customer_name = getattr(order.customer, 'name', None) or getattr(order.customer, 'full_name', None)

            # Send email alert for medium/high risk
            if risk_level in ("medium", "high"):
                try:
                    from app.services.email_service import get_email_service
                    await get_email_service().alert_fraud_detected(
                        order_id=result_order_id,
                        risk_score=overall_score,
                        risk_level=risk_level,
                        factors=triggered_rules,
                        customer_name=customer_name,
                        amount=result_amount,
                    )
                except Exception:
                    pass  # never fail the agent on notification errors

            return {
                "success": True,
                "order_id": result_order_id,
                "risk_level": risk_level,
                "overall_score": round(overall_score, 3),
                "risk_scores": {k: round(v, 3) for k, v in risk_scores.items()},
                "triggered_rules": triggered_rules,
                "explanation": explanation,
                "recommendation": self._get_recommendation(risk_level, triggered_rules)
            }
            
        finally:
            db.close()
    
    async def _check_velocity(self, db: Session, order: Order) -> Tuple[float, List[str]]:
        """Check order velocity patterns"""
        customer_id = order.customer_id
        order_time = order.created_at
        
        # Check orders in last hour
        hour_ago = order_time - timedelta(hours=1)
        orders_last_hour = db.query(Order).filter(
            Order.customer_id == customer_id,
            Order.created_at >= hour_ago,
            Order.created_at <= order_time
        ).count()
        
        # Check orders in last day
        day_ago = order_time - timedelta(days=1)
        orders_last_day = db.query(Order).filter(
            Order.customer_id == customer_id,
            Order.created_at >= day_ago,
            Order.created_at <= order_time
        ).count()
        
        score = 0.0
        triggered_rules = []
        
        if orders_last_hour >= self.fraud_rules["velocity_check"]["max_orders_per_hour"]:
            score += 0.8
            triggered_rules.append(f"High order velocity: {orders_last_hour} orders in last hour")
        
        if orders_last_day >= self.fraud_rules["velocity_check"]["max_orders_per_day"]:
            score += 0.6
            triggered_rules.append(f"High daily order count: {orders_last_day} orders in last day")
        
        return min(score, 1.0), triggered_rules
    
    async def _check_amount(self, db: Session, order: Order) -> Tuple[float, List[str]]:
        """Check order amount patterns"""
        order_total = float(order.total or 0)
        customer_id = order.customer_id
        
        # Get customer's historical order amounts
        historical_orders = db.query(Order).filter(
            Order.customer_id == customer_id,
            Order.id != order.id
        ).all()
        
        score = 0.0
        triggered_rules = []
        
        # Check if order is unusually high value
        if order_total >= self.fraud_rules["amount_check"]["high_value_threshold"]:
            score += 0.7
            triggered_rules.append(f"High value order: ₦{order_total:,.2f}")
        
        # Check if order is unusually large compared to history
        if historical_orders:
            avg_order_value = sum(float(o.total or 0) for o in historical_orders) / len(historical_orders)
            if order_total > avg_order_value * self.fraud_rules["amount_check"]["unusual_amount_multiplier"]:
                score += 0.8
                triggered_rules.append(f"Unusually large order: {order_total/avg_order_value:.1f}x average")
        
        return min(score, 1.0), triggered_rules
    
    async def _check_location(self, db: Session, order: Order) -> Tuple[float, List[str]]:
        """Check location-based fraud patterns"""
        # This is a simplified implementation
        # In production, you'd integrate with geolocation services
        
        score = 0.0
        triggered_rules = []
        
        # Check for suspicious delivery addresses
        # This would typically involve checking against known fraud patterns
        # For now, we'll use a simple heuristic
        
        return score, triggered_rules
    
    async def _check_payment(self, db: Session, order: Order) -> Tuple[float, List[str]]:
        """Check payment method patterns"""
        score = 0.0
        triggered_rules = []
        
        # Check payment method
        # This would typically check against the payments table
        # For now, we'll use order channel as a proxy
        
        if order.channel == "cash_on_delivery" and float(order.total or 0) > 50000:
            score += 0.6
            triggered_rules.append("Large cash on delivery order")
        
        return min(score, 1.0), triggered_rules
    
    async def _check_customer(self, db: Session, order: Order) -> Tuple[float, List[str]]:
        """Check customer history and patterns"""
        customer_id = order.customer_id
        order_time = order.created_at
        
        # Get customer info
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        
        score = 0.0
        triggered_rules = []
        
        if customer:
            # Check if customer is new
            customer_age_days = (order_time - customer.created_at).days
            if customer_age_days <= self.fraud_rules["customer_check"]["new_customer_threshold_days"]:
                score += 0.4
                triggered_rules.append(f"New customer: {customer_age_days} days old")
            
            # Check for missing customer information
            if not customer.phone or not customer.email:
                score += 0.3
                triggered_rules.append("Incomplete customer information")
        
        return min(score, 1.0), triggered_rules
    
    def _calculate_overall_score(self, risk_scores: Dict[str, float]) -> float:
        """Calculate weighted overall risk score"""
        total_score = 0.0
        total_weight = 0.0
        
        for category, score in risk_scores.items():
            weight = self.fraud_rules.get(f"{category}_check", {}).get("weight", 0.1)
            total_score += score * weight
            total_weight += weight
        
        return total_score / max(total_weight, 0.1)
    
    def _determine_risk_level(self, score: float) -> str:
        """Determine risk level from score"""
        if score >= self.risk_thresholds["high"]:
            return "high"
        elif score >= self.risk_thresholds["medium"]:
            return "medium"
        else:
            return "low"
    
    async def _generate_risk_explanation(self, risk_scores: Dict[str, float], 
                                       triggered_rules: List[str], overall_score: float) -> str:
        """Generate AI explanation of risk assessment"""
        try:
            prompt = f"""
            Analyze this fraud risk assessment and provide a clear explanation:
            
            Risk Scores: {risk_scores}
            Triggered Rules: {triggered_rules}
            Overall Score: {overall_score}
            
            Provide a brief, professional explanation of the risk factors and what they mean for this order.
            """
            
            response = await self.llm_client.complete(
                prompt=prompt,
                system="You are a fraud detection expert. Explain risk assessments clearly and professionally.",
                temperature=0.3,
                max_tokens=200
            )
            
            return response
            
        except Exception:
            return f"Risk assessment completed with overall score of {overall_score:.2f}. {len(triggered_rules)} risk factors identified."
    
    def _get_recommendation(self, risk_level: str, triggered_rules: List[str]) -> str:
        """Get recommendation based on risk level"""
        if risk_level == "high":
            return "Recommend manual review and additional verification before processing"
        elif risk_level == "medium":
            return "Recommend enhanced monitoring and verification"
        else:
            return "Order appears safe to process normally"
    
    async def _check_customer_history(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Check customer's fraud history"""
        customer_id = payload.get("customer_id")
        
        if not customer_id:
            return {
                "success": False,
                "message": "customer_id is required"
            }
        
        db = SessionLocal()
        try:
            # Get customer's order history
            orders = db.query(Order).filter(Order.customer_id == customer_id).all()
            
            if not orders:
                return {
                    "success": True,
                    "customer_id": customer_id,
                    "total_orders": 0,
                    "fraud_indicators": [],
                    "risk_level": "unknown"
                }
            
            # Analyze order patterns
            total_orders = len(orders)
            total_value = sum(float(o.total or 0) for o in orders)
            avg_order_value = total_value / total_orders if total_orders > 0 else 0
            
            # Check for suspicious patterns
            fraud_indicators = []
            
            # Check for rapid order creation
            if total_orders > 5:
                recent_orders = [o for o in orders if (datetime.utcnow() - o.created_at).days <= 7]
                if len(recent_orders) > 3:
                    fraud_indicators.append("High recent order frequency")
            
            # Check for unusual order values
            if avg_order_value > 100000:  # 100k NGN average
                fraud_indicators.append("High average order value")
            
            # Determine risk level
            if len(fraud_indicators) >= 2:
                risk_level = "high"
            elif len(fraud_indicators) == 1:
                risk_level = "medium"
            else:
                risk_level = "low"
            
            return {
                "success": True,
                "customer_id": customer_id,
                "total_orders": total_orders,
                "total_value": total_value,
                "avg_order_value": avg_order_value,
                "fraud_indicators": fraud_indicators,
                "risk_level": risk_level
            }
            
        finally:
            db.close()
    
    async def _validate_payment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validate payment information"""
        payment_data = payload.get("payment_data", {})
        order_id = payload.get("order_id")
        
        # This would typically integrate with payment processors
        # For now, we'll implement basic validation
        
        validation_results = {
            "payment_method_valid": True,
            "amount_valid": True,
            "currency_valid": True,
            "risk_factors": []
        }
        
        # Check payment method
        payment_method = payment_data.get("method", "")
        if payment_method in self.fraud_rules["payment_check"]["suspicious_payment_methods"]:
            validation_results["risk_factors"].append("Suspicious payment method")
        
        # Check amount
        amount = payment_data.get("amount", 0)
        if amount > 500000:  # 500k NGN
            validation_results["risk_factors"].append("High payment amount")
        
        return {
            "success": True,
            "order_id": order_id,
            "validation_results": validation_results,
            "recommendation": "Proceed with caution" if validation_results["risk_factors"] else "Payment appears valid"
        }
    
    async def _generate_fraud_report(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate fraud detection report"""
        days = payload.get("days", 30)
        
        db = SessionLocal()
        try:
            # Get orders from the specified period
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            orders = db.query(Order).filter(Order.created_at >= cutoff_date).all()
            
            # Analyze fraud patterns
            total_orders = len(orders)
            high_value_orders = len([o for o in orders if float(o.total or 0) > 100000])
            new_customer_orders = 0  # Would need to join with customer table
            
            # Calculate fraud metrics
            fraud_metrics = {
                "total_orders": total_orders,
                "high_value_orders": high_value_orders,
                "new_customer_orders": new_customer_orders,
                "high_value_percentage": (high_value_orders / max(total_orders, 1)) * 100
            }
            
            return {
                "success": True,
                "report_period_days": days,
                "fraud_metrics": fraud_metrics,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        finally:
            db.close()
    
    async def _general_fraud_query(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general fraud-related queries using LLM"""
        query = payload.get("message", "")
        
        # Use LLM to generate response
        response = await self.llm_client.complete(
            prompt=f"User query about fraud detection: {query}",
            system="You are a fraud detection expert. Help users understand fraud patterns and prevention measures.",
            temperature=0.3
        )
        
        return {
            "success": True,
            "response": response,
            "type": "llm_response"
        }


# Create global instance
fraud_detection_agent = FraudDetectionAgent()
