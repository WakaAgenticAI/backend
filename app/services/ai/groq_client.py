from __future__ import annotations
from typing import Optional

from groq import Groq
from pydantic import BaseModel

from app.core.config import get_settings


class GroqCompletionRequest(BaseModel):
    prompt: str
    system: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 256


class GroqClient:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        settings = get_settings()
        self._api_key = api_key or settings.GROQ_API_KEY
        if not self._api_key:
            raise RuntimeError("GROQ_API_KEY is not configured")
        self._model = model or settings.GROQ_MODEL
        self._client = Groq(api_key=self._api_key)

    def complete(self, req: GroqCompletionRequest) -> str:
        messages = []
        if req.system:
            messages.append({"role": "system", "content": req.system})
        messages.append({"role": "user", "content": req.prompt})

        chat = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            stream=False,
        )
        # Extract first choice text
        choice = chat.choices[0].message.content if chat.choices else ""
        return choice or ""
