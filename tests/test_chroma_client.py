"""Comprehensive tests for app/services/chroma_client.py — ConversationMemory."""
from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock

from app.services.chroma_client import (
    ConversationMemory, get_memory_client,
    add_message, get_context,
)


def _make_memory():
    """Create a ConversationMemory with a mocked ChromaDB collection."""
    mock_collection = MagicMock()
    with patch("app.services.chroma_client.get_collection", return_value=mock_collection), \
         patch("app.services.chroma_client.get_settings"):
        mem = ConversationMemory()
    return mem, mock_collection


# ── ConversationMemory init ──────────────────────────────────

def test_init():
    mem, coll = _make_memory()
    assert mem.max_context_messages == 10
    assert mem.max_memory_age_days == 30
    assert mem.collection is coll


# ── add_message ──────────────────────────────────────────────

def test_add_message_basic():
    mem, coll = _make_memory()
    msg_id = mem.add_message(1, "user", "Hello")
    assert isinstance(msg_id, str)
    coll.add.assert_called_once()
    call_kwargs = coll.add.call_args
    assert call_kwargs[1]["documents"] == ["user: Hello"]


def test_add_message_with_metadata():
    mem, coll = _make_memory()
    msg_id = mem.add_message(1, "assistant", "Hi", metadata={"intent": "greeting"})
    assert isinstance(msg_id, str)
    meta = coll.add.call_args[1]["metadatas"][0]
    assert meta["intent"] == "greeting"
    assert meta["role"] == "assistant"
    assert meta["session_id"] == "1"


# ── get_context ──────────────────────────────────────────────

def test_get_context_with_recent():
    mem, coll = _make_memory()
    coll.get.return_value = {
        "ids": ["m1", "m2"],
        "documents": ["user: Hello", "assistant: Hi there"],
        "metadatas": [
            {"session_id": "1", "role": "user", "timestamp": "2025-01-01T00:00:00"},
            {"session_id": "1", "role": "assistant", "timestamp": "2025-01-01T00:01:00"},
        ],
    }
    ctx = mem.get_context(1, limit=5)
    assert len(ctx) == 2
    assert ctx[0]["role"] in ("user", "assistant")


def test_get_context_empty():
    mem, coll = _make_memory()
    coll.get.return_value = {"ids": [], "documents": [], "metadatas": []}
    ctx = mem.get_context(1)
    assert ctx == []


def test_get_context_no_recent():
    mem, coll = _make_memory()
    ctx = mem.get_context(1, include_recent=False)
    assert ctx == []


def test_get_context_exception():
    mem, coll = _make_memory()
    coll.get.side_effect = Exception("ChromaDB error")
    ctx = mem.get_context(1)
    assert ctx == []


# ── search_similar_messages ──────────────────────────────────

def test_search_similar_success():
    mem, coll = _make_memory()
    coll.query.return_value = {
        "ids": [["m1", "m2"]],
        "documents": [["user: order status", "assistant: Your order is shipped"]],
        "metadatas": [[
            {"session_id": "1", "role": "user", "timestamp": "2025-01-01T00:00:00"},
            {"session_id": "1", "role": "assistant", "timestamp": "2025-01-01T00:01:00"},
        ]],
        "distances": [[0.1, 0.3]],
    }
    results = mem.search_similar_messages(1, "order", limit=5)
    assert len(results) == 2
    assert results[0]["role"] == "user"
    assert results[0]["similarity"] == 0.1


def test_search_similar_no_colon():
    mem, coll = _make_memory()
    coll.query.return_value = {
        "ids": [["m1"]],
        "documents": [["plain text without colon"]],
        "metadatas": [[{"session_id": "1"}]],
        "distances": [[0.5]],
    }
    results = mem.search_similar_messages(1, "query")
    assert results[0]["role"] == "unknown"


def test_search_similar_empty():
    mem, coll = _make_memory()
    coll.query.return_value = {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
    results = mem.search_similar_messages(1, "query")
    assert results == []


def test_search_similar_no_distances():
    mem, coll = _make_memory()
    coll.query.return_value = {
        "ids": [["m1"]],
        "documents": [["user: hello"]],
        "metadatas": [[{"session_id": "1"}]],
    }
    results = mem.search_similar_messages(1, "hello")
    assert results[0]["similarity"] == 0


def test_search_similar_exception():
    mem, coll = _make_memory()
    coll.query.side_effect = Exception("search error")
    results = mem.search_similar_messages(1, "query")
    assert results == []


# ── get_session_summary ──────────────────────────────────────

def test_session_summary_short():
    mem, coll = _make_memory()
    coll.get.return_value = {
        "ids": ["m1", "m2"],
        "documents": ["user: Hello", "assistant: Hi"],
        "metadatas": [
            {"timestamp": "2025-01-01T00:00:00"},
            {"timestamp": "2025-01-01T00:01:00"},
        ],
    }
    summary = mem.get_session_summary(1)
    assert "2 messages" in summary


def test_session_summary_long():
    mem, coll = _make_memory()
    ids = [f"m{i}" for i in range(8)]
    docs = [f"user: message {i}" for i in range(8)]
    metas = [{"timestamp": f"2025-01-01T00:0{i}:00"} for i in range(8)]
    coll.get.return_value = {"ids": ids, "documents": docs, "metadatas": metas}
    summary = mem.get_session_summary(1)
    assert "8 messages" in summary
    assert "Recent topics" in summary


def test_session_summary_empty():
    mem, coll = _make_memory()
    coll.get.return_value = {"ids": [], "documents": [], "metadatas": []}
    summary = mem.get_session_summary(1)
    assert summary is None


def test_session_summary_no_colon():
    mem, coll = _make_memory()
    coll.get.return_value = {
        "ids": ["m1"],
        "documents": ["plain text"],
        "metadatas": [{"timestamp": "2025-01-01T00:00:00"}],
    }
    summary = mem.get_session_summary(1)
    assert "1 messages" in summary


def test_session_summary_exception():
    mem, coll = _make_memory()
    coll.get.side_effect = Exception("error")
    summary = mem.get_session_summary(1)
    assert summary is None


# ── cleanup_old_messages ─────────────────────────────────────

def test_cleanup_deletes_old():
    mem, coll = _make_memory()
    coll.get.return_value = {"ids": ["old1", "old2"]}
    count = mem.cleanup_old_messages(days=30)
    assert count == 2
    coll.delete.assert_called_once_with(ids=["old1", "old2"])


def test_cleanup_nothing_to_delete():
    mem, coll = _make_memory()
    coll.get.return_value = {"ids": []}
    count = mem.cleanup_old_messages()
    assert count == 0


def test_cleanup_exception():
    mem, coll = _make_memory()
    coll.get.side_effect = Exception("error")
    count = mem.cleanup_old_messages()
    assert count == 0


# ── _get_recent_messages ─────────────────────────────────────

def test_get_recent_messages_sorted():
    mem, coll = _make_memory()
    coll.get.return_value = {
        "ids": ["m1", "m2", "m3"],
        "documents": ["user: first", "assistant: second", "user: third"],
        "metadatas": [
            {"timestamp": "2025-01-01T00:00:00"},
            {"timestamp": "2025-01-01T00:02:00"},
            {"timestamp": "2025-01-01T00:01:00"},
        ],
    }
    msgs = mem._get_recent_messages(1, limit=2)
    assert len(msgs) == 2
    # Most recent first
    assert msgs[0]["timestamp"] >= msgs[1]["timestamp"]


def test_get_recent_messages_exception():
    mem, coll = _make_memory()
    coll.get.side_effect = Exception("error")
    msgs = mem._get_recent_messages(1, limit=5)
    assert msgs == []


# ── Backward compat functions ────────────────────────────────

def test_backward_add_message():
    with patch("app.services.chroma_client.get_memory_client") as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client
        add_message(1, "user", "hello")
        mock_client.add_message.assert_called_once_with(1, "user", "hello")


def test_backward_get_context():
    with patch("app.services.chroma_client.get_memory_client") as mock_get:
        mock_client = MagicMock()
        mock_client.get_context.return_value = [{"role": "user", "content": "hi"}]
        mock_get.return_value = mock_client
        ctx = get_context(1)
        assert len(ctx) == 1
