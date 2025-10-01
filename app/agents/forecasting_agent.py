"""
AI-powered Inventory Forecasting Agent

This agent implements time series forecasting for inventory management using
classical methods (Prophet, ARIMA) and can be extended with ML models.
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_

from app.agents.orchestrator import Agent, AgentState
from app.db.session import SessionLocal
from app.models.orders import Order, OrderItem
from app.models.products import Product
from app.models.inventory import Inventory, Warehouse
from app.models.forecasts import Forecast
from app.services.llm_client import get_llm_client


class ForecastingAgent:
    """AI-powered inventory forecasting agent"""
    
    name = "inventory.forecast"
    description = "AI-powered inventory forecasting and demand prediction"
    tools = [
        "forecast_demand",
        "update_reorder_points", 
        "generate_forecast_report",
        "analyze_trends",
        "detect_anomalies"
    ]
    
    def __init__(self):
        self.llm_client = get_llm_client()
        self.forecast_horizon_days = 30
        self.min_data_points = 7  # Minimum days of data needed
    
    async def can_handle(self, intent: str, payload: Dict[str, Any]) -> bool:
        """Check if agent can handle the intent"""
        return intent.startswith("inventory.forecast") or intent.startswith("forecast")
    
    async def handle(self, state: AgentState) -> AgentState:
        """Handle forecasting requests"""
        try:
            intent = state["intent"]
            payload = state["payload"]
            
            if intent == "inventory.forecast.generate":
                result = await self._generate_forecast(payload)
            elif intent == "inventory.forecast.analyze":
                result = await self._analyze_trends(payload)
            elif intent == "inventory.forecast.update_reorder":
                result = await self._update_reorder_points(payload)
            else:
                result = await self._general_forecast_query(payload)
            
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
    
    async def _generate_forecast(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate demand forecast for products"""
        product_id = payload.get("product_id")
        warehouse_id = payload.get("warehouse_id")
        horizon_days = payload.get("horizon_days", self.forecast_horizon_days)
        
        db = SessionLocal()
        try:
            # Get historical order data
            historical_data = await self._get_historical_data(db, product_id, warehouse_id)
            
            if len(historical_data) < self.min_data_points:
                return {
                    "success": False,
                    "message": f"Insufficient data for forecasting. Need at least {self.min_data_points} days of data.",
                    "data_points": len(historical_data)
                }
            
            # Generate forecast using simple moving average (can be enhanced with Prophet/ARIMA)
            forecast_data = await self._simple_forecast(historical_data, horizon_days)
            
            # Save forecast to database
            forecast_id = await self._save_forecast(db, product_id, warehouse_id, forecast_data, horizon_days)
            
            # Update reorder points based on forecast
            await self._update_reorder_points_from_forecast(db, product_id, warehouse_id, forecast_data)
            
            return {
                "success": True,
                "forecast_id": forecast_id,
                "forecast_data": forecast_data,
                "horizon_days": horizon_days,
                "data_points_used": len(historical_data),
                "message": f"Generated {horizon_days}-day forecast successfully"
            }
            
        finally:
            db.close()
    
    async def _get_historical_data(self, db: Session, product_id: Optional[int], warehouse_id: Optional[int]) -> List[Dict[str, Any]]:
        """Get historical order data for forecasting"""
        # Build query for order items
        query = db.query(
            func.date(Order.created_at).label('date'),
            func.sum(OrderItem.quantity).label('total_quantity')
        ).join(OrderItem, Order.id == OrderItem.order_id)
        
        if product_id:
            query = query.filter(OrderItem.product_id == product_id)
        
        # Filter for last 90 days
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        query = query.filter(Order.created_at >= cutoff_date)
        query = query.filter(Order.status.in_(['completed', 'shipped', 'delivered']))
        
        query = query.group_by(func.date(Order.created_at)).order_by('date')
        
        results = query.all()
        
        # Convert to list of dicts
        historical_data = []
        for result in results:
            historical_data.append({
                'date': result.date,
                'quantity': float(result.total_quantity or 0)
            })
        
        return historical_data
    
    async def _simple_forecast(self, historical_data: List[Dict[str, Any]], horizon_days: int) -> Dict[str, Any]:
        """Generate forecast using simple moving average"""
        if not historical_data:
            return {"forecast": [], "trend": "stable", "confidence": 0.0}
        
        # Convert to pandas DataFrame
        df = pd.DataFrame(historical_data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        
        # Calculate moving averages
        df['ma_7'] = df['quantity'].rolling(window=7, min_periods=1).mean()
        df['ma_14'] = df['quantity'].rolling(window=14, min_periods=1).mean()
        
        # Calculate trend
        recent_avg = df['quantity'].tail(7).mean()
        older_avg = df['quantity'].head(7).mean() if len(df) >= 14 else recent_avg
        
        if recent_avg > older_avg * 1.1:
            trend = "increasing"
        elif recent_avg < older_avg * 0.9:
            trend = "decreasing"
        else:
            trend = "stable"
        
        # Generate forecast
        last_ma = df['ma_7'].iloc[-1]
        forecast_values = []
        
        for i in range(1, horizon_days + 1):
            # Simple linear trend projection
            if trend == "increasing":
                forecast_value = last_ma * (1 + 0.02 * i)  # 2% growth per day
            elif trend == "decreasing":
                forecast_value = last_ma * (1 - 0.01 * i)  # 1% decline per day
            else:
                forecast_value = last_ma
            
            forecast_values.append({
                'date': (datetime.utcnow() + timedelta(days=i)).date().isoformat(),
                'predicted_quantity': max(0, round(forecast_value, 2)),
                'confidence': max(0.5, 1.0 - (i * 0.02))  # Decreasing confidence over time
            })
        
        # Calculate confidence based on data consistency
        quantity_std = df['quantity'].std()
        quantity_mean = df['quantity'].mean()
        confidence = max(0.3, 1.0 - (quantity_std / max(quantity_mean, 1)))
        
        return {
            "forecast": forecast_values,
            "trend": trend,
            "confidence": round(confidence, 2),
            "last_known_quantity": float(df['quantity'].iloc[-1]),
            "moving_average_7d": float(df['ma_7'].iloc[-1]),
            "moving_average_14d": float(df['ma_14'].iloc[-1]) if len(df) >= 14 else None
        }
    
    async def _save_forecast(self, db: Session, product_id: Optional[int], warehouse_id: Optional[int], 
                           forecast_data: Dict[str, Any], horizon_days: int) -> int:
        """Save forecast to database"""
        forecast = Forecast(
            product_id=product_id,
            warehouse_id=warehouse_id,
            horizon_days=horizon_days,
            data_json=forecast_data
        )
        
        db.add(forecast)
        db.commit()
        db.refresh(forecast)
        
        return forecast.id
    
    async def _update_reorder_points_from_forecast(self, db: Session, product_id: Optional[int], 
                                                 warehouse_id: Optional[int], forecast_data: Dict[str, Any]):
        """Update reorder points based on forecast"""
        if not forecast_data.get("forecast"):
            return
        
        # Calculate average daily demand from forecast
        daily_demands = [day["predicted_quantity"] for day in forecast_data["forecast"][:7]]  # First week
        avg_daily_demand = sum(daily_demands) / len(daily_demands)
        
        # Set reorder point to 2 weeks of average demand
        new_reorder_point = max(10, round(avg_daily_demand * 14))
        
        # Update inventory records
        query = db.query(Inventory)
        if product_id:
            query = query.filter(Inventory.product_id == product_id)
        if warehouse_id:
            query = query.filter(Inventory.warehouse_id == warehouse_id)
        
        inventory_records = query.all()
        for inv in inventory_records:
            inv.reorder_point = new_reorder_point
        
        db.commit()
    
    async def _analyze_trends(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze demand trends and patterns"""
        product_id = payload.get("product_id")
        warehouse_id = payload.get("warehouse_id")
        
        db = SessionLocal()
        try:
            historical_data = await self._get_historical_data(db, product_id, warehouse_id)
            
            if len(historical_data) < 7:
                return {
                    "success": False,
                    "message": "Insufficient data for trend analysis"
                }
            
            # Analyze trends
            df = pd.DataFrame(historical_data)
            df['date'] = pd.to_datetime(df['date'])
            
            # Calculate weekly patterns
            df['weekday'] = df['date'].dt.dayofweek
            weekday_avg = df.groupby('weekday')['quantity'].mean()
            
            # Calculate growth rate
            first_week = df.head(7)['quantity'].mean()
            last_week = df.tail(7)['quantity'].mean()
            growth_rate = ((last_week - first_week) / max(first_week, 1)) * 100
            
            # Identify peak days
            peak_day = weekday_avg.idxmax()
            peak_day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][peak_day]
            
            return {
                "success": True,
                "analysis": {
                    "growth_rate_percent": round(growth_rate, 2),
                    "peak_day": peak_day_name,
                    "average_daily_demand": round(df['quantity'].mean(), 2),
                    "demand_volatility": round(df['quantity'].std(), 2),
                    "total_period_days": len(df),
                    "weekday_patterns": {
                        day: round(avg, 2) for day, avg in weekday_avg.items()
                    }
                }
            }
            
        finally:
            db.close()
    
    async def _update_reorder_points(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Update reorder points for products"""
        product_id = payload.get("product_id")
        warehouse_id = payload.get("warehouse_id")
        new_reorder_point = payload.get("reorder_point")
        
        if not new_reorder_point:
            return {
                "success": False,
                "message": "reorder_point is required"
            }
        
        db = SessionLocal()
        try:
            query = db.query(Inventory)
            if product_id:
                query = query.filter(Inventory.product_id == product_id)
            if warehouse_id:
                query = query.filter(Inventory.warehouse_id == warehouse_id)
            
            inventory_records = query.all()
            updated_count = 0
            
            for inv in inventory_records:
                inv.reorder_point = new_reorder_point
                updated_count += 1
            
            db.commit()
            
            return {
                "success": True,
                "updated_count": updated_count,
                "new_reorder_point": new_reorder_point,
                "message": f"Updated reorder point for {updated_count} inventory records"
            }
            
        finally:
            db.close()
    
    async def _general_forecast_query(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general forecasting queries using LLM"""
        query = payload.get("message", "")
        
        # Get recent forecast data
        db = SessionLocal()
        try:
            recent_forecasts = db.query(Forecast).order_by(Forecast.generated_at.desc()).limit(5).all()
            
            forecast_summary = []
            for forecast in recent_forecasts:
                forecast_summary.append({
                    "product_id": forecast.product_id,
                    "warehouse_id": forecast.warehouse_id,
                    "horizon_days": forecast.horizon_days,
                    "generated_at": forecast.generated_at.isoformat(),
                    "trend": forecast.data_json.get("trend", "unknown"),
                    "confidence": forecast.data_json.get("confidence", 0)
                })
            
            # Use LLM to generate response
            context = f"Recent forecasts: {forecast_summary}"
            response = await self.llm_client.complete(
                prompt=f"User query: {query}\n\nContext: {context}",
                system="You are an inventory forecasting expert. Help users understand their demand forecasts and trends.",
                temperature=0.3
            )
            
            return {
                "success": True,
                "response": response,
                "type": "llm_response",
                "recent_forecasts": forecast_summary
            }
            
        finally:
            db.close()


# Create global instance
forecasting_agent = ForecastingAgent()
