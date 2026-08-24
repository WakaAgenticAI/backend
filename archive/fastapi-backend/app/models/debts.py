from __future__ import annotations
from sqlalchemy import String, Integer, Date, DateTime, CheckConstraint, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base


class Debt(Base):
    __tablename__ = "debts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'receivable' or 'payable'
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'customer', 'supplier', 'other'
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)  # FK to customer/supplier
    amount_ngn: Mapped[Numeric] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="NGN")
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    due_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # 'pending', 'partial', 'paid', 'overdue', 'cancelled'
    priority: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")  # 'low', 'medium', 'high'
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    payments: Mapped[list["DebtPayment"]] = relationship("DebtPayment", back_populates="debt", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("type IN ('receivable', 'payable')", name="check_debt_type"),
        CheckConstraint("entity_type IN ('customer', 'supplier', 'other')", name="check_entity_type"),
        CheckConstraint("status IN ('pending', 'partial', 'paid', 'overdue', 'cancelled')", name="check_debt_status"),
        CheckConstraint("priority IN ('low', 'medium', 'high')", name="check_priority"),
    )


class DebtPayment(Base):
    __tablename__ = "debt_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    debt_id: Mapped[int] = mapped_column(Integer, ForeignKey("debts.id"), nullable=False, index=True)
    amount_ngn: Mapped[Numeric] = mapped_column(Numeric(15, 2), nullable=False)
    payment_date: Mapped[Date] = mapped_column(Date, nullable=False)
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    debt: Mapped["Debt"] = relationship("Debt", back_populates="payments")
