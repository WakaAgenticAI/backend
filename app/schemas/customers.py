from __future__ import annotations
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class CustomerIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    phone: str | None = None
    segment: str = "regular"
    status: str = "active"
    location: str | None = None


class CustomerOut(BaseModel):
    id: int
    email: EmailStr
    name: str
    phone: str | None
    segment: str
    status: str
    location: str | None
    created_at: datetime

    class Config:
        from_attributes = True
