"""Comprehensive tests for app/services/llm_client.py."""
from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.llm_client import LLMClient, get_llm_client, complete


# ── LLMClient init ───────────────────────────────────────────

def test_llm_client_init_no_groq():
    mock_settings = MagicMock()
    mock_settings.GROQ_API_KEY = ""
    with patch("app.services.llm_client.get_settings", return_value=mock_settings):
        client = LLMClient()
        assert client.groq_client is None


def test_llm_client_init_groq_error():
    mock_settings = MagicMock()
    mock_settings.GROQ_API_KEY = "test-key"
    with patch("app.services.llm_client.get_settings", return_value=mock_settings), \
         patch("app.services.llm_client.GroqClient", side_effect=Exception("init fail")):
        client = LLMClient()
        assert client.groq_client is None


# ── _build_system_prompt ─────────────────────────────────────

def test_build_system_prompt_default():
    mock_settings = MagicMock()
    mock_settings.GROQ_API_KEY = ""
    with patch("app.services.llm_client.get_settings", return_value=mock_settings):
        client = LLMClient()
    prompt = client._build_system_prompt(None, [], None)
    assert "WakaAgent AI" in prompt
    assert "English" in prompt


def test_build_system_prompt_custom_system():
    mock_settings = MagicMock()
    mock_settings.GROQ_API_KEY = ""
    with patch("app.services.llm_client.get_settings", return_value=mock_settings):
        client = LLMClient()
    prompt = client._build_system_prompt("Custom system", [], None)
    assert prompt == "Custom system"


def test_build_system_prompt_with_context():
    mock_settings = MagicMock()
    mock_settings.GROQ_API_KEY = ""
    with patch("app.services.llm_client.get_settings", return_value=mock_settings):
        client = LLMClient()
    context = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ]
    prompt = client._build_system_prompt(None, context, None)
    assert "user: Hello" in prompt
    assert "assistant: Hi there" in prompt


def test_build_system_prompt_pidgin():
    mock_settings = MagicMock()
    mock_settings.GROQ_API_KEY = ""
    with patch("app.services.llm_client.get_settings", return_value=mock_settings):
        client = LLMClient()
    prompt = client._build_system_prompt(None, [], "pcm")
    assert "Pidgin" in prompt


def test_build_system_prompt_hausa():
    mock_settings = MagicMock()
    mock_settings.GROQ_API_KEY = ""
    with patch("app.services.llm_client.get_settings", return_value=mock_settings):
        client = LLMClient()
    prompt = client._build_system_prompt(None, [], "ha")
    assert "Hausa" in prompt


def test_build_system_prompt_yoruba():
    mock_settings = MagicMock()
    mock_settings.GROQ_API_KEY = ""
    with patch("app.services.llm_client.get_settings", return_value=mock_settings):
        client = LLMClient()
    prompt = client._build_system_prompt(None, [], "yo")
    assert "Yoruba" in prompt


def test_build_system_prompt_igbo():
    mock_settings = MagicMock()
    mock_settings.GROQ_API_KEY = ""
    with patch("app.services.llm_client.get_settings", return_value=mock_settings):
        client = LLMClient()
    prompt = client._build_system_prompt(None, [], "ig")
    assert "Igbo" in prompt


# ── _simple_fallback_response ────────────────────────────────

def test_fallback_greeting():
    mock_settings = MagicMock()
    mock_settings.GROQ_API_KEY = ""
    with patch("app.services.llm_client.get_settings", return_value=mock_settings):
        client = LLMClient()
    resp = client._simple_fallback_response("hello there")
    assert "WakaAgent AI" in resp


def test_fallback_order():
    mock_settings = MagicMock()
    mock_settings.GROQ_API_KEY = ""
    with patch("app.services.llm_client.get_settings", return_value=mock_settings):
        client = LLMClient()
    resp = client._simple_fallback_response("I want to place an order")
    assert "order" in resp.lower()


def test_fallback_inventory():
    mock_settings = MagicMock()
    mock_settings.GROQ_API_KEY = ""
    with patch("app.services.llm_client.get_settings", return_value=mock_settings):
        client = LLMClient()
    resp = client._simple_fallback_response("check my inventory levels")
    assert "inventory" in resp.lower()


def test_fallback_help():
    mock_settings = MagicMock()
    mock_settings.GROQ_API_KEY = ""
    with patch("app.services.llm_client.get_settings", return_value=mock_settings):
        client = LLMClient()
    resp = client._simple_fallback_response("I need help")
    assert "help" in resp.lower() or "assist" in resp.lower()


def test_fallback_default():
    mock_settings = MagicMock()
    mock_settings.GROQ_API_KEY = ""
    with patch("app.services.llm_client.get_settings", return_value=mock_settings):
        client = LLMClient()
    resp = client._simple_fallback_response("xyzzy random gibberish")
    assert "xyzzy random gibberish" in resp


# ── complete (integration with fallback) ─────────────────────

@pytest.mark.asyncio
async def test_complete_uses_groq_first():
    mock_settings = MagicMock()
    mock_settings.GROQ_API_KEY = "key"
    mock_groq = MagicMock()
    mock_groq.complete.return_value = "Groq response"

    with patch("app.services.llm_client.get_settings", return_value=mock_settings), \
         patch("app.services.llm_client.GroqClient", return_value=mock_groq), \
         patch("app.services.llm_client.get_context", return_value=[]):
        client = LLMClient()
        result = await client.complete("Hello")
        assert result == "Groq response"


@pytest.mark.asyncio
async def test_complete_falls_back_to_ollama():
    mock_settings = MagicMock()
    mock_settings.GROQ_API_KEY = "key"
    mock_groq = MagicMock()
    mock_groq.complete.side_effect = Exception("Groq down")

    mock_response = MagicMock()
    mock_response.json.return_value = {"response": "Ollama response"}
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.llm_client.get_settings", return_value=mock_settings), \
         patch("app.services.llm_client.GroqClient", return_value=mock_groq), \
         patch("app.services.llm_client.get_context", return_value=[]), \
         patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=mock_response)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        client = LLMClient()
        result = await client.complete("Hello")
        assert result == "Ollama response"


@pytest.mark.asyncio
async def test_complete_falls_back_to_simple():
    mock_settings = MagicMock()
    mock_settings.GROQ_API_KEY = ""

    with patch("app.services.llm_client.get_settings", return_value=mock_settings), \
         patch("app.services.llm_client.get_context", return_value=[]), \
         patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(side_effect=Exception("Ollama down"))
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        client = LLMClient()
        result = await client.complete("hello")
        assert "WakaAgent AI" in result


@pytest.mark.asyncio
async def test_complete_with_session_id():
    mock_settings = MagicMock()
    mock_settings.GROQ_API_KEY = "key"
    mock_groq = MagicMock()
    mock_groq.complete.return_value = "response"

    with patch("app.services.llm_client.get_settings", return_value=mock_settings), \
         patch("app.services.llm_client.GroqClient", return_value=mock_groq), \
         patch("app.services.llm_client.get_context", return_value=[{"role": "user", "content": "prev"}]):
        client = LLMClient()
        result = await client.complete("Hello", session_id=42)
        assert result == "response"


# ── get_llm_client singleton ─────────────────────────────────

def test_get_llm_client_returns_instance():
    client = get_llm_client()
    assert isinstance(client, LLMClient)


# ── backward compat complete() ───────────────────────────────

@pytest.mark.asyncio
async def test_backward_compat_complete():
    with patch("app.services.llm_client.get_llm_client") as mock_get:
        mock_client = MagicMock()
        mock_client.complete = AsyncMock(return_value="compat response")
        mock_get.return_value = mock_client

        result = await complete("Hello")
        assert result == "compat response"
