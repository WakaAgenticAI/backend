"""Comprehensive tests for app/services/debt_service.py — covers all functions."""
from __future__ import annotations
import pytest
from decimal import Decimal
from datetime import date, timedelta

from sqlalchemy import inspect

from app.services.debt_service import (
    create_debt, get_debt, list_debts, update_debt, delete_debt,
    add_payment, get_debt_aging_report, get_debt_summary,
    update_overdue_statuses, DebtNotFound, InvalidDebtOperation,
)
from app.schemas.debts import DebtIn, DebtUpdate, DebtPaymentIn
from app.db.session import SessionLocal, _engine as engine
from app.models.debts import Debt, DebtPayment
from app.models.base import Base


@pytest.fixture(autouse=True, scope="module")
def _ensure_debt_tables():
    inspector = inspect(engine)
    existing = inspector.get_table_names()
    if "debts" not in existing or "debt_payments" not in existing:
        Debt.__table__.create(engine, checkfirst=True)
        DebtPayment.__table__.create(engine, checkfirst=True)


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _make_debt(db, dtype="receivable", amount="1000.00", due_days=30, status="pending"):
    data = DebtIn(
        type=dtype,
        entity_type="customer",
        entity_id=1,
        amount_ngn=Decimal(amount),
        description="test",
        due_date=date.today() + timedelta(days=due_days),
        priority="medium",
    )
    return create_debt(db, data)


# ── create_debt ──────────────────────────────────────────────

def test_create_receivable(db):
    out = _make_debt(db, dtype="receivable")
    assert out.type == "receivable"
    assert out.status == "pending"
    assert out.amount_ngn == Decimal("1000.00")


def test_create_payable(db):
    out = _make_debt(db, dtype="payable", amount="500.00")
    assert out.type == "payable"
    assert out.amount_ngn == Decimal("500.00")


# ── get_debt ─────────────────────────────────────────────────

def test_get_debt_success(db):
    created = _make_debt(db)
    fetched = get_debt(db, created.id)
    assert fetched.id == created.id
    assert fetched.type == created.type


def test_get_debt_not_found(db):
    with pytest.raises(DebtNotFound):
        get_debt(db, 999999)


# ── list_debts ───────────────────────────────────────────────

def test_list_debts_no_filter(db):
    _make_debt(db)
    results = list_debts(db)
    assert len(results) >= 1


def test_list_debts_type_filter(db):
    _make_debt(db, dtype="receivable")
    results = list_debts(db, type_filter="receivable")
    assert all(d.type == "receivable" for d in results)


def test_list_debts_status_filter(db):
    _make_debt(db)
    results = list_debts(db, status_filter="pending")
    assert all(d.status == "pending" for d in results)


def test_list_debts_entity_filter(db):
    _make_debt(db)
    results = list_debts(db, entity_type="customer", entity_id=1)
    assert all(d.entity_type == "customer" for d in results)


def test_list_debts_due_date_filter(db):
    _make_debt(db, due_days=10)
    before = date.today() + timedelta(days=15)
    after = date.today()
    results = list_debts(db, due_before=before, due_after=after)
    assert isinstance(results, list)


def test_list_debts_pagination(db):
    for _ in range(3):
        _make_debt(db)
    page = list_debts(db, skip=0, limit=2)
    assert len(page) <= 2


# ── update_debt ──────────────────────────────────────────────

def test_update_debt_status(db):
    created = _make_debt(db)
    updated = update_debt(db, created.id, DebtUpdate(status="partial"))
    assert updated.status == "partial"


def test_update_debt_priority(db):
    created = _make_debt(db)
    updated = update_debt(db, created.id, DebtUpdate(priority="high"))
    assert updated.priority == "high"


def test_update_debt_not_found(db):
    with pytest.raises(DebtNotFound):
        update_debt(db, 999999, DebtUpdate(status="paid"))


def test_update_debt_auto_overdue(db):
    """Debt with past due_date and pending status should auto-mark overdue."""
    created = _make_debt(db, due_days=-5)
    updated = update_debt(db, created.id, DebtUpdate(description="trigger update"))
    assert updated.status == "overdue"


# ── delete_debt ──────────────────────────────────────────────

def test_delete_debt_success(db):
    created = _make_debt(db)
    delete_debt(db, created.id)
    with pytest.raises(DebtNotFound):
        get_debt(db, created.id)


def test_delete_debt_not_found(db):
    with pytest.raises(DebtNotFound):
        delete_debt(db, 999999)


# ── add_payment ──────────────────────────────────────────────

def test_add_payment_partial(db):
    created = _make_debt(db, amount="1000.00")
    payment = add_payment(db, created.id, DebtPaymentIn(
        amount_ngn=Decimal("400.00"),
        payment_date=date.today(),
        payment_method="bank_transfer",
        notes="partial payment",
    ))
    assert payment.amount_ngn == Decimal("400.00")
    debt_after = get_debt(db, created.id)
    assert debt_after.status == "partial"


def test_add_payment_full(db):
    created = _make_debt(db, amount="500.00")
    add_payment(db, created.id, DebtPaymentIn(
        amount_ngn=Decimal("500.00"),
        payment_date=date.today(),
    ))
    debt_after = get_debt(db, created.id)
    assert debt_after.status == "paid"


def test_add_payment_exceeds_amount(db):
    created = _make_debt(db, amount="100.00")
    with pytest.raises(InvalidDebtOperation, match="exceeds"):
        add_payment(db, created.id, DebtPaymentIn(
            amount_ngn=Decimal("200.00"),
            payment_date=date.today(),
        ))


def test_add_payment_debt_not_found(db):
    with pytest.raises(DebtNotFound):
        add_payment(db, 999999, DebtPaymentIn(
            amount_ngn=Decimal("10.00"),
            payment_date=date.today(),
        ))


# ── get_debt_aging_report ────────────────────────────────────

def test_aging_report_structure(db):
    _make_debt(db)
    report = get_debt_aging_report(db)
    assert hasattr(report, "range_0_30")
    assert hasattr(report, "range_31_60")
    assert hasattr(report, "range_61_90")
    assert hasattr(report, "range_90_plus")
    assert hasattr(report, "total_overdue_amount")
    assert hasattr(report, "total_debts")
    assert hasattr(report, "total_amount")
    assert report.total_debts >= 1


# ── get_debt_summary ─────────────────────────────────────────

def test_debt_summary_structure(db):
    _make_debt(db, dtype="receivable")
    _make_debt(db, dtype="payable")
    summary = get_debt_summary(db)
    assert hasattr(summary, "receivables_total")
    assert hasattr(summary, "payables_total")
    assert hasattr(summary, "receivables_count")
    assert hasattr(summary, "payables_count")
    assert summary.receivables_count >= 1
    assert summary.payables_count >= 1


def test_debt_summary_overdue_counts(db):
    _make_debt(db, dtype="receivable", due_days=-10)
    summary = get_debt_summary(db)
    assert summary.overdue_receivables >= 0


# ── update_overdue_statuses ──────────────────────────────────

def test_update_overdue_statuses(db):
    _make_debt(db, due_days=-5)
    count = update_overdue_statuses(db)
    assert isinstance(count, int)
    assert count >= 0
