from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import datetime, date
from decimal import Decimal
from typing import Optional


class DebtIn(BaseModel):
    type: str = Field(..., description="Type of debt: 'receivable' or 'payable'")
    entity_type: str = Field(..., description="Entity type: 'customer', 'supplier', or 'other'")
    entity_id: Optional[int] = Field(None, description="ID of the related entity (customer/supplier)")
    amount_ngn: Decimal = Field(..., gt=0, description="Amount in NGN")
    currency: str = Field("NGN", min_length=3, max_length=3)
    description: Optional[str] = Field(None, max_length=1000)
    due_date: Optional[date] = None
    priority: str = Field("medium", description="Priority: 'low', 'medium', 'high'")


class DebtUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Status: 'pending', 'partial', 'paid', 'overdue', 'cancelled'")
    priority: Optional[str] = Field(None, description="Priority: 'low', 'medium', 'high'")
    description: Optional[str] = Field(None, max_length=1000)
    due_date: Optional[date] = None


class DebtOut(BaseModel):
    id: int
    type: str
    entity_type: str
    entity_id: Optional[int]
    amount_ngn: Decimal
    currency: str
    description: Optional[str]
    due_date: Optional[date]
    status: str
    priority: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DebtPaymentIn(BaseModel):
    amount_ngn: Decimal = Field(..., gt=0)
    payment_date: date
    payment_method: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = Field(None, max_length=500)


class DebtPaymentOut(BaseModel):
    id: int
    debt_id: int
    amount_ngn: Decimal
    payment_date: date
    payment_method: Optional[str]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class DebtAgingReport(BaseModel):
    range_0_30: int = Field(..., description="Number of debts 0-30 days overdue")
    range_31_60: int = Field(..., description="Number of debts 31-60 days overdue")
    range_61_90: int = Field(..., description="Number of debts 61-90 days overdue")
    range_90_plus: int = Field(..., description="Number of debts 90+ days overdue")
    total_overdue_amount: Decimal
    total_debts: int
    total_amount: Decimal


class DebtSummary(BaseModel):
    receivables_total: Decimal
    payables_total: Decimal
    receivables_count: int
    payables_count: int
    overdue_receivables: int
    overdue_payables: int
