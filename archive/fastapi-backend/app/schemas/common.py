"""Common Pydantic schemas shared across endpoints/services."""
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel


class StatusResponse(BaseModel):
    status: str = "ok"
    timestamp: datetime = datetime.utcnow()


class PageMeta(BaseModel):
    page: int = 1
    size: int = 20
    total: int = 0
