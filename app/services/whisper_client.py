from __future__ import annotations
from typing import Optional
import httpx
import os

WHISPER_HOST = os.getenv("WHISPER_HOST", "http://whisper:8000")


async def transcribe(audio_url: str) -> Optional[str]:
    # Stub: call a hypothetical transcription endpoint
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(f"{WHISPER_HOST}/transcribe", json={"audio_url": audio_url})
            r.raise_for_status()
            data = r.json()
            return data.get("text")
    except Exception:
        return None
