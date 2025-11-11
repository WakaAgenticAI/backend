from __future__ import annotations
from typing import List, Optional
from decimal import Decimal
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_

from app.schemas.debts import DebtIn, DebtUpdate, DebtOut, DebtPaymentIn, DebtPaymentOut, DebtAgingReport, DebtSummary
from app.models.debts import Debt, DebtPayment


class DebtNotFound(Exception):
    pass


class InvalidDebtOperation(Exception):
    pass


def create_debt(db: Session, data: DebtIn) -> DebtOut:
    """Create a new debt record."""
    debt = Debt(
        type=data.type,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        amount_ngn=data.amount_ngn,
        currency=data.currency,
        description=data.description,
        due_date=data.due_date,
        priority=data.priority,
    )
    db.add(debt)
    db.commit()
    db.refresh(debt)
    return DebtOut.from_orm(debt)


def get_debt(db: Session, debt_id: int) -> DebtOut:
    """Get a debt by ID."""
    debt = db.execute(select(Debt).where(Debt.id == debt_id)).scalar_one_or_none()
    if not debt:
        raise DebtNotFound(f"Debt {debt_id} not found")
    return DebtOut.from_orm(debt)


def list_debts(
    db: Session,
    type_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    due_before: Optional[date] = None,
    due_after: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[DebtOut]:
    """List debts with optional filters."""
    query = select(Debt)

    if type_filter:
        query = query.where(Debt.type == type_filter)
    if status_filter:
        query = query.where(Debt.status == status_filter)
    if entity_type:
        query = query.where(Debt.entity_type == entity_type)
    if entity_id:
        query = query.where(Debt.entity_id == entity_id)
    if due_before:
        query = query.where(Debt.due_date <= due_before)
    if due_after:
        query = query.where(Debt.due_date >= due_after)

    query = query.offset(skip).limit(limit).order_by(Debt.due_date.asc(), Debt.id.asc())
    debts = db.execute(query).scalars().all()
    return [DebtOut.from_orm(debt) for debt in debts]


def update_debt(db: Session, debt_id: int, data: DebtUpdate) -> DebtOut:
    """Update a debt record."""
    debt = db.execute(select(Debt).where(Debt.id == debt_id)).scalar_one_or_none()
    if not debt:
        raise DebtNotFound(f"Debt {debt_id} not found")

    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(debt, key, value)

    # Auto-update status if overdue
    if debt.due_date and debt.due_date < date.today() and debt.status in ['pending', 'partial']:
        debt.status = 'overdue'

    debt.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(debt)
    return DebtOut.from_orm(debt)


def delete_debt(db: Session, debt_id: int) -> None:
    """Delete a debt record."""
    debt = db.execute(select(Debt).where(Debt.id == debt_id)).scalar_one_or_none()
    if not debt:
        raise DebtNotFound(f"Debt {debt_id} not found")

    db.delete(debt)
    db.commit()


def add_payment(db: Session, debt_id: int, data: DebtPaymentIn) -> DebtPaymentOut:
    """Add a payment to a debt."""
    debt = db.execute(select(Debt).where(Debt.id == debt_id)).scalar_one_or_none()
    if not debt:
        raise DebtNotFound(f"Debt {debt_id} not found")

    # Calculate total paid so far
    total_paid = db.execute(
        select(func.sum(DebtPayment.amount_ngn)).where(DebtPayment.debt_id == debt_id)
    ).scalar() or Decimal("0.00")

    if total_paid + data.amount_ngn > debt.amount_ngn:
        raise InvalidDebtOperation("Payment amount exceeds remaining debt")

    payment = DebtPayment(
        debt_id=debt_id,
        amount_ngn=data.amount_ngn,
        payment_date=data.payment_date,
        payment_method=data.payment_method,
        notes=data.notes,
    )
    db.add(payment)

    # Update debt status
    new_total_paid = total_paid + data.amount_ngn
    if new_total_paid >= debt.amount_ngn:
        debt.status = 'paid'
    else:
        debt.status = 'partial'

    debt.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(payment)
    return DebtPaymentOut.from_orm(payment)


def get_debt_aging_report(db: Session) -> DebtAgingReport:
    """Generate debt aging report."""
    today = date.today()

    # Calculate ranges
    range_0_30 = db.execute(
        select(func.count(Debt.id)).where(
            and_(
                Debt.status.in_(['pending', 'partial', 'overdue']),
                Debt.due_date >= today - timedelta(days=30),
                Debt.due_date <= today
            )
        )
    ).scalar() or 0

    range_31_60 = db.execute(
        select(func.count(Debt.id)).where(
            and_(
                Debt.status.in_(['pending', 'partial', 'overdue']),
                Debt.due_date >= today - timedelta(days=60),
                Debt.due_date < today - timedelta(days=30)
            )
        )
    ).scalar() or 0

    range_61_90 = db.execute(
        select(func.count(Debt.id)).where(
            and_(
                Debt.status.in_(['pending', 'partial', 'overdue']),
                Debt.due_date >= today - timedelta(days=90),
                Debt.due_date < today - timedelta(days=60)
            )
        )
    ).scalar() or 0

    range_90_plus = db.execute(
        select(func.count(Debt.id)).where(
            and_(
                Debt.status.in_(['pending', 'partial', 'overdue']),
                Debt.due_date < today - timedelta(days=90)
            )
        )
    ).scalar() or 0

    total_overdue_amount = db.execute(
        select(func.sum(Debt.amount_ngn)).where(
            and_(
                Debt.status.in_(['pending', 'partial', 'overdue']),
                Debt.due_date < today
            )
        )
    ).scalar() or Decimal("0.00")

    total_debts = db.execute(select(func.count(Debt.id))).scalar() or 0
    total_amount = db.execute(select(func.sum(Debt.amount_ngn))).scalar() or Decimal("0.00")

    return DebtAgingReport(
        range_0_30=range_0_30,
        range_31_60=range_31_60,
        range_61_90=range_61_90,
        range_90_plus=range_90_plus,
        total_overdue_amount=total_overdue_amount,
        total_debts=total_debts,
        total_amount=total_amount,
    )


def get_debt_summary(db: Session) -> DebtSummary:
    """Get debt summary statistics."""
    receivables_total = db.execute(
        select(func.sum(Debt.amount_ngn)).where(Debt.type == 'receivable')
    ).scalar() or Decimal("0.00")

    payables_total = db.execute(
        select(func.sum(Debt.amount_ngn)).where(Debt.type == 'payable')
    ).scalar() or Decimal("0.00")

    receivables_count = db.execute(
        select(func.count(Debt.id)).where(Debt.type == 'receivable')
    ).scalar() or 0

    payables_count = db.execute(
        select(func.count(Debt.id)).where(Debt.type == 'payable')
    ).scalar() or 0

    today = date.today()
    overdue_receivables = db.execute(
        select(func.count(Debt.id)).where(
            and_(
                Debt.type == 'receivable',
                Debt.status.in_(['pending', 'partial', 'overdue']),
                Debt.due_date < today
            )
        )
    ).scalar() or 0

    overdue_payables = db.execute(
        select(func.count(Debt.id)).where(
            and_(
                Debt.type == 'payable',
                Debt.status.in_(['pending', 'partial', 'overdue']),
                Debt.due_date < today
            )
        )
    ).scalar() or 0

    return DebtSummary(
        receivables_total=receivables_total,
        payables_total=payables_total,
        receivables_count=receivables_count,
        payables_count=payables_count,
        overdue_receivables=overdue_receivables,
        overdue_payables=overdue_payables,
    )


def update_overdue_statuses(db: Session) -> int:
    """Update debts that are now overdue. Returns number of updated debts."""
    today = date.today()
    result = db.execute(
        select(Debt).where(
            and_(
                Debt.status.in_(['pending', 'partial']),
                Debt.due_date < today
            )
        )
    )
    overdue_debts = result.scalars().all()

    for debt in overdue_debts:
        debt.status = 'overdue'
        debt.updated_at = datetime.utcnow()

    db.commit()
    return len(overdue_debts)
