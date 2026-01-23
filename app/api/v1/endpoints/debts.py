from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.core.deps import require_roles
from app.schemas.debts import DebtIn, DebtUpdate, DebtOut, DebtPaymentIn, DebtPaymentOut, DebtAgingReport, DebtSummary
from app.services.debt_service import (
    create_debt, get_debt, list_debts, update_debt, delete_debt, add_payment,
    get_debt_aging_report, get_debt_summary, update_overdue_statuses,
    DebtNotFound, InvalidDebtOperation
)
from app.core.audit import audit_log

router = APIRouter()


@router.post("/debts", response_model=DebtOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("Admin", "Sales", "Ops"))])
def create_debt_endpoint(body: DebtIn, db: Session = Depends(get_db)) -> DebtOut:
    """Create a new debt record."""
    try:
        debt = create_debt(db, body)
        audit_log(action="create", entity="debt", entity_id=debt.id, data={"type": debt.type, "amount": str(debt.amount_ngn)})
        return debt
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/debts", response_model=List[DebtOut], dependencies=[Depends(require_roles("Admin", "Sales", "Ops"))])
def list_debts_endpoint(
    db: Session = Depends(get_db),
    type_filter: Optional[str] = Query(None, description="Filter by debt type: receivable/payable"),
    status_filter: Optional[str] = Query(None, description="Filter by status: pending/partial/paid/overdue/cancelled"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type: customer/supplier/other"),
    entity_id: Optional[int] = Query(None, description="Filter by entity ID"),
    due_before: Optional[str] = Query(None, description="Due before date (YYYY-MM-DD)"),
    due_after: Optional[str] = Query(None, description="Due after date (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> List[DebtOut]:
    """List debts with optional filters."""
    from datetime import date
    due_before_date = date.fromisoformat(due_before) if due_before else None
    due_after_date = date.fromisoformat(due_after) if due_after else None

    try:
        return list_debts(
            db=db,
            type_filter=type_filter,
            status_filter=status_filter,
            entity_type=entity_type,
            entity_id=entity_id,
            due_before=due_before_date,
            due_after=due_after_date,
            skip=skip,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/debts/{debt_id}", response_model=DebtOut, dependencies=[Depends(require_roles("Admin", "Sales", "Ops"))])
def get_debt_endpoint(debt_id: int, db: Session = Depends(get_db)) -> DebtOut:
    """Get a specific debt by ID."""
    try:
        return get_debt(db, debt_id)
    except DebtNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debt not found")


@router.put("/debts/{debt_id}", response_model=DebtOut, dependencies=[Depends(require_roles("Admin", "Sales", "Ops"))])
def update_debt_endpoint(debt_id: int, body: DebtUpdate, db: Session = Depends(get_db)) -> DebtOut:
    """Update a debt record."""
    try:
        debt = update_debt(db, debt_id, body)
        audit_log(action="update", entity="debt", entity_id=debt.id, data={"status": debt.status})
        return debt
    except DebtNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debt not found")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/debts/{debt_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles("Admin"))], response_class=Response)
def delete_debt_endpoint(debt_id: int, db: Session = Depends(get_db)):
    """Delete a debt record (Admin only)."""
    try:
        delete_debt(db, debt_id)
        audit_log(action="delete", entity="debt", entity_id=debt_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except DebtNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debt not found")


@router.post("/debts/{debt_id}/payments", response_model=DebtPaymentOut, dependencies=[Depends(require_roles("Admin", "Sales", "Ops"))])
def add_payment_endpoint(debt_id: int, body: DebtPaymentIn, db: Session = Depends(get_db)) -> DebtPaymentOut:
    """Add a payment to a debt."""
    try:
        payment = add_payment(db, debt_id, body)
        audit_log(action="create", entity="debt_payment", entity_id=payment.id, data={"debt_id": debt_id, "amount": str(payment.amount_ngn)})
        return payment
    except DebtNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debt not found")
    except InvalidDebtOperation as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/debts/reports/aging", response_model=DebtAgingReport, dependencies=[Depends(require_roles("Admin", "Sales", "Ops"))])
def get_aging_report_endpoint(db: Session = Depends(get_db)) -> DebtAgingReport:
    """Get debt aging report."""
    return get_debt_aging_report(db)


@router.get("/debts/reports/summary", response_model=DebtSummary, dependencies=[Depends(require_roles("Admin", "Sales", "Ops"))])
def get_summary_endpoint(db: Session = Depends(get_db)) -> DebtSummary:
    """Get debt summary statistics."""
    return get_debt_summary(db)


@router.post("/debts/update-overdue", dependencies=[Depends(require_roles("Admin"))])
def update_overdue_endpoint(db: Session = Depends(get_db)) -> dict:
    """Update overdue debt statuses (Admin only)."""
    updated_count = update_overdue_statuses(db)
    return {"updated_count": updated_count, "message": f"Updated {updated_count} debts to overdue status"}
