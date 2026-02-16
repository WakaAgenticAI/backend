from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, ForeignKey, Numeric

from app.models.base import Base


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)


class Inventory(Base):
    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id", ondelete="CASCADE"), index=True)
    warehouse_id: Mapped[int] = mapped_column(Integer, ForeignKey("warehouses.id", ondelete="CASCADE"), index=True)
    on_hand: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    reserved: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    reorder_point: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
