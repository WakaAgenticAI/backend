"""Tests for app/main.py — create_app, lifespan, middleware stack."""
from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock

from app.main import create_app, app


# ── create_app ───────────────────────────────────────────────

def test_create_app_returns_fastapi():
    from fastapi import FastAPI
    assert isinstance(app, FastAPI)


def test_app_has_routes():
    routes = [r.path for r in app.routes]
    assert len(routes) > 0


def test_app_title():
    assert app.title is not None
    assert len(app.title) > 0


def test_app_has_middleware():
    # FastAPI stores middleware in app.user_middleware
    assert len(app.user_middleware) >= 3  # security, rate limit, sanitization, etc.


# ── Endpoint integration via TestClient ──────────────────────

def test_healthz_via_app(client):
    r = client.get("/api/v1/healthz")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"


def test_readyz_via_app(client):
    r = client.get("/api/v1/readyz")
    assert r.status_code == 200


def test_docs_available_in_non_prod(client):
    """In test/dev mode, docs should be available."""
    from app.core.config import get_settings
    settings = get_settings()
    if settings.APP_ENV != "prod":
        r = client.get(f"{settings.API_V1_PREFIX}/docs")
        # Should be 200 (docs page) or redirect
        assert r.status_code in (200, 307)


def test_openapi_available_in_non_prod(client):
    from app.core.config import get_settings
    settings = get_settings()
    if settings.APP_ENV != "prod":
        r = client.get(f"{settings.API_V1_PREFIX}/openapi.json")
        assert r.status_code == 200
        data = r.json()
        assert "paths" in data


# ── Auth endpoints ───────────────────────────────────────────

def test_login_success(client):
    r = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "admin123"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data


def test_login_wrong_password(client):
    r = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "wrong"})
    assert r.status_code in (401, 429)


# ── Protected endpoints require auth ─────────────────────────

def test_orders_requires_auth(client):
    r = client.get("/api/v1/orders")
    assert r.status_code == 401


def test_products_requires_auth(client):
    r = client.get("/api/v1/products")
    assert r.status_code == 401


def test_customers_requires_auth(client):
    r = client.get("/api/v1/customers")
    assert r.status_code == 401


def test_inventory_requires_auth(client):
    r = client.get("/api/v1/inventory")
    assert r.status_code == 401


# ── Authenticated endpoints ──────────────────────────────────

def test_orders_with_auth(client, auth_headers):
    r = client.get("/api/v1/orders", headers=auth_headers)
    assert r.status_code == 200


def test_products_with_auth(client, auth_headers):
    r = client.get("/api/v1/products", headers=auth_headers)
    assert r.status_code == 200


def test_customers_with_auth(client, auth_headers):
    r = client.get("/api/v1/customers", headers=auth_headers)
    assert r.status_code == 200


def test_inventory_with_auth(client, auth_headers):
    r = client.get("/api/v1/inventory", headers=auth_headers)
    assert r.status_code == 200


def test_debts_with_auth(client, auth_headers):
    r = client.get("/api/v1/debts", headers=auth_headers)
    assert r.status_code == 200


def test_debts_summary_with_auth(client, auth_headers):
    r = client.get("/api/v1/debts/reports/summary", headers=auth_headers)
    assert r.status_code == 200


def test_debts_aging_with_auth(client, auth_headers):
    r = client.get("/api/v1/debts/reports/aging", headers=auth_headers)
    assert r.status_code == 200
