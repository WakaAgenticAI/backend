"""Comprehensive tests for app/services/multilingual_client.py."""
from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.multilingual_client import (
    MultilingualClient, NigerianLanguage, get_multilingual_client,
)


# ── NigerianLanguage enum ────────────────────────────────────

def test_language_enum_values():
    assert NigerianLanguage.ENGLISH.value == "en"
    assert NigerianLanguage.PIDGIN.value == "pcm"
    assert NigerianLanguage.HAUSA.value == "ha"
    assert NigerianLanguage.YORUBA.value == "yo"
    assert NigerianLanguage.IGBO.value == "ig"


# ── detect_language ──────────────────────────────────────────

def test_detect_english():
    client = MultilingualClient()
    lang, conf = client.detect_language("The quarterly financial report looks great.")
    assert lang == NigerianLanguage.ENGLISH


def test_detect_pidgin():
    client = MultilingualClient()
    lang, conf = client.detect_language("How far, wetin dey happen? Na wahala o")
    assert lang == NigerianLanguage.PIDGIN
    assert conf > 0


def test_detect_hausa():
    client = MultilingualClient()
    lang, conf = client.detect_language("Sannu, ina kwana? Yaya aiki?")
    assert lang == NigerianLanguage.HAUSA


def test_detect_yoruba():
    client = MultilingualClient()
    lang, conf = client.detect_language("Bawo ni, e kaaro, se daadaa")
    assert lang == NigerianLanguage.YORUBA


def test_detect_igbo():
    client = MultilingualClient()
    lang, conf = client.detect_language("Kedu ka i mere? Gini ka i na eme?")
    assert lang == NigerianLanguage.IGBO


def test_detect_empty_text():
    client = MultilingualClient()
    lang, conf = client.detect_language("")
    assert lang == NigerianLanguage.ENGLISH
    assert conf == 0.5


def test_detect_no_match():
    client = MultilingualClient()
    lang, conf = client.detect_language("xyz 123 abc")
    assert lang == NigerianLanguage.ENGLISH


# ── translate_to_english ─────────────────────────────────────

@pytest.mark.asyncio
async def test_translate_english_passthrough():
    client = MultilingualClient()
    result = await client.translate_to_english("Hello", NigerianLanguage.ENGLISH)
    assert result == "Hello"


@pytest.mark.asyncio
async def test_translate_pidgin_to_english():
    client = MultilingualClient()
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value="How are you?")
    client.llm_client = mock_llm

    result = await client.translate_to_english("How far?", NigerianLanguage.PIDGIN)
    assert result == "How are you?"


@pytest.mark.asyncio
async def test_translate_to_english_error():
    client = MultilingualClient()
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(side_effect=Exception("LLM down"))
    client.llm_client = mock_llm

    result = await client.translate_to_english("How far?", NigerianLanguage.PIDGIN)
    assert result == "How far?"  # returns original on error


# ── translate_to_language ────────────────────────────────────

@pytest.mark.asyncio
async def test_translate_to_english_target():
    client = MultilingualClient()
    result = await client.translate_to_language("Hello", NigerianLanguage.ENGLISH)
    assert result == "Hello"


@pytest.mark.asyncio
async def test_translate_to_pidgin():
    client = MultilingualClient()
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value="How far?")
    client.llm_client = mock_llm

    result = await client.translate_to_language("How are you?", NigerianLanguage.PIDGIN)
    assert result == "How far?"


@pytest.mark.asyncio
async def test_translate_to_language_error():
    client = MultilingualClient()
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(side_effect=Exception("fail"))
    client.llm_client = mock_llm

    result = await client.translate_to_language("Hello", NigerianLanguage.HAUSA)
    assert result == "Hello"


# ── generate_culturally_appropriate_response ─────────────────

@pytest.mark.asyncio
async def test_cultural_response_english():
    client = MultilingualClient()
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value="I can help with that order.")
    client.llm_client = mock_llm

    result = await client.generate_culturally_appropriate_response(
        "I need help with my order", "order management", NigerianLanguage.ENGLISH
    )
    assert result == "I can help with that order."


@pytest.mark.asyncio
async def test_cultural_response_pidgin():
    client = MultilingualClient()
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value="No wahala, I go help you.")
    client.llm_client = mock_llm

    result = await client.generate_culturally_appropriate_response(
        "Help me", "support", NigerianLanguage.PIDGIN
    )
    assert result == "No wahala, I go help you."


@pytest.mark.asyncio
async def test_cultural_response_hausa():
    client = MultilingualClient()
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value="Lafiya, zan taimake ka.")
    client.llm_client = mock_llm

    result = await client.generate_culturally_appropriate_response(
        "Help me", "support", NigerianLanguage.HAUSA
    )
    assert "taimake" in result


@pytest.mark.asyncio
async def test_cultural_response_error():
    client = MultilingualClient()
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(side_effect=Exception("fail"))
    client.llm_client = mock_llm

    result = await client.generate_culturally_appropriate_response(
        "Help me", "support", NigerianLanguage.PIDGIN
    )
    assert "help" in result.lower()


# ── get_language_support_info ────────────────────────────────

def test_language_support_info():
    client = MultilingualClient()
    info = client.get_language_support_info()
    assert len(info["supported_languages"]) == 5
    codes = [l["code"] for l in info["supported_languages"]]
    assert "en" in codes
    assert "pcm" in codes
    assert info["translation_supported"] is True


# ── _get_display_name ────────────────────────────────────────

def test_display_names():
    client = MultilingualClient()
    assert client._get_display_name(NigerianLanguage.ENGLISH) == "English"
    assert client._get_display_name(NigerianLanguage.PIDGIN) == "Nigerian Pidgin"
    assert client._get_display_name(NigerianLanguage.HAUSA) == "Hausa"
    assert client._get_display_name(NigerianLanguage.YORUBA) == "Yoruba"
    assert client._get_display_name(NigerianLanguage.IGBO) == "Igbo"


# ── _get_llm_client ─────────────────────────────────────────

def test_get_llm_client_lazy():
    client = MultilingualClient()
    assert client.llm_client is None
    with patch("app.services.llm_client.get_llm_client") as mock:
        mock.return_value = MagicMock()
        result = client._get_llm_client()
        assert result is not None
        mock.assert_called_once()


# ── process_multilingual_message ─────────────────────────────

@pytest.mark.asyncio
async def test_process_multilingual_english():
    client = MultilingualClient()
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value="Here is your order status.")
    client.llm_client = mock_llm

    result = await client.process_multilingual_message("What is my order status?")
    assert result["detected_language"] == "en"
    assert result["original_message"] == "What is my order status?"
    assert "response" in result


@pytest.mark.asyncio
async def test_process_multilingual_pidgin():
    client = MultilingualClient()
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value="No wahala, your order dey come.")
    client.llm_client = mock_llm

    result = await client.process_multilingual_message(
        "How far, wetin happen to my order? Na wahala o", context="order tracking"
    )
    assert result["detected_language"] == "pcm"
    assert result["confidence"] > 0


# ── singleton ────────────────────────────────────────────────

def test_get_multilingual_client_singleton():
    c1 = get_multilingual_client()
    c2 = get_multilingual_client()
    assert c1 is c2
