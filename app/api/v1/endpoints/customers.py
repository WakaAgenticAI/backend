from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import require_roles
from app.models.customers import Customer
from app.schemas.customers import CustomerIn, CustomerOut
from app.core.audit import audit_log

router = APIRouter()


@router.post("/customers", response_model=CustomerOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("Admin", "Sales", "Ops"))])
def create_customer(body: CustomerIn, db: Session = Depends(get_db)) -> CustomerOut:
    # unique email
    if db.query(Customer).filter(Customer.email == body.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
    c = Customer(
        email=body.email,
        name=body.name,
        phone=body.phone,
        segment=body.segment,
        status=body.status,
        location=body.location,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    audit_log(action="create", entity="customer", entity_id=c.id, data={"email": c.email})
    return CustomerOut.model_validate(c)


@router.get("/customers", response_model=list[CustomerOut], dependencies=[Depends(require_roles("Admin", "Sales", "Ops"))])
def list_customers(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    q: str | None = Query(None, description="search by name or email"),
    segment: str | None = None,
    status_f: str | None = Query(None, alias="status"),
) -> list[CustomerOut]:
    query = db.query(Customer)
    if q:
        like = f"%{q}%"
        query = query.filter((Customer.name.ilike(like)) | (Customer.email.ilike(like)))
    if segment:
        query = query.filter(Customer.segment == segment)
    if status_f:
        query = query.filter(Customer.status == status_f)
    rows = query.order_by(Customer.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return [CustomerOut.model_validate(r) for r in rows]
