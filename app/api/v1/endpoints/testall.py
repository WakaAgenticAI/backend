import os
from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()


@router.get("/testall")
async def testall() -> dict:
    """
    Simple diagnostics endpoint to verify API, config, and environment are wired.
    Does not touch external services aggressively.
    """
    settings = get_settings()

    # Redact secrets
    def redact(v: str | None) -> str | None:
        if not v:
            return v
        if len(v) <= 8:
            return "***"
        return v[:4] + "***" + v[-4:]

    info = {
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "api_prefix": settings.API_V1_PREFIX,
        "cors": settings.CORS_ORIGINS,
        "database_url": "postgresql+psycopg://***@***:***/***" if settings.DATABASE_URL else None,
        "redis_url": settings.REDIS_URL,
        "ollama_host": settings.OLLAMA_HOST,
        "whisper_host": settings.WHISPER_HOST,
        "python_version": os.sys.version.split(" ")[0],
    }
    return {"status": "ok", "info": info}
