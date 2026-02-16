from __future__ import annotations
import pytest
from decimal import Decimal
from datetime import date

from sqlalchemy import inspect

from app.services.debt_service import create_debt, get_debt, DebtNotFound
from app.schemas.debts import DebtIn
from app.db.session import SessionLocal, _engine as engine
from app.models.debts import Debt, DebtPayment
from app.models.base import Base


@pytest.fixture(autouse=True, scope="module")
def _ensure_debt_tables():
    """Create debts/debt_payments tables if they don't exist."""
    inspector = inspect(engine)
    existing = inspector.get_table_names()
    if "debts" not in existing or "debt_payments" not in existing:
        Debt.__table__.create(engine, checkfirst=True)
        DebtPayment.__table__.create(engine, checkfirst=True)


def test_create_debt(db_session):
    """Test creating a debt record."""
    data = DebtIn(
        type="receivable",
        entity_type="customer",
        entity_id=1,
        amount_ngn=Decimal("1000.00"),
        description="Test debt",
        due_date=date.today(),
        priority="medium"
    )

    debt = create_debt(db_session, data)

    assert debt.type == "receivable"
    assert debt.entity_type == "customer"
    assert debt.amount_ngn == Decimal("1000.00")
    assert debt.status == "pending"


def test_get_debt(db_session):
    """Test retrieving a debt by ID."""
    data = DebtIn(
        type="payable",
        entity_type="supplier",
        amount_ngn=Decimal("500.00"),
        description="Supplier payment"
    )

    created = create_debt(db_session, data)
    retrieved = get_debt(db_session, created.id)

    assert retrieved.id == created.id
    assert retrieved.type == "payable"
    assert retrieved.amount_ngn == Decimal("500.00")


def test_get_debt_not_found(db_session):
    """Test getting a non-existent debt raises DebtNotFound."""
    with pytest.raises(DebtNotFound):
        get_debt(db_session, 9999)
