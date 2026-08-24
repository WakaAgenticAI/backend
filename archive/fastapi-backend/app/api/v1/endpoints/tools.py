from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.deps import require_roles
from app.core.app_state import get_app

router = APIRouter()
REQUIRE_ROLES = require_roles("Admin", "Ops", "Sales")


class ToolExecuteIn(BaseModel):
    intent: str
    payload: dict


@router.post("/tools/execute", dependencies=[Depends(REQUIRE_ROLES)])
async def execute_tool(body: ToolExecuteIn):
    app = get_app()
    if not app or not hasattr(app.state, "orchestrator"):
        raise HTTPException(status_code=503, detail="orchestrator not ready")
    result = await app.state.orchestrator.route(body.intent, body.payload)
    return result
