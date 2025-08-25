from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from app.core.config import get_settings


def get_tools_dir(explicit: Optional[str] = None) -> Path:
    """
    Resolve the absolute path to the repo-level `tools/` directory without moving it into backend.

    Resolution order:
    1) Function argument `explicit` if provided.
    2) Settings.TOOLS_DIR env value (can be absolute or relative to backend/).
    3) Fallback: compute repo root from this file and join 'tools'.

    Returns a Path that may or may not exist; callers can check `.exists()`.
    """
    if explicit:
        p = Path(explicit).expanduser()
        return p if p.is_absolute() else (Path.cwd() / p).resolve()

    settings = get_settings()
    if settings.TOOLS_DIR:
        p = Path(settings.TOOLS_DIR).expanduser()
        return p if p.is_absolute() else (Path(__file__).resolve().parents[3] / p).resolve()

    # Prefer colocated backend/tools first
    # utils -> app -> backend
    backend_dir = Path(__file__).resolve().parents[2]
    backend_tools = (backend_dir / "tools").resolve()
    if backend_tools.exists():
        return backend_tools

    # Fallback: repo root tools
    # utils -> app -> backend -> repo_root
    repo_root = Path(__file__).resolve().parents[3]
    return (repo_root / "tools").resolve()


def require_tools_dir() -> Path:
    """Like get_tools_dir but raises if it does not exist."""
    p = get_tools_dir()
    if not p.exists():
        raise FileNotFoundError(f"tools directory not found at: {p}")
    return p
