from __future__ import annotations
import logging
from typing import Any

from app.db.session import SessionLocal
from app.models.audit import AuditLog

_audit_logger = logging.getLogger("audit")


def audit_log(
    action: str,
    entity: str,
    entity_id: int | str | None = None,
    actor_id: int | str | None = None,
    data: dict[str, Any] | None = None,
) -> None:
    # Log to structured logger first
    try:
        _audit_logger.info(
            "audit",
            extra={
                "action": action,
                "entity": entity,
                "entity_id": entity_id,
                "actor_id": actor_id,
                "data": data or {},
            },
        )
    except Exception:
        pass

    # Persist to DB, never fail caller on error
    try:
        db = SessionLocal()
        try:
            row = AuditLog(
                action=action,
                entity=entity,
                entity_id=str(entity_id) if entity_id is not None else None,
                actor_id=int(actor_id) if isinstance(actor_id, (int,)) else None,
                data_json=data or {},
            )
            db.add(row)
            db.commit()
        finally:
            db.close()
    except Exception:
        # swallow any persistence errors
        pass
