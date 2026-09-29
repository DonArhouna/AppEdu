"""
Modèle PaiementIntent : une intention de paiement en ligne (lot 4b).

Le paiement en ligne est un processus en deux temps, comme un guichet
différé : d'abord une **intention** — « cette facture peut être payée pour
tant, via ce lien » — puis la **confirmation** — « la famille a payé, la
caisse doit suivre ». L'intention porte l'empreinte SHA-256 du jeton du
lien, jamais le jeton : une base interceptée ne doit pas contenir de quoi
payer à la place de la famille.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

#: Statuts de vie d'une intention.
INTENT_EN_ATTENTE = "en_attente"
INTENT_CONFIRMEE = "confirmee"
INTENT_ANNULEE = "annulee"
INTENT_EXPIREE = "expiree"


class PaiementIntent(Base, TimestampMixin):
    __tablename__ = "paiement_intents"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    facture_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("factures.id", ondelete="CASCADE"), nullable=True, index=True
    )
    etudiant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("etudiants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("sessions_academiques.id", ondelete="CASCADE"), nullable=False
    )
    periode_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    #: Ce que l'intention autorise, figé à la création : une facture qui
    #: évolue ensuite n'élargit pas le lien déjà émis.
    montant: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    #: L'empreinte SHA-256 du jeton du lien — jamais le jeton. Le lien
    #: complet ne vit que dans la réponse de création.
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    statut: Mapped[str] = mapped_column(String(20), nullable=False, default=INTENT_EN_ATTENTE)
    #: ``simulation`` tant qu'aucune passerelle réelle n'est branchée ; le
    #: jour venu, « wave », « orange_money », « stripe »...
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="simulation")
    expires_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmee_le: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    #: Le paiement créé par la confirmation. Non-FK pour survivre à un
    #: purge ultérieure sans casser la trace.
    paiement_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    creee_par_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True
    )

    facture: Mapped[Optional["Facture"]] = relationship("Facture", lazy="selectin")
    etudiant: Mapped["Etudiant"] = relationship("Etudiant", lazy="selectin")
    session: Mapped["SessionAcademique"] = relationship("SessionAcademique", lazy="selectin")
    creee_par: Mapped[Optional["Utilisateur"]] = relationship("Utilisateur", lazy="selectin")

    def __repr__(self) -> str:
        return (
            f"<PaiementIntent etudiant={self.etudiant_id} montant={self.montant} "
            f"statut='{self.statut}'>"
        )
