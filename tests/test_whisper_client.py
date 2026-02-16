"""Comprehensive tests for app/services/whisper_client.py."""
from __future__ import annotations
import asyncio
import base64
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.whisper_client import WhisperClient, get_whisper_client, transcribe


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ── WhisperClient init ───────────────────────────────────────

def test_whisper_client_defaults():
    client = WhisperClient()
    assert client.whisper_host is not None
    assert ".mp3" in client.supported_formats
    assert client.max_file_size == 25 * 1024 * 1024


# ── is_supported_format ──────────────────────────────────────

def test_supported_format_mp3():
    client = WhisperClient()
    assert client.is_supported_format("audio.mp3") is True


def test_supported_format_wav():
    client = WhisperClient()
    assert client.is_supported_format("recording.wav") is True


def test_supported_format_webm():
    client = WhisperClient()
    assert client.is_supported_format("voice.webm") is True


def test_unsupported_format_txt():
    client = WhisperClient()
    assert client.is_supported_format("notes.txt") is False


def test_unsupported_format_exe():
    client = WhisperClient()
    assert client.is_supported_format("malware.exe") is False


# ── get_supported_formats ────────────────────────────────────

def test_get_supported_formats():
    client = WhisperClient()
    formats = client.get_supported_formats()
    assert isinstance(formats, list)
    assert len(formats) >= 5
    assert ".mp3" in formats
    assert ".flac" in formats


# ── get_whisper_client singleton ─────────────────────────────

def test_get_whisper_client_singleton():
    c1 = get_whisper_client()
    c2 = get_whisper_client()
    assert c1 is c2


# ── transcribe_from_url ─────────────────────────────────────

def test_transcribe_from_url_success():
    client = WhisperClient()
    mock_response = MagicMock()
    mock_response.json.return_value = {"text": "Hello world"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=mock_response)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = _run(client.transcribe_from_url("http://example.com/audio.mp3"))
        assert result == "Hello world"


def test_transcribe_from_url_timeout():
    import httpx
    client = WhisperClient()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = _run(client.transcribe_from_url("http://example.com/audio.mp3"))
        assert result is None


def test_transcribe_from_url_413():
    import httpx
    client = WhisperClient()

    mock_response = MagicMock()
    mock_response.status_code = 413
    error = httpx.HTTPStatusError("too large", request=MagicMock(), response=mock_response)

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(side_effect=error)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = _run(client.transcribe_from_url("http://example.com/big.mp3"))
        assert result is not None
        assert "too large" in result.lower()


def test_transcribe_from_url_generic_error():
    client = WhisperClient()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(side_effect=Exception("connection refused"))
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = _run(client.transcribe_from_url("http://example.com/audio.mp3"))
        assert result is None


def test_transcribe_from_url_with_language():
    client = WhisperClient()
    mock_response = MagicMock()
    mock_response.json.return_value = {"text": "Bonjour"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=mock_response)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = _run(client.transcribe_from_url("http://example.com/audio.mp3", language="fr"))
        assert result == "Bonjour"


# ── transcribe_from_file ────────────────────────────────────

def test_transcribe_from_file_not_exists():
    client = WhisperClient()
    result = _run(client.transcribe_from_file("/nonexistent/audio.mp3"))
    assert result is None


def test_transcribe_from_file_unsupported_format(tmp_path):
    f = tmp_path / "audio.xyz"
    f.write_text("fake")
    client = WhisperClient()
    result = _run(client.transcribe_from_file(str(f)))
    assert "Unsupported" in result


def test_transcribe_from_file_too_large(tmp_path):
    f = tmp_path / "big.mp3"
    # Create a file that exceeds max size check (we fake the size)
    f.write_bytes(b"x" * 100)
    client = WhisperClient()
    client.max_file_size = 50  # artificially low
    result = _run(client.transcribe_from_file(str(f)))
    assert "too large" in result.lower()


def test_transcribe_from_file_success(tmp_path):
    f = tmp_path / "audio.mp3"
    f.write_bytes(b"fake audio data")
    client = WhisperClient()

    mock_response = MagicMock()
    mock_response.json.return_value = {"text": "transcribed text"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=mock_response)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = _run(client.transcribe_from_file(str(f)))
        assert result == "transcribed text"


# ── transcribe_from_base64 ──────────────────────────────────

def test_transcribe_from_base64_success():
    client = WhisperClient()
    audio_b64 = base64.b64encode(b"fake audio").decode()

    mock_response = MagicMock()
    mock_response.json.return_value = {"text": "base64 result"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=mock_response)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = _run(client.transcribe_from_base64(audio_b64, "test.mp3"))
        assert result == "base64 result"


def test_transcribe_from_base64_too_large():
    client = WhisperClient()
    client.max_file_size = 5
    audio_b64 = base64.b64encode(b"x" * 100).decode()
    result = _run(client.transcribe_from_base64(audio_b64, "test.mp3"))
    assert "too large" in result.lower()


def test_transcribe_from_base64_unsupported_format():
    client = WhisperClient()
    audio_b64 = base64.b64encode(b"data").decode()
    result = _run(client.transcribe_from_base64(audio_b64, "test.xyz"))
    assert "Unsupported" in result


def test_transcribe_from_base64_error():
    client = WhisperClient()
    # Invalid base64
    result = _run(client.transcribe_from_base64("not-valid-base64!!!", "test.mp3"))
    assert result is None


# ── detect_language ──────────────────────────────────────────

def test_detect_language_success():
    client = WhisperClient()
    mock_response = MagicMock()
    mock_response.json.return_value = {"language": "en"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=mock_response)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = _run(client.detect_language("http://example.com/audio.mp3"))
        assert result == "en"


def test_detect_language_error():
    client = WhisperClient()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(side_effect=Exception("fail"))
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = _run(client.detect_language("http://example.com/audio.mp3"))
        assert result is None


# ── backward compat transcribe() ─────────────────────────────

def test_transcribe_backward_compat():
    mock_response = MagicMock()
    mock_response.json.return_value = {"text": "compat result"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=mock_response)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = _run(transcribe("http://example.com/audio.mp3"))
        assert result == "compat result"
