"""Tests for app/kb/chroma.py — get_client, get_collection."""
from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock

from app.kb.chroma import get_client, get_collection


def test_get_client():
    mock_settings = MagicMock()
    mock_settings.CHROMA_PERSIST_DIR = "/tmp/test_chroma"
    with patch("app.kb.chroma.get_settings", return_value=mock_settings), \
         patch("app.kb.chroma.chromadb") as mock_chromadb:
        mock_chromadb.PersistentClient.return_value = MagicMock()
        client = get_client()
        mock_chromadb.PersistentClient.assert_called_once_with(path="/tmp/test_chroma")
        assert client is not None


def test_get_collection_existing():
    """get_collection should return existing collection if found."""
    mock_settings = MagicMock()
    mock_settings.CHROMA_PERSIST_DIR = "/tmp/test_chroma"
    mock_settings.ENVIRONMENT = "development"

    mock_coll = MagicMock()
    mock_client = MagicMock()
    mock_client.get_collection.return_value = mock_coll

    with patch("app.kb.chroma.get_settings", return_value=mock_settings), \
         patch("app.kb.chroma.chromadb") as mock_chromadb:
        mock_chromadb.PersistentClient.return_value = mock_client
        result = get_collection("test_collection")
        mock_client.get_collection.assert_called_once_with(name="test_collection")
        assert result is mock_coll


def test_get_collection_not_found_creates():
    """get_collection should create collection if not found."""
    import chromadb
    mock_settings = MagicMock()
    mock_settings.CHROMA_PERSIST_DIR = "/tmp/test_chroma"
    mock_settings.ENVIRONMENT = "development"

    mock_coll = MagicMock()
    mock_client = MagicMock()
    mock_client.get_collection.side_effect = ValueError("not found")
    mock_client.get_or_create_collection.return_value = mock_coll

    with patch("app.kb.chroma.get_settings", return_value=mock_settings), \
         patch("app.kb.chroma.chromadb") as mock_chromadb:
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_chromadb.errors.NotFoundError = chromadb.errors.NotFoundError if hasattr(chromadb, 'errors') else ValueError
        result = get_collection("new_collection")
        mock_client.get_or_create_collection.assert_called_once()
        assert result is mock_coll
