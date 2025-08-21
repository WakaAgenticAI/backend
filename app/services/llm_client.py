from __future__ import annotations
from typing import Optional
import os

# Stub LLM client. In production, call Groq/OpenAI/Ollama depending on env.
OLLAMA_HOST = os.getenv("OLLAMA_HOST")


async def complete(prompt: str, session_id: int | None = None) -> str:
    # Minimal deterministic stub: echo prompt or a canned response
    if not prompt:
        return ""
    # Extend later to call external LLM
    return f"You said: {prompt}"
