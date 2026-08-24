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
    
    # Use a mock embedder in development to save memory
    if getattr(settings, 'ENVIRONMENT', 'development') == 'development':
        from chromadb.utils.embedding_functions import EmbeddingFunction
        class MockEmbedder(EmbeddingFunction):
            def __call__(self, input: list[str]) -> list[list[float]]:
                # Return random embeddings of dimension 384 (same as all-MiniLM-L6-v2)
                import random
                return [[random.random() for _ in range(384)] for _ in input]
                
        embedder = MockEmbedder()
    else:
        # Use the real embedder in production
        embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
    
    try:
        # Try to get the existing collection first
        coll = client.get_collection(name=name)
        # If we get here, the collection exists
        print(f"Using existing collection: {name}")
        return coll
    except (ValueError, chromadb.errors.NotFoundError):
        # Collection doesn't exist, create it with our embedder
        print(f"Creating new collection: {name}")
        coll = client.get_or_create_collection(
            name=name, 
            embedding_function=embedder
        )
        return coll