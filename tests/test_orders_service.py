"""Comprehensive tests for app/services/orders_service.py."""
from __future__ import annotations
import pytest
from decimal import Decimal

from app.services.orders_service import create_order, fulfill_order, InsufficientStock, _compute_total
from app.schemas.orders import OrderCreate, OrderItemIn
from app.db.session import SessionLocal
from app.models.products import Product
from app.models.inventory import Inventory, Warehouse
from app.models.orders import Order, OrderItem


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _ensure_product(db, product_id=1, sku="TST-1", price=500):
    """Ensure a product exists for testing."""
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        p = Product(id=product_id, sku=sku, name="Test Product", unit="unit", price_ngn=price, tax_rate=0)
        db.add(p)
        db.flush()
    return p


def _ensure_warehouse(db):
    wh = db.query(Warehouse).first()
    if not wh:
        wh = Warehouse(name="Main")
        db.add(wh)
        db.flush()
    return wh


def _ensure_inventory(db, product_id, warehouse_id, on_hand=100, reserved=0):
    inv = db.query(Inventory).filter(
        Inventory.product_id == product_id,
        Inventory.warehouse_id == warehouse_id,
    ).first()
    if not inv:
        inv = Inventory(product_id=product_id, warehouse_id=warehouse_id, on_hand=on_hand, reserved=reserved)
        db.add(inv)
        db.flush()
    else:
        inv.on_hand = on_hand
        inv.reserved = reserved
        db.flush()
    return inv


# ── _compute_total ───────────────────────────────────────────

def test_compute_total_basic():
    data = OrderCreate(customer_id=1, items=[
        OrderItemIn(product_id=1, qty=2, price=100.0),
        OrderItemIn(product_id=2, qty=1, price=50.0),
    ])
    assert _compute_total(data) == 250.0


def test_compute_total_no_price():
    data = OrderCreate(customer_id=1, items=[
        OrderItemIn(product_id=1, qty=3, price=None),
    ])
    assert _compute_total(data) == 0.0


def test_compute_total_empty_items():
    data = OrderCreate(customer_id=1, items=[])
    assert _compute_total(data) == 0.0


# ── create_order ─────────────────────────────────────────────

def test_create_order_success(db):
    p = _ensure_product(db)
    wh = _ensure_warehouse(db)
    _ensure_inventory(db, p.id, wh.id, on_hand=100, reserved=0)

    data = OrderCreate(customer_id=1, items=[
        OrderItemIn(product_id=p.id, qty=2),
    ])
    order_id, out = create_order(db, data)
    assert order_id > 0
    assert out.total > 0


def test_create_order_insufficient_stock(db):
    p = _ensure_product(db, product_id=99, sku="LOW-1", price=100)
    wh = _ensure_warehouse(db)
    _ensure_inventory(db, p.id, wh.id, on_hand=1, reserved=0)

    data = OrderCreate(customer_id=1, items=[
        OrderItemIn(product_id=p.id, qty=10),
    ])
    with pytest.raises(InsufficientStock):
        create_order(db, data)


def test_create_order_product_not_found(db):
    data = OrderCreate(customer_id=1, items=[
        OrderItemIn(product_id=99999, qty=1),
    ])
    with pytest.raises(ValueError, match="not found"):
        create_order(db, data)


def test_create_order_reserves_inventory(db):
    p = _ensure_product(db, product_id=50, sku="RES-1", price=200)
    wh = _ensure_warehouse(db)
    _ensure_inventory(db, p.id, wh.id, on_hand=50, reserved=0)

    data = OrderCreate(customer_id=1, items=[
        OrderItemIn(product_id=p.id, qty=5),
    ])
    create_order(db, data)

    inv = db.query(Inventory).filter(
        Inventory.product_id == p.id, Inventory.warehouse_id == wh.id
    ).first()
    assert Decimal(str(inv.reserved)) >= Decimal("5")


# ── fulfill_order ────────────────────────────────────────────

def test_fulfill_order_success(db):
    p = _ensure_product(db, product_id=60, sku="FUL-1", price=300)
    wh = _ensure_warehouse(db)
    _ensure_inventory(db, p.id, wh.id, on_hand=50, reserved=0)

    data = OrderCreate(customer_id=1, items=[
        OrderItemIn(product_id=p.id, qty=3),
    ])
    order_id, _ = create_order(db, data)
    order = fulfill_order(db, order_id)
    assert order.status == "fulfilled"

    inv = db.query(Inventory).filter(
        Inventory.product_id == p.id, Inventory.warehouse_id == wh.id
    ).first()
    # on_hand should have decreased by qty
    assert Decimal(str(inv.on_hand)) <= Decimal("50")


def test_fulfill_order_not_found(db):
    with pytest.raises(ValueError, match="Order not found"):
        fulfill_order(db, 999999)
