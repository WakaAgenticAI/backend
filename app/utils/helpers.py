"""General utilities and helpers."""
from __future__ import annotations
from datetime import datetime


def utc_now_iso() -> str:
    """Return current UTC time in ISO8601 format."""
    return datetime.utcnow().isoformat() + "Z"
