import os
from typing import Any
from fastapi.testclient import TestClient
import pytest


@pytest.fixture(autouse=True)
def _set_api_prefix_env() -> None:
    os.environ.setdefault("API_V1_PREFIX", "/api/v1")


def test_ai_complete_success(client: TestClient, monkeypatch: Any):
    # Ensure an API key is set for initialization
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    # Stub out the GroqClient.complete to avoid external call
    from app.services.ai import groq_client as gc

    def fake_init(self, api_key=None, model=None):  # noqa: ANN001
        self._api_key = api_key or "test-key"
        self._model = model or "llama3-8b-8192"
        self._client = object()

    def fake_complete(_self, req):  # noqa: ANN001
        assert req.prompt == "Hello"
        return "Hi there!"

    monkeypatch.setattr(gc.GroqClient, "__init__", fake_init)
    monkeypatch.setattr(gc.GroqClient, "complete", fake_complete)

    r = client.post("/api/v1/ai/complete", json={"prompt": "Hello"})
    assert r.status_code == 200
    assert r.json()["content"] == "Hi there!"


def test_ai_complete_missing_key(client: TestClient, monkeypatch: Any):
    # Ensure client raises when no key — simulate by forcing init to raise
    from app.services.ai import groq_client as gc

    def raising_init(self, api_key=None, model=None):  # noqa: ANN001
        raise RuntimeError("GROQ_API_KEY is not configured")

    monkeypatch.setattr(gc.GroqClient, "__init__", raising_init)

    r = client.post("/api/v1/ai/complete", json={"prompt": "Hello"})
    assert r.status_code == 400
    assert "GROQ_API_KEY" in r.json()["detail"]
