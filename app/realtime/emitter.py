from __future__ import annotations
from typing import Any

async def order_updated(app, order_id: int, payload: dict[str, Any] | None = None) -> None:
    rt = getattr(app.state, "realtime", None)
    if not rt or not getattr(rt, "enabled", False):
        return
    await rt.emit("ORDER_UPDATED", room=f"orders:{order_id}", data=payload or {})
