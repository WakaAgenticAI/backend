from __future__ import annotations
import logging
from typing import Any

_audit_logger = logging.getLogger("audit")


def audit_log(action: str, entity: str, entity_id: int | str | None = None, actor_id: int | str | None = None, data: dict[str, Any] | None = None) -> None:
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
        # Never fail request due to audit logging issues
        pass
