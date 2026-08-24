from __future__ import annotations
from fastapi.testclient import TestClient
from types import SimpleNamespace
import asyncio

from app.main import app
from app.api.v1.endpoints.tools import REQUIRE_ROLES
from app.core.app_state import set_app


class DummyOrch:
    async def route(self, intent: str, payload: dict) -> dict:
        return {"handled": True, "intent": intent, "echo": payload}


def test_tools_execute_endpoint(monkeypatch):
    # Inject orchestrator into app.state
    app.state.orchestrator = DummyOrch()
    set_app(app)
    # Override auth dependency to bypass auth checks
    app.dependency_overrides[REQUIRE_ROLES] = lambda: None

    client = TestClient(app)
    # Bypass auth dependency by not setting it; or we could monkeypatch require_roles in router include
    body = {"intent": "inventory.check", "payload": {"sku": "SKU-APPLE"}}
    resp = client.post("/api/v1/tools/execute", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["handled"] is True
    assert data["intent"] == "inventory.check"
