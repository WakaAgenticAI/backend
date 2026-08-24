from __future__ import annotations
from types import SimpleNamespace
from unittest.mock import AsyncMock
import asyncio

from app.realtime import emitter
from app.core.app_state import set_app


class DummyRealtime:
    enabled = True

    def __init__(self):
        self.emit = AsyncMock()


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def test_order_emitters():
    rt = DummyRealtime()
    app = SimpleNamespace(state=SimpleNamespace(realtime=rt))
    set_app(app)

    _run(emitter.order_created(10, {"k": 1}))
    _run(emitter.order_updated(10, {"k": 2}))
    _run(emitter.order_fulfilled(10, {"k": 3}))

    rt.emit.assert_any_await("order.created", room="orders:10", data={"k": 1}, namespace="/orders")
    rt.emit.assert_any_await("order.updated", room="orders:10", data={"k": 2}, namespace="/orders")
    rt.emit.assert_any_await("order.fulfilled", room="orders:10", data={"k": 3}, namespace="/orders")


def test_chat_session_emitter():
    rt = DummyRealtime()
    app = SimpleNamespace(state=SimpleNamespace(realtime=rt))
    set_app(app)

    _run(emitter.chat_session_event(5, "chat.message", {"text": "hi"}))
    rt.emit.assert_any_await("chat.message", room="chat_session:5", data={"text": "hi"}, namespace="/chat")
