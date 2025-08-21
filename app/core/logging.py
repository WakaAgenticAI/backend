from __future__ import annotations
import json
import logging
import sys
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "time": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),
        }
        # Include extra if present
        for key in ("request_id", "path", "method", "actor_id", "action", "entity", "entity_id", "data"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, ensure_ascii=False)


def setup_json_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        # Avoid double init in reload
        for h in list(root.handlers):
            root.removeHandler(h)
    root.setLevel(logging.INFO)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)

    # Dedicated audit logger inherits handlers
    audit_logger = logging.getLogger("audit")
    audit_logger.setLevel(logging.INFO)
