from __future__ import annotations
from typing import Tuple
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.schemas.orders import OrderCreate, OrderOut
from app.models.orders import Order, OrderItem
from app.models.products import Product
from app.models.inventory import Inventory, Warehouse


class InsufficientStock(Exception):
    pass


def _compute_total(data: OrderCreate) -> float:
    total = 0.0
    for it in data.items:
        line_price = (it.price or 0.0) * it.qty
        total += line_price
    return round(total, 2)

def create_order(db: Session, data: OrderCreate) -> Tuple[int, OrderOut]:
    """Create an order and order_items in the database.
    Validates stock and reserves inventory per item.
    """
    total = Decimal("0.00")
    order = Order(customer_id=data.customer_id, channel=data.channel)
    db.add(order)
    db.flush()  # assign order.id

    # Build a map of product_id -> price from DB
    product_ids = {it.product_id for it in data.items}
    products = db.execute(select(Product).where(Product.id.in_(product_ids))).scalars().all()
    price_map: dict[int, Decimal] = {p.id: Decimal(str(p.price_ngn)) for p in products}

    # Default warehouse (first one); in startup we seed one
    wh = db.execute(select(Warehouse).order_by(Warehouse.id.asc())).scalars().first()
    if not wh:
        wh = Warehouse(name="Main")
        db.add(wh)
        db.flush()

    for it in data.items:
        if it.product_id not in price_map:
            raise ValueError(f"Product {it.product_id} not found")
        price = price_map[it.product_id]
        line_total = price * it.qty
        total += line_total

        # Reserve inventory
        inv = (
            db.execute(
                select(Inventory).where(
                    Inventory.product_id == it.product_id,
                    Inventory.warehouse_id == wh.id,
                )
            )
            .scalars()
            .first()
        )
        if not inv:
            inv = Inventory(product_id=it.product_id, warehouse_id=wh.id, on_hand=Decimal("0"), reserved=Decimal("0"))
            db.add(inv)
            db.flush()
        available = Decimal(str(inv.on_hand or 0)) - Decimal(str(inv.reserved or 0))
        if Decimal(str(it.qty)) > available:
            raise InsufficientStock(f"Insufficient stock for product {it.product_id}")
        inv.reserved = Decimal(str(inv.reserved or 0)) + Decimal(str(it.qty))

        db.add(
            OrderItem(
                order_id=order.id,
                product_id=it.product_id,
                qty=it.qty,
                price=price,
                line_total=line_total,
            )
        )

    order.total = total
    db.commit()
    db.refresh(order)

    out = OrderOut(id=order.id, total=float(order.total))
    return order.id, out


def fulfill_order(db: Session, order_id: int) -> Order:
    """Decrement on_hand and reserved per order items and mark order fulfilled."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise ValueError("Order not found")
    wh = db.execute(select(Warehouse).order_by(Warehouse.id.asc())).scalars().first()
    if not wh:
        raise ValueError("No warehouse configured")
    items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
    for it in items:
        inv = (
            db.execute(
                select(Inventory).where(
                    Inventory.product_id == it.product_id,
                    Inventory.warehouse_id == wh.id,
                )
            )
            .scalars()
            .first()
        )
        if not inv:
            raise ValueError(f"Inventory row missing for product {it.product_id}")
        # Ensure reserved has at least qty
        if Decimal(str(inv.reserved or 0)) < Decimal(str(it.qty)):
            raise ValueError(f"Reserved less than fulfill qty for product {it.product_id}")
        # Ensure on_hand has at least qty
        if Decimal(str(inv.on_hand or 0)) < Decimal(str(it.qty)):
            raise ValueError(f"On hand less than fulfill qty for product {it.product_id}")
        inv.reserved = Decimal(str(inv.reserved or 0)) - Decimal(str(it.qty))
        inv.on_hand = Decimal(str(inv.on_hand or 0)) - Decimal(str(it.qty))
    order.status = "fulfilled"
    db.commit()
    db.refresh(order)
    return order
