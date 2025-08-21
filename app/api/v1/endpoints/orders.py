from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from app.schemas.orders import OrderCreate, OrderOut, OrderUpdate
from app.services import orders_service
from app.db.session import get_db
from app.core.deps import require_roles
from app.models.orders import Order
from app.core.audit import audit_log
from app.realtime.emitter import order_updated

router = APIRouter()


@router.post("/orders", response_model=OrderOut, dependencies=[Depends(require_roles("Admin", "Sales"))])
async def create_order(data: OrderCreate, req: Request, db: Session = Depends(get_db)) -> OrderOut:
    try:
        _order_id, out = orders_service.create_order(db, data)
        await order_updated(req.app, _order_id, {"status": "created", "order_id": _order_id})
        return out
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except orders_service.InsufficientStock as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/orders", response_model=list[OrderOut], dependencies=[Depends(require_roles("Admin", "Sales"))])
def list_orders(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    status: str | None = Query(None, description="filter by status"),
    customer_id: int | None = Query(None, ge=1),
) -> list[OrderOut]:
    q = db.query(Order)
    if status:
        q = q.filter(Order.status == status)
    if customer_id:
        q = q.filter(Order.customer_id == customer_id)
    rows = q.order_by(Order.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return [OrderOut(id=o.id, status=o.status, total=float(o.total), currency=o.currency) for o in rows]


@router.get("/orders/{order_id}", response_model=OrderOut, dependencies=[Depends(require_roles("Admin", "Sales"))])
def get_order(order_id: int, db: Session = Depends(get_db)) -> OrderOut:
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return OrderOut(id=o.id, status=o.status, total=float(o.total), currency=o.currency)


@router.post("/orders/{order_id}/fulfill", response_model=OrderOut, dependencies=[Depends(require_roles("Admin", "Ops"))])
async def fulfill_order(order_id: int, req: Request, db: Session = Depends(get_db)) -> OrderOut:
    try:
        o = orders_service.fulfill_order(db, order_id)
        audit_log(action="fulfill", entity="order", entity_id=o.id, data={"status": o.status})
        await order_updated(req.app, o.id, {"status": o.status, "order_id": o.id})
        return OrderOut(id=o.id, status=o.status, total=float(o.total), currency=o.currency)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/orders/{order_id}", response_model=OrderOut, dependencies=[Depends(require_roles("Admin", "Ops", "Sales"))])
async def update_order(order_id: int, body: OrderUpdate, req: Request, db: Session = Depends(get_db)) -> OrderOut:
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    o.status = body.status
    db.commit()
    db.refresh(o)
    audit_log(action="update", entity="order", entity_id=o.id, data={"status": o.status})
    await order_updated(req.app, o.id, {"status": o.status, "order_id": o.id})
    return OrderOut(id=o.id, status=o.status, total=float(o.total), currency=o.currency)
