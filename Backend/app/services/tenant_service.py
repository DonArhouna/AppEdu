"""
Registre multi-tenant (lot 6) : le côté service, appelable depuis l'API.

La partie qui **crée des bases et applique des migrations** vit dans
``app.provisioning`` (CLI) : elle manipule Alembic de façon synchrone et
doit tourner dans son propre processus, jamais dans la boucle
d'événements du serveur — provisionner une école pendant qu'elle sert des
requêtes bloquerait tout le monde.

Ici : la lecture du registre (résolution d'une requête vers une école),
le changement de statut (suspension d'un impayé) et les vérifications de
slug. Tout ce qui se contente de la base de contrôle.
"""

from datetime import date
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import TENANT_ACTIF, TENANT_RESILIEE, TENANT_SUSPENDUE, Tenant
from app.services.tenant_dto import TenantDetail

#: Statuts autorisés à ouvrir une session.
STATUTS_SERVICE = (TENANT_ACTIF,)


class TenantInvalide(Exception):
    """Le registre refuse : slug déjà pris, inconnu, statut illégal..."""


def slug_valide(slug: str) -> bool:
    """Un slug de tenant entre dans un nom de base : restons stricts."""
    return (
        bool(slug)
        and len(slug) <= 50
        and slug == slug.lower()
        and all(c.isalnum() or c in ("-", "_") for c in slug)
    )


def url_base_tenant(slug: str) -> str:
    """L'URL de la base physique d'une école (même règle que le routage)."""
    from app.core.database import get_tenant_database_url

    return get_tenant_database_url(slug)


async def resoudre(db: AsyncSession, slug: str) -> Optional[Tenant]:
    """Le tenant du registre pour ce slug, s'il existe et est en service.

    ``None`` pour un slug inconnu comme pour une école suspendue ou
    résiliée : le résolveur répond « école inconnue », sans distinguer —
    une école suspendue n'a pas à apprendre qu'elle l'est par une réponse
    technique de son logiciel de gestion.
    """
    if not slug:
        return None
    ligne = (
        await db.execute(
            text("SELECT * FROM tenants WHERE slug = :slug"),
            {"slug": slug},
        )
    ).first()
    if ligne is None:
        return None
    if ligne.statut not in STATUTS_SERVICE:
        return None
    return Tenant(
        id=ligne.id,
        slug=ligne.slug,
        nom=ligne.nom,
        statut=ligne.statut,
        plan=ligne.plan,
        abonnement_jusquau=ligne.abonnement_jusquau,
        contact_email=ligne.contact_email,
        created_at=ligne.created_at,
        updated_at=ligne.updated_at,
    )


async def lister(db: AsyncSession) -> List[TenantDetail]:
    """Toutes les écoles du registre, pour l'exploitation."""
    lignes = (await db.execute(text("SELECT * FROM tenants ORDER BY slug"))).all()
    return [
        TenantDetail(
            id=l.id,
            slug=l.slug,
            nom=l.nom,
            statut=l.statut,
            plan=l.plan,
            abonnement_jusquau=l.abonnement_jusquau,
            contact_email=l.contact_email,
            created_at=l.created_at,
        )
        for l in lignes
    ]


async def changer_statut(db: AsyncSession, slug: str, statut: str) -> TenantDetail:
    """Suspend (impayé), réactive ou résilie une école."""
    if statut not in (TENANT_ACTIF, TENANT_SUSPENDUE, TENANT_RESILIEE):
        raise TenantInvalide(f"Statut inconnu : {statut}.")
    ligne = (
        await db.execute(text("SELECT * FROM tenants WHERE slug = :slug"), {"slug": slug})
    ).first()
    if ligne is None:
        raise TenantInvalide(f"Aucun tenant « {slug} » dans le registre.")
    await db.execute(
        text("UPDATE tenants SET statut = :statut, updated_at = now() WHERE slug = :slug"),
        {"statut": statut, "slug": slug},
    )
    await db.commit()
    mis_a_jour = (
        await db.execute(text("SELECT * FROM tenants WHERE slug = :slug"), {"slug": slug})
    ).first()
    return TenantDetail(
        id=mis_a_jour.id,
        slug=mis_a_jour.slug,
        nom=mis_a_jour.nom,
        statut=mis_a_jour.statut,
        plan=mis_a_jour.plan,
        abonnement_jusquau=mis_a_jour.abonnement_jusquau,
        contact_email=mis_a_jour.contact_email,
        created_at=mis_a_jour.created_at,
    )
