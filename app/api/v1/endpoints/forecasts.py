from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.models.forecasts import Forecast
from app.core.deps import get_current_user
from app.models.users import User

router = APIRouter()


@router.get("/forecasts")
async def get_forecasts(
    product_id: Optional[int] = Query(None),
    warehouse_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get inventory forecasts.
    
    Query parameters:
    - product_id: Filter by product ID
    - warehouse_id: Filter by warehouse ID
    """
    query = db.query(Forecast)
    
    if product_id:
        query = query.filter(Forecast.product_id == product_id)
    
    if warehouse_id:
        query = query.filter(Forecast.warehouse_id == warehouse_id)
    
    forecasts = query.order_by(Forecast.generated_at.desc()).limit(10).all()
    
    result = []
    for forecast in forecasts:
        result.append({
            "id": forecast.id,
            "product_id": forecast.product_id,
            "warehouse_id": forecast.warehouse_id,
            "horizon_days": forecast.horizon_days,
            "generated_at": forecast.generated_at.isoformat(),
            "data": forecast.data_json,
            "trend": forecast.data_json.get("trend", "unknown"),
            "confidence": forecast.data_json.get("confidence", 0),
            "reorder_alert": forecast.data_json.get("confidence", 0) < 0.5
        })
    
    return result
