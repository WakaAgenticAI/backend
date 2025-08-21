from __future__ import annotations
import logging
from typing import Any

logger = logging.getLogger(__name__)


class Realtime:
    """Minimal realtime stub. Later: integrate python-socketio with Redis adapter.
    Methods are no-ops other than logging so the app runs without extra deps.
    """

    def __init__(self) -> None:
        self.enabled = True  # flip to False if initialization fails later

    async def emit(self, event: str, room: str, data: dict[str, Any] | None = None) -> None:
        try:
            logger.info("realtime_emit", extra={"event": event, "room": room, "data": data or {}})
        except Exception:
            # Never fail request due to realtime
            pass
