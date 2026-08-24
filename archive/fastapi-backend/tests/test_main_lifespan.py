"""Tests for app/main.py — lifespan startup, create_app, and run()."""
from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from contextlib import asynccontextmanager

from app.main import create_app, lifespan, app


# ── create_app ───────────────────────────────────────────────

def test_create_app_type():
    from fastapi import FastAPI
    assert isinstance(app, FastAPI)


def test_create_app_title():
    assert app.title is not None


def test_create_app_has_routes():
    paths = [r.path for r in app.routes]
    assert len(paths) > 0


def test_create_app_middleware_count():
    assert len(app.user_middleware) >= 3


def test_create_app_docs_in_dev():
    from app.core.config import get_settings
    settings = get_settings()
    if settings.APP_ENV != "prod":
        assert app.openapi_url is not None


# ── lifespan ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_lifespan_runs_startup():
    """Test that lifespan sets up orchestrator, realtime, and seeds data."""
    mock_app = MagicMock()
    mock_app.state = MagicMock()
    mock_app.router = MagicMock()
    mock_app.mount = MagicMock()

    # Mock all the heavy dependencies
    with patch("app.main.setup_json_logging"), \
         patch("app.main.set_app"), \
         patch("app.main.get_orchestrator") as mock_orch, \
         patch("app.main.Realtime") as MockRT, \
         patch("app.main.SessionLocal") as MockSession, \
         patch("app.main.get_settings") as mock_settings:

        mock_settings.return_value = MagicMock(REDIS_URL="redis://localhost:6379")

        mock_orchestrator = MagicMock()
        mock_orch.return_value = mock_orchestrator

        mock_rt = MagicMock()
        MockRT.return_value = mock_rt

        # Mock DB session
        mock_db = MagicMock()
        mock_db.query.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.count.return_value = 0
        MockSession.return_value = mock_db

        async with lifespan(mock_app):
            # Verify orchestrator was set
            assert mock_app.state.orchestrator == mock_orchestrator
            # Verify agents were registered
            assert mock_orchestrator.register_agent.call_count == 7
            # Verify realtime was initialized
            MockRT.assert_called_once()
            mock_rt.attach_to.assert_called_once_with(mock_app)
            # Verify DB seeding happened
            assert mock_db.commit.called
            mock_db.close.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_seeds_roles():
    """Test that lifespan seeds default roles."""
    mock_app = MagicMock()
    mock_app.state = MagicMock()
    mock_app.router = MagicMock()
    mock_app.mount = MagicMock()

    with patch("app.main.setup_json_logging"), \
         patch("app.main.set_app"), \
         patch("app.main.get_orchestrator") as mock_orch, \
         patch("app.main.Realtime") as MockRT, \
         patch("app.main.SessionLocal") as MockSession, \
         patch("app.main.get_settings") as mock_settings:

        mock_settings.return_value = MagicMock(REDIS_URL="")
        mock_orch.return_value = MagicMock()
        MockRT.return_value = MagicMock()

        mock_db = MagicMock()
        # No existing roles
        mock_db.query.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.count.return_value = 0
        MockSession.return_value = mock_db

        async with lifespan(mock_app):
            pass

        # Should have added roles
        assert mock_db.add.called
        assert mock_db.commit.called


@pytest.mark.asyncio
async def test_lifespan_seeds_admin_user():
    """Test that lifespan seeds admin user when not present."""
    mock_app = MagicMock()
    mock_app.state = MagicMock()
    mock_app.router = MagicMock()
    mock_app.mount = MagicMock()

    with patch("app.main.setup_json_logging"), \
         patch("app.main.set_app"), \
         patch("app.main.get_orchestrator") as mock_orch, \
         patch("app.main.Realtime") as MockRT, \
         patch("app.main.SessionLocal") as MockSession, \
         patch("app.main.get_settings") as mock_settings, \
         patch("app.main.get_password_hash", return_value="hashed"):

        mock_settings.return_value = MagicMock(REDIS_URL="")
        mock_orch.return_value = MagicMock()
        MockRT.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.query.return_value.all.return_value = []
        # No existing user
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.count.return_value = 0
        MockSession.return_value = mock_db

        async with lifespan(mock_app):
            pass

        assert mock_db.add.called


@pytest.mark.asyncio
async def test_lifespan_seeds_products():
    """Test that lifespan seeds products when none exist."""
    mock_app = MagicMock()
    mock_app.state = MagicMock()
    mock_app.router = MagicMock()
    mock_app.mount = MagicMock()

    with patch("app.main.setup_json_logging"), \
         patch("app.main.set_app"), \
         patch("app.main.get_orchestrator") as mock_orch, \
         patch("app.main.Realtime") as MockRT, \
         patch("app.main.SessionLocal") as MockSession, \
         patch("app.main.get_settings") as mock_settings, \
         patch("app.main.get_password_hash", return_value="hashed"):

        mock_settings.return_value = MagicMock(REDIS_URL="")
        mock_orch.return_value = MagicMock()
        MockRT.return_value = MagicMock()

        mock_db = MagicMock()
        mock_db.query.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.count.return_value = 0
        MockSession.return_value = mock_db

        async with lifespan(mock_app):
            pass

        # Products should have been seeded (3 products + roles + user + warehouse + inventory)
        assert mock_db.add.call_count >= 3


# ── run() ────────────────────────────────────────────────────

def test_run_calls_uvicorn():
    with patch("uvicorn.run") as mock_uvicorn:
        from app.main import run
        run()
        mock_uvicorn.assert_called_once_with("app.main:app", host="0.0.0.0", port=8000, reload=True)
