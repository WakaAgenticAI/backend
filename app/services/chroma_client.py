from __future__ import annotations
from typing import List, Dict, Any

# Minimal in-memory stub for last-5 message memory per session.
# Replace with real ChromaDB client later.
_memory: dict[int, List[Dict[str, Any]]] = {}


def add_message(session_id: int, role: str, content: str) -> None:
    buf = _memory.setdefault(session_id, [])
    buf.append({"role": role, "content": content})
    # keep last 5
    if len(buf) > 5:
        del buf[0 : len(buf) - 5]


def get_context(session_id: int) -> List[Dict[str, Any]]:
    return list(_memory.get(session_id, []))
