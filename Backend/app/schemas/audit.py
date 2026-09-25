"""Schémas du journal d'audit."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class AuditEventResponse(BaseModel):
    id: str
    occurred_at: datetime
    actor_id: Optional[int] = None
    actor_email: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    outcome: str
    reason: Optional[str] = None
    details: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)
