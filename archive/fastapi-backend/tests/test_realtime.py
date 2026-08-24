"""Tests for app/realtime/server.py and app/realtime/emitter.py."""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.realtime.server import Realtime
from app.realtime import emitter


# ── Realtime server ──────────────────────────────────────────

def test_realtime_init_defaults():
    rt = Realtime()
    assert rt.enabled is False
    assert rt.sio is None
    assert rt.redis_url is None


def test_realtime_init_with_redis_url():
    rt = Realtime(redis_url="redis://localhost:6379")
    assert rt.redis_url == "redis://localhost:6379"
    assert rt.enabled is False  # not attached yet


@pytest.mark.asyncio
async def test_realtime_emit_when_disabled():
    """Emit should log fallback when not enabled."""
    rt = Realtime()
    # Should not raise
    await rt.emit("test.event", room="room:1", data={"key": "val"})


@pytest.mark.asyncio
async def test_realtime_emit_when_enabled():
    """Emit should call sio.emit when enabled."""
    rt = Realtime()
    rt.enabled = True
    rt.sio = MagicMock()
    rt.sio.emit = AsyncMock()

    await rt.emit("test.event", room="room:1", data={"key": "val"}, namespace="/orders")
    rt.sio.emit.assert_called_once_with("test.event", {"key": "val"}, to="room:1", namespace="/orders")


@pytest.mark.asyncio
async def test_realtime_emit_with_none_data():
    rt = Realtime()
    rt.enabled = True
    rt.sio = MagicMock()
    rt.sio.emit = AsyncMock()

    await rt.emit("test.event", room="room:1", data=None)
    rt.sio.emit.assert_called_once_with("test.event", {}, to="room:1", namespace="/orders")


@pytest.mark.asyncio
async def test_realtime_emit_exception_handled():
    """Emit should catch and log exceptions."""
    rt = Realtime()
    rt.enabled = True
    rt.sio = MagicMock()
    rt.sio.emit = AsyncMock(side_effect=Exception("emit failed"))

    # Should not raise
    await rt.emit("test.event", room="room:1")


# ── Emitter functions ────────────────────────────────────────

@pytest.mark.asyncio
async def test_order_created_no_app():
    """Should return silently when no app is set."""
    with patch.object(emitter, "get_app", return_value=None):
        await emitter.order_created(1, {"status": "created"})


@pytest.mark.asyncio
async def test_order_created_no_realtime():
    """Should return silently when app has no realtime."""
    mock_app = MagicMock()
    mock_app.state = MagicMock(spec=[])  # no 'realtime' attribute
    with patch.object(emitter, "get_app", return_value=mock_app):
        await emitter.order_created(1)


@pytest.mark.asyncio
async def test_order_created_realtime_disabled():
    mock_app = MagicMock()
    mock_rt = MagicMock()
    mock_rt.enabled = False
    mock_app.state.realtime = mock_rt
    with patch.object(emitter, "get_app", return_value=mock_app):
        await emitter.order_created(1)


@pytest.mark.asyncio
async def test_order_created_emits():
    mock_app = MagicMock()
    mock_rt = MagicMock()
    mock_rt.enabled = True
    mock_rt.emit = AsyncMock()
    mock_app.state.realtime = mock_rt
    with patch.object(emitter, "get_app", return_value=mock_app):
        await emitter.order_created(42, {"total": 1000})
    mock_rt.emit.assert_called_once_with(
        "order.created", room="orders:42", data={"total": 1000}, namespace="/orders"
    )


@pytest.mark.asyncio
async def test_order_fulfilled_emits():
    mock_app = MagicMock()
    mock_rt = MagicMock()
    mock_rt.enabled = True
    mock_rt.emit = AsyncMock()
    mock_app.state.realtime = mock_rt
    with patch.object(emitter, "get_app", return_value=mock_app):
        await emitter.order_fulfilled(7)
    mock_rt.emit.assert_called_once()
    call_args = mock_rt.emit.call_args
    assert call_args[0][0] == "order.fulfilled"
    assert "orders:7" in call_args[1]["room"]


@pytest.mark.asyncio
async def test_order_updated_emits():
    mock_app = MagicMock()
    mock_rt = MagicMock()
    mock_rt.enabled = True
    mock_rt.emit = AsyncMock()
    mock_app.state.realtime = mock_rt
    with patch.object(emitter, "get_app", return_value=mock_app):
        await emitter.order_updated(5, {"status": "shipped"})
    mock_rt.emit.assert_called_once()


@pytest.mark.asyncio
async def test_chat_session_event_emits():
    mock_app = MagicMock()
    mock_rt = MagicMock()
    mock_rt.enabled = True
    mock_rt.emit = AsyncMock()
    mock_app.state.realtime = mock_rt
    with patch.object(emitter, "get_app", return_value=mock_app):
        await emitter.chat_session_event(10, "chat.message", {"content": "hi"})
    mock_rt.emit.assert_called_once_with(
        "chat.message", room="chat_session:10", data={"content": "hi"}, namespace="/chat"
    )


@pytest.mark.asyncio
async def test_chat_session_event_no_payload():
    mock_app = MagicMock()
    mock_rt = MagicMock()
    mock_rt.enabled = True
    mock_rt.emit = AsyncMock()
    mock_app.state.realtime = mock_rt
    with patch.object(emitter, "get_app", return_value=mock_app):
        await emitter.chat_session_event(10, "chat.typing")
    mock_rt.emit.assert_called_once_with(
        "chat.typing", room="chat_session:10", data={}, namespace="/chat"
    )
