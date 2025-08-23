from __future__ import annotations
import os
from celery import Celery

from app.core.config import get_settings

_settings = get_settings()

# Use Redis as broker and result backend by default
broker_url = os.getenv("CELERY_BROKER_URL", _settings.REDIS_URL)
result_backend = os.getenv("CELERY_RESULT_BACKEND", _settings.REDIS_URL)

celery_app = Celery(
    "waka_backend",
    broker=broker_url,
    backend=result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Autodiscover tasks within app.services and app.jobs packages if present
celery_app.autodiscover_tasks(["app.services", "app.jobs"], force=True)
