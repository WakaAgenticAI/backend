from __future__ import annotations
from pydantic import BaseModel
from typing import List, Optional


class WarehouseCreate(BaseModel):
    name: str


class WarehouseOut(BaseModel):
    id: int
    name: str


class InventoryOut(BaseModel):
    product_id: int
    warehouse_id: int
    on_hand: float
    reserved: float


class InventoryQuery(BaseModel):
    sku: Optional[str] = None
    warehouse_id: Optional[int] = None


class FulfillOut(BaseModel):
    id: int
    status: str
