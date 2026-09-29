"""
DTO partagé du registre multi-tenant (lot 6).

Le détail d'une école tel que l'exploitation le lit — CLI ou futur écran
d'administration SaaS. Aucun secret ici : la base de contrôle ne conserve
ni mot de passe ni jeton d'école, chaque base garde ses propres comptes.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class TenantDetail(BaseModel):
    id: str
    slug: str
    nom: str
    statut: str
    plan: str
    abonnement_jusquau: Optional[date] = None
    contact_email: Optional[str] = None
    created_at: Optional[datetime] = None
