"""
Relances de facturation : ce qu'on a fait pour recouvrer.

Une relance est un **acte constate**, pas un envoi automatique. Le modele
fige ce qui a ete reclame au moment de la relance : une facture soldee depuis
ne doit pas reecrire l'historique, sinon « 150 000 reclames le 3 mars »
cesserait d'etre vrai.

``solde_apres`` est laisse a ``NULL`` a l'ecriture, et renseigne par un appel
distinct quand un encaissement est constate. Il decrit ce que la situation
valait **apres** la relance, pas aujourd'hui : un paiement de mai ne doit pas
retroagir sur une relance de janvier.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

#: JSON portable : JSONB sur PostgreSQL, JSON ailleurs.
JSONType = JSON().with_variant(JSONB, "postgresql")


class Relance(Base):
    """Une relance constatee, avec l'instantane de ce qui etait reclame."""

    __tablename__ = "relances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    etudiant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("etudiants.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("sessions_academiques.id", ondelete="SET NULL"), nullable=True
    )
    #: 1re, 2e, 3e... sur la dette de cet etudiant. Calcule a l'ecriture
    #: depuis les relances deja enregistrees, jamais saisi.
    niveau: Mapped[int] = mapped_column(Integer, nullable=False)
    date_relance: Mapped[date] = mapped_column(Date, nullable=False)
    #: Libelle pris dans une liste fermee, pour que l'historique reste
    #: lisible d'un bout a l'autre.
    moyen: Mapped[str] = mapped_column(String(30), nullable=False)
    #: Total reclame ce jour-la.
    montant_reclame: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    #: Les factures concernees, avec leur reste au moment de la relance.
    factures_concernees: Mapped[List[Dict[str, Any]]] = mapped_column(
        "factures_concernees", JSONType, nullable=False, default=list
    )
    #: Retard de la plus ancienne echeance : c'est l'anciennete qui justifie
    #: la relance.
    retard_jours: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    #: Solde constate apres la relance. ``NULL`` tant qu'aucun encaissement
    #: n'a suivi : une relance efficace n'est pas un solde sur du papier.
    solde_apres: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    relance_par_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True
    )
    #: Trace du dernier envoi de la lettre par email (lot 4). ``NULL`` tant
    #: qu'aucun envoi n'a ete demande ; le statut dit ce qui s'est passe —
    #: ``envoye`` (parti), ``simule`` (SMTP non configure) ou ``echec``
    #: (serveur de courrier injoignable). L'application ne pretend jamais
    #: avoir contacte un etudiant qu'elle n'a pas contacte.
    email_envoye_le: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    email_statut: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    etudiant = relationship("Etudiant", lazy="selectin")
    auteur = relationship("Utilisateur", lazy="selectin")

    __table_args__ = (
        # Suivi d'un etudiant : l'historique et le prochain niveau se lisent
        # par etudiant, du plus ancien au plus recent.
        Index("ix_relances_etudiant", "etudiant_id", "date_relance"),
        # Vue « a relancer » : les creances les plus anciennes d'abord.
        Index("ix_relances_date", "date_relance"),
    )

    @property
    def resolue(self) -> bool:
        """Un encaissement a-t-il suivi la relance ?"""

        return self.solde_apres is not None and self.solde_apres <= 0

    def __repr__(self) -> str:
        return (
            f"<Relance etudiant={self.etudiant_id} niveau={self.niveau} "
            f"montant={self.montant_reclame}>"
        )


__all__ = ["Relance"]
