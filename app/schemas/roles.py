from __future__ import annotations
from pydantic import BaseModel, Field


class RoleIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=64)


class RoleOut(BaseModel):
    id: int
    name: str


class AssignRoleIn(BaseModel):
    role_name: str = Field(..., min_length=2, max_length=64)
