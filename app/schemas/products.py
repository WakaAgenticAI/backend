from __future__ import annotations
from pydantic import BaseModel, Field


class ProductIn(BaseModel):
    sku: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    unit: str = Field(default="unit", max_length=32)
    price_ngn: float = Field(default=0, ge=0)
    tax_rate: float = Field(default=0, ge=0)


class ProductOut(BaseModel):
    id: int
    sku: str
    name: str
    unit: str
    price_ngn: float
    tax_rate: float


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    unit: str | None = Field(default=None, max_length=32)
    price_ngn: float | None = Field(default=None, ge=0)
    tax_rate: float | None = Field(default=None, ge=0)
