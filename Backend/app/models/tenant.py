"""
Modèle Tenant : une école cliente, côté base de contrôle (lot 6).

Le registre vit sur ``DATABASE_URL`` — la base de contrôle — et non dans
les bases des écoles : c'est elle qui sait qui existe, où est sa base et
quel est son statut. Une école ne doit pas pouvoir lire le registre de ses
concierges ; le registre, lui, ne contient aucune donnée métier.

Le slug nomme trois choses à la fois : l'identifiant de résolution
(``X-Tenant-ID: isi``), la base physique (``emp_tenant_isi``) et — le jour
du déploiement SaaS — le sous-domaine (``isi.edumanagepro.com``).
"""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

#: Statuts de vie d'une école cliente.
TENANT_ACTIF = "active"
TENANT_SUSPENDUE = "suspendue"
TENANT_RESILIEE = "resiliee"


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    #: Identifiant court, alphanumérique + ``-`` + ``_`` : il entre dans le
    #: nom de la base et dans l'en-tête de résolution.
    slug: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    statut: Mapped[str] = mapped_column(String(20), nullable=False, default=TENANT_ACTIF)
    #: Étiquette commerciale libre : ``standard``, ``premium``... Le
    #: provisionneur ne l'interprète pas, la facturation la lira.
    plan: Mapped[str] = mapped_column(String(50), nullable=False, default="standard")
    #: Fin de l'abonnement payé. ``None`` = pas de limite (pilote, on-premise).
    abonnement_jusquau: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Tenant slug='{self.slug}' nom='{self.nom}' statut='{self.statut}'>"
