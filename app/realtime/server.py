from __future__ import annotations
import logging
from typing import Any, Optional

import socketio

logger = logging.getLogger(__name__)


class Realtime:
    """Socket.IO wrapper with optional Redis manager.

    - Namespaces: /orders, /chat
    - Rooms: arbitrary strings (e.g., order:<id>, chat_session:<id>)
    - If Redis manager cannot be initialized, falls back to in-process manager.
    """

    def __init__(self, redis_url: Optional[str] = None) -> None:
        self.enabled = False
        self.redis_url = redis_url
        self.sio: Optional[socketio.AsyncServer] = None

    def attach_to(self, app) -> None:
        try:
            mgr = None
            if self.redis_url:
                try:
                    # Try Redis-based manager; fallback if unavailable
                    from socketio.asyncio_redis_manager import AsyncRedisManager  # type: ignore

                    mgr = AsyncRedisManager(self.redis_url)
                except Exception as e:  # pragma: no cover
                    logger.warning("realtime_redis_manager_init_failed", extra={"error": str(e)})

            self.sio = socketio.AsyncServer(async_mode="asgi", client_manager=mgr, cors_allowed_origins="*")

            # Basic connection logs
            @self.sio.event(namespace="/orders")
            async def connect(sid, environ):  # type: ignore
                logger.info("socket_connect_orders", extra={"sid": sid})

            @self.sio.event(namespace="/chat")
            async def connect(sid, environ):  # type: ignore
                logger.info("socket_connect_chat", extra={"sid": sid})

            # Mount Socket.IO on the FastAPI app at /ws (keeps existing routes intact)
            sio_app = socketio.ASGIApp(self.sio, other_asgi_app=app, socketio_path="ws")
            app.router.lifespan_context  # keep reference to ensure FastAPI lifespan runs
            app.mount("/ws", sio_app)
            self.enabled = True
            logger.info("realtime_initialized", extra={"redis": bool(mgr)})
        except Exception as e:  # pragma: no cover
            logger.warning("realtime_init_failed", extra={"error": str(e)})
            self.enabled = False

    async def emit(self, event: str, room: str, data: dict[str, Any] | None = None, namespace: str = "/orders") -> None:
        try:
            payload = data or {}
            if self.sio and self.enabled:
                await self.sio.emit(event, payload, to=room, namespace=namespace)
            else:
                logger.info("realtime_emit_fallback", extra={"event": event, "room": room, "ns": namespace, "data": payload})
        except Exception as e:
            logger.warning("realtime_emit_failed", extra={"error": str(e)})
