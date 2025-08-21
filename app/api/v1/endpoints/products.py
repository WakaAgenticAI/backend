from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.products import Product
from app.schemas.products import ProductIn, ProductOut, ProductUpdate
from app.core.deps import require_roles
from app.core.audit import audit_log

router = APIRouter()


@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("Admin", "Ops"))])
def create_product(body: ProductIn, db: Session = Depends(get_db)) -> ProductOut:
    # enforce unique sku
    if db.query(Product).filter(Product.sku == body.sku).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SKU already exists")
    prod = Product(
        sku=body.sku,
        name=body.name,
        unit=body.unit,
        price_ngn=body.price_ngn,
        tax_rate=body.tax_rate,
    )
    db.add(prod)
    db.commit()
    db.refresh(prod)
    audit_log(action="create", entity="product", entity_id=prod.id, data={"sku": prod.sku})
    return ProductOut(
        id=prod.id,
        sku=prod.sku,
        name=prod.name,
        unit=prod.unit,
        price_ngn=float(prod.price_ngn),
        tax_rate=float(prod.tax_rate),
    )


@router.get("/products", response_model=list[ProductOut], dependencies=[Depends(require_roles("Admin", "Ops", "Sales"))])
def list_products(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    sku: str | None = None,
    q: str | None = Query(None, description="search in name or sku"),
) -> list[ProductOut]:
    query = db.query(Product)
    if sku:
        query = query.filter(Product.sku == sku)
    if q:
        like = f"%{q}%"
        query = query.filter((Product.name.ilike(like)) | (Product.sku.ilike(like)))
    prods = query.order_by(Product.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return [
        ProductOut(
            id=p.id,
            sku=p.sku,
            name=p.name,
            unit=p.unit,
            price_ngn=float(p.price_ngn),
            tax_rate=float(p.tax_rate),
        )
        for p in prods
    ]


@router.patch("/products/{product_id}", response_model=ProductOut, dependencies=[Depends(require_roles("Admin", "Ops"))])
def update_product(product_id: int, body: ProductUpdate, db: Session = Depends(get_db)) -> ProductOut:
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if body.name is not None:
        p.name = body.name
    if body.unit is not None:
        p.unit = body.unit
    if body.price_ngn is not None:
        p.price_ngn = body.price_ngn
    if body.tax_rate is not None:
        p.tax_rate = body.tax_rate
    db.commit()
    db.refresh(p)
    audit_log(action="update", entity="product", entity_id=p.id, data={"fields": body.dict(exclude_none=True)})
    return ProductOut(id=p.id, sku=p.sku, name=p.name, unit=p.unit, price_ngn=float(p.price_ngn), tax_rate=float(p.tax_rate))


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles("Admin", "Ops"))])
def delete_product(product_id: int, db: Session = Depends(get_db)) -> None:
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        return
    db.delete(p)
    db.commit()
    audit_log(action="delete", entity="product", entity_id=product_id)
