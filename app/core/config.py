from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    APP_NAME: str = "WakaAgent AI Backend"
    APP_ENV: str = "dev"
    API_V1_PREFIX: str = "/api/v1"

    # Security
    JWT_SECRET: str = "change-me"
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # CORS
    CORS_ORIGINS: str = "*"

    # DB & Infra
    DATABASE_URL: str = "postgresql+psycopg://user:pass@localhost:5432/waka"
    REDIS_URL: str = "redis://localhost:6379/0"
    S3_ENDPOINT: Optional[str] = None
    S3_BUCKET: Optional[str] = None

    # AI services
    OLLAMA_HOST: Optional[str] = None
    WHISPER_HOST: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama3-8b-8192"

    # Feature flags
    AI_REPORTS_ENABLED: bool = True

    # Reports export
    REPORTS_EXPORT_DIR: str = "exports"

    # Render (MCP) integration
    RENDER_API_KEY: Optional[str] = None

    # Embeddings/KB
    CHROMA_PERSIST_DIR: str = ".chromadb"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
