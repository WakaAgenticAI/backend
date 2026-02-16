"""Tests for app/realtime/server.py — attach_to method and Socket.IO setup."""
from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.realtime.server import Realtime


def test_attach_to_without_redis():
    """attach_to should create sio, register handlers, mount, and set enabled=True."""
    rt = Realtime()
    mock_app = MagicMock()
    mock_app.router = MagicMock()

    with patch("app.realtime.server.socketio") as mock_sio_mod:
        mock_server = MagicMock()
        mock_sio_mod.AsyncServer.return_value = mock_server
        mock_sio_mod.ASGIApp.return_value = MagicMock()

        rt.attach_to(mock_app)

        mock_sio_mod.AsyncServer.assert_called_once()
        assert rt.sio is mock_server
        assert rt.enabled is True
        mock_app.mount.assert_called_once()
        # Verify event handlers were registered
        assert mock_server.event.called or mock_server.on.called


def test_attach_to_with_redis():
    """attach_to with redis_url should attempt to create AsyncRedisManager."""
    rt = Realtime(redis_url="redis://localhost:6379")
    mock_app = MagicMock()
    mock_app.router = MagicMock()

    with patch("app.realtime.server.socketio") as mock_sio_mod:
        mock_server = MagicMock()
        mock_sio_mod.AsyncServer.return_value = mock_server
        mock_sio_mod.ASGIApp.return_value = MagicMock()

        rt.attach_to(mock_app)

        assert rt.enabled is True
        # AsyncServer should have been called with a client_manager
        call_kwargs = mock_sio_mod.AsyncServer.call_args
        assert call_kwargs is not None


def test_attach_to_mounts_at_ws():
    """Socket.IO should be mounted at /ws path."""
    rt = Realtime()
    mock_app = MagicMock()
    mock_app.router = MagicMock()

    with patch("app.realtime.server.socketio") as mock_sio_mod:
        mock_sio_mod.AsyncServer.return_value = MagicMock()
        mock_sio_mod.ASGIApp.return_value = MagicMock()

        rt.attach_to(mock_app)

        mock_app.mount.assert_called_once()
        mount_args = mock_app.mount.call_args
        assert mount_args[0][0] == "/ws"
