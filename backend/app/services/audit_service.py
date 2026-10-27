import uuid
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import pino_logger, scrub_sensitive_data
from app.models.audit_log import AuditLog


async def record_audit_log(
    db: AsyncSession,
    *,
    actor_id: Optional[uuid.UUID],
    action: str,
    target_entity: str,
    ip_address: str,
    details: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """
    Appends an immutable state change record to audit_logs (Section 4.5 & 5.3)
    after scrubbing any sensitive fields (Section 5.1).
    """
    clean_details = scrub_sensitive_data(details or {})
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        target_entity=target_entity,
        ip_address=ip_address,
        details=clean_details,
    )
    db.add(entry)
    await db.flush()

    pino_logger.info(
        "Immutable audit log recorded",
        audit_log_id=str(entry.log_id),
        actor_id=str(actor_id) if actor_id else None,
        action=action,
        target_entity=target_entity,
        ip_address=ip_address,
    )
    return entry