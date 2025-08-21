from __future__ import annotations
from typing import List
from pydantic import BaseModel, Field


class OrderItemIn(BaseModel):
    product_id: int = Field(..., ge=1)
    qty: int = Field(..., ge=1)
    price: float | None = None


class OrderCreate(BaseModel):
    customer_id: int = Field(..., ge=1)
    items: List[OrderItemIn]
    channel: str = "chatbot"


class OrderOut(BaseModel):
    id: int
    status: str = "created"
    total: float
    currency: str = "NGN"


class OrderUpdate(BaseModel):
    status: str = Field(..., pattern="^(created|paid|fulfilled|cancelled)$")
