from __future__ import annotations
from typing import Optional, Iterable, List, Dict

import chromadb
from chromadb.utils import embedding_functions

from app.core.config import get_settings


def get_client():
    settings = get_settings()
    client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
    return client


def get_collection(name: str):
    client = get_client()
    settings = get_settings()
    # Use a lightweight embedder by default; can be swapped to OpenAI etc.
    embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    coll = client.get_or_create_collection(name=name, embedding_function=embedder)
    return coll
