from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    # Environment
    ENVIRONMENT: str = "development"  # or "production"

    APP_NAME: str = "WakaAgent AI Backend"
    APP_ENV: str = "dev"
    API_V1_PREFIX: str = "/api/v1"

    # Security
    JWT_SECRET: str = "change-me"
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour (was 15 min)
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Security headers
    TRUSTED_HOSTS: str = "localhost,127.0.0.1"
    MAX_REQUEST_SIZE_MB: int = 10

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

    # External tools directory (kept at repo root by default)
    # If unset, backend will attempt to resolve '../../tools' relative to this file.
    TOOLS_DIR: Optional[str] = None

    # Email notifications (Resend — free tier: 100 emails/day)
    RESEND_API_KEY: Optional[str] = None
    ALERT_EMAIL_FROM: str = "WakaAgent AI <alerts@resend.dev>"
    ALERT_EMAIL_TO: str = ""  # comma-separated list of admin emails
    EMAIL_NOTIFICATIONS_ENABLED: bool = True

    # Render (MCP) integration
    RENDER_API_KEY: Optional[str] = None

    # Embeddings/KB
    CHROMA_PERSIST_DIR: str = ".chromadb"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
