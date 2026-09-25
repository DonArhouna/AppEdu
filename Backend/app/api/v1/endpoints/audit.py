"""Consultation du journal d'audit de sécurité.

Le guard historique ``require_admin`` est remplacé par ``require_audit_read``
(permission dynamique ``audit.read``).  Le comportement observable ne change
pas : ADMIN legacy passe toujours, tout autre rôle non porteur était et reste
refusé.  Un compte non administrateur peut désormais consulter l'audit si un
rôle dynamique lui accorde explicitement ``audit.read``.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_audit_read
from app.models.audit import AuditEvent
from app.models.utilisateur import Utilisateur
from app.schemas.audit import AuditEventResponse

router = APIRouter()


@router.get(
    "/events",
    response_model=List[AuditEventResponse],
    summary="Consulter les événements d'audit",
)
async def list_audit_events(
    action: Optional[str] = Query(None, max_length=100),
    resource_type: Optional[str] = Query(None, max_length=100),
    resource_id: Optional[str] = Query(None, max_length=100),
    actor_id: Optional[int] = None,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _actor: Utilisateur = Depends(require_audit_read),
):
    stmt = select(AuditEvent)
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    if resource_type:
        stmt = stmt.where(AuditEvent.resource_type == resource_type)
    if resource_id:
        stmt = stmt.where(AuditEvent.resource_id == resource_id)
    if actor_id is not None:
        stmt = stmt.where(AuditEvent.actor_id == actor_id)

    stmt = (
        stmt.order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()
