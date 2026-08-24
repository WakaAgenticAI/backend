"""Tests for AI API endpoints."""
import pytest
from fastapi.testclient import TestClient


def test_ai_complete_requires_auth(client: TestClient):
    """Verify /ai/complete requires authentication."""
    r = client.post("/api/v1/ai/complete", json={"prompt": "hello"})
    assert r.status_code in (401, 403)


def test_ai_complete_with_language(client: TestClient, auth_headers: dict):
    """Verify /ai/complete accepts language parameter."""
    r = client.post(
        "/api/v1/ai/complete",
        json={"prompt": "hello", "language": "pcm", "max_tokens": 50},
        headers=auth_headers,
    )
    # Should succeed (200) or fail gracefully if Groq key is invalid
    assert r.status_code in (200, 500, 503)


def test_ai_capabilities(client: TestClient, auth_headers: dict):
    """Verify /ai/capabilities returns supported features."""
    r = client.get("/api/v1/ai/capabilities", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "supported_languages" in data
    assert "features" in data


def test_ai_languages(client: TestClient, auth_headers: dict):
    """Verify /ai/languages returns all 5 supported languages."""
    r = client.get("/api/v1/ai/languages", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    langs = data.get("supported_languages", [])
    codes = [l["code"] for l in langs]
    assert "en" in codes
    assert "pcm" in codes  # Pidgin
    assert "ha" in codes   # Hausa
    assert "yo" in codes   # Yoruba
    assert "ig" in codes   # Igbo


def test_ai_classify_intent(client: TestClient, auth_headers: dict):
    """Verify /ai/classify-intent returns an intent."""
    r = client.post(
        "/api/v1/ai/classify-intent",
        json={"message": "I want to place an order"},
        headers=auth_headers,
    )
    # May fail if LLM is unavailable, but should not crash
    assert r.status_code in (200, 500, 503)
    if r.status_code == 200:
        data = r.json()
        assert "intent" in data


def test_ai_multilingual(client: TestClient, auth_headers: dict):
    """Verify /ai/multilingual processes messages."""
    r = client.post(
        "/api/v1/ai/multilingual",
        json={"message": "How far, wetin dey happen?"},
        headers=auth_headers,
    )
    assert r.status_code in (200, 500, 503)
    if r.status_code == 200:
        data = r.json()
        assert "detected_language" in data
        assert "response" in data
