from __future__ import annotations
from typing import Any

from app.core.app_state import get_app


async def order_created(order_id: int, payload: dict[str, Any] | None = None) -> None:
    app = get_app()
    if not app:
        return
    rt = getattr(app.state, "realtime", None)
    if not rt or not getattr(rt, "enabled", False):
        return
    await rt.emit("order.created", room=f"orders:{order_id}", data=payload or {}, namespace="/orders")


async def order_fulfilled(order_id: int, payload: dict[str, Any] | None = None) -> None:
    app = get_app()
    if not app:
        return
    rt = getattr(app.state, "realtime", None)
    if not rt or not getattr(rt, "enabled", False):
        return
    await rt.emit("order.fulfilled", room=f"orders:{order_id}", data=payload or {}, namespace="/orders")


async def order_updated(order_id: int, payload: dict[str, Any] | None = None) -> None:
    app = get_app()
    if not app:
        return
    rt = getattr(app.state, "realtime", None)
    if not rt or not getattr(rt, "enabled", False):
        return
    await rt.emit("order.updated", room=f"orders:{order_id}", data=payload or {}, namespace="/orders")


async def chat_session_event(session_id: int, event: str, payload: dict | None = None) -> None:
    """Emit chat events to /chat namespace, room chat_session:<id>."""
    app = get_app()
    if not app:
        return
    rt = getattr(app.state, "realtime", None)
    if not rt or not getattr(rt, "enabled", False):
        return
    await rt.emit(event, room=f"chat_session:{session_id}", data=payload or {}, namespace="/chat")
