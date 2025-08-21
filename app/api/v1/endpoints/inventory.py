from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.schemas.inventory import WarehouseCreate, WarehouseOut, InventoryOut
from app.models.inventory import Warehouse, Inventory
from app.models.products import Product

router = APIRouter()


@router.post("/warehouses", response_model=WarehouseOut, dependencies=[Depends(require_roles("Admin", "Ops"))])
def create_warehouse(body: WarehouseCreate, db: Session = Depends(get_db)) -> WarehouseOut:
    wh = Warehouse(name=body.name)
    db.add(wh)
    db.commit()
    db.refresh(wh)
    return WarehouseOut(id=wh.id, name=wh.name)


@router.get("/warehouses", response_model=list[WarehouseOut], dependencies=[Depends(require_roles("Admin", "Ops", "Sales"))])
def list_warehouses(db: Session = Depends(get_db)) -> list[WarehouseOut]:
    rows = db.query(Warehouse).order_by(Warehouse.id.asc()).all()
    return [WarehouseOut(id=w.id, name=w.name) for w in rows]


@router.get("/inventory", response_model=list[InventoryOut], dependencies=[Depends(require_roles("Admin", "Ops", "Sales"))])
def get_inventory(
    db: Session = Depends(get_db),
    warehouse_id: int | None = Query(None, ge=1),
    sku: str | None = Query(None),
) -> list[InventoryOut]:
    q = db.query(Inventory)
    if warehouse_id:
        q = q.filter(Inventory.warehouse_id == warehouse_id)
    if sku:
        q = q.join(Product, Product.id == Inventory.product_id).filter(Product.sku == sku)
    rows = q.all()
    return [
        InventoryOut(product_id=r.product_id, warehouse_id=r.warehouse_id, on_hand=float(r.on_hand or 0), reserved=float(r.reserved or 0))
        for r in rows
    ]
