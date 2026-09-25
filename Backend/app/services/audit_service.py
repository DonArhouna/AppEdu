"""Service d'écriture des événements de sécurité."""

import uuid
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent


async def record_audit_event(
    db: AsyncSession,
    *,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    actor_id: Optional[int] = None,
    actor_email: Optional[str] = None,
    outcome: str = "success",
    reason: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> AuditEvent:
    """Ajoute un événement à la transaction courante sans l'écraser.

    L'appelant est responsable du commit. Aucun secret, mot de passe ou JWT ne
    doit être placé dans ``details``.
    """

    event = AuditEvent(
        id=str(uuid.uuid4()),
        actor_id=actor_id,
        actor_email=actor_email,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        outcome=outcome,
        reason=reason,
        details=details or {},
    )
    db.add(event)
    return event
