from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any, Dict, List
from datetime import datetime


class ChatRouteIn(BaseModel):
    intent: str = Field(..., examples=["orders.create"])
    payload: Dict[str, Any] = Field(default_factory=dict)


class ChatRouteOut(BaseModel):
    handled: bool
    result: Dict[str, Any] | None = None
    reason: str | None = None


class ChatSessionOut(BaseModel):
    id: int
    status: str
    last_activity_at: datetime


class ChatSessionCreate(BaseModel):
    reuse_recent: bool = True


class ChatMessageCreate(BaseModel):
    content: str | None = None
    audio_url: str | None = None


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    audio_url: str | None = None
    created_at: datetime


class ChatMessagesPage(BaseModel):
    items: List[ChatMessageOut]
