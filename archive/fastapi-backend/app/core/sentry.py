"""Sentry integration for error tracking and monitoring."""

import logging
from typing import Optional

from app.core.config import get_settings

settings = get_settings()

def init_sentry() -> None:
    """Initialize Sentry SDK if DSN is provided."""
    if not settings.SENTRY_DSN:
        return
    
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        
        # Configure Sentry integrations
        integrations = [
            FastApiIntegration(auto_enabling_integrations=False),
            StarletteIntegration(auto_enabling_integrations=False),
            SqlalchemyIntegration(),
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
            ),
        ]
        
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=integrations,
            traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
            environment=settings.APP_ENV,
            release="wakaagent-backend@0.1.0",
        )
        
        logging.getLogger(__name__).info("Sentry initialized successfully")
        
    except ImportError:
        logging.getLogger(__name__).warning(
            "Sentry SDK not installed. Install with: pip install sentry-sdk[fastapi]"
        )
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to initialize Sentry: {e}")


def capture_exception(error: Exception, extra_data: Optional[dict] = None) -> None:
    """Capture an exception in Sentry."""
    if not settings.SENTRY_DSN:
        return
    
    try:
        import sentry_sdk
        
        if extra_data:
            sentry_sdk.set_context("additional_data", extra_data)
        
        sentry_sdk.capture_exception(error)
        
    except ImportError:
        # Sentry not available
        pass
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to capture exception in Sentry: {e}")


def capture_message(message: str, level: str = "info") -> None:
    """Capture a message in Sentry."""
    if not settings.SENTRY_DSN:
        return
    
    try:
        import sentry_sdk
        
        sentry_sdk.capture_message(message, level=level)
        
    except ImportError:
        # Sentry not available
        pass
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to capture message in Sentry: {e}")
