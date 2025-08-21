from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.ai.groq_client import GroqClient, GroqCompletionRequest

router = APIRouter()


class AICompleteIn(BaseModel):
    prompt: str
    system: str | None = None
    temperature: float = 0.3
    max_tokens: int = 256


class AICompleteOut(BaseModel):
    content: str


@router.post("/complete", response_model=AICompleteOut)
async def ai_complete(payload: AICompleteIn) -> AICompleteOut:
    try:
        client = GroqClient()
        text = client.complete(
            GroqCompletionRequest(
                prompt=payload.prompt,
                system=payload.system,
                temperature=payload.temperature,
                max_tokens=payload.max_tokens,
            )
        )
        return AICompleteOut(content=text)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # fallback
        raise HTTPException(status_code=500, detail="AI service error") from e
