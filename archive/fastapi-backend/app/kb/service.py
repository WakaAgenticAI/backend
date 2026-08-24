from __future__ import annotations
from typing import Iterable, List, Dict, Optional


def get_collection(name: str):  # pragma: no cover - thin wrapper, patched in tests
    from app.kb.chroma import get_collection as _gc

    return _gc(name)


def kb_upsert(collection: str, items: Iterable[Dict]) -> int:
    """
    Upsert items into a Chroma collection.
    Each item supports: {id: str, text: str, metadata: dict}
    Returns number of upserted items.
    """
    coll = get_collection(collection)
    ids: List[str] = []
    documents: List[str] = []
    metadatas: List[dict] = []
    for it in items:
        ids.append(str(it["id"]))
        documents.append(str(it["text"]))
        metadatas.append(dict(it.get("metadata") or {}))
    if not ids:
        return 0
    coll.upsert(ids=ids, documents=documents, metadatas=metadatas)
    return len(ids)


def kb_query(collection: str, query: str, k: int = 5) -> List[Dict]:
    coll = get_collection(collection)
    res = coll.query(query_texts=[query], n_results=k)
    # Normalize result shape
    out: List[Dict] = []
    ids = res.get("ids", [[]])[0]
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    for i in range(len(ids)):
        out.append({"id": ids[i], "text": docs[i], "metadata": metas[i]})
    return out
