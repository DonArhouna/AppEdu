"""
Modèles Finances :
- Facture : Appels de frais de scolarité / écolages
- Paiement : Transactions d'encaissement rattachées aux tranches de sessions
- Recu : Reçus fiscaux/scolaires numérotés avec données structurées pour impression
"""

from datetime import date
from typing import List, Optional
from sqlalchemy import String, Float, Date, ForeignKey, Text, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class GrilleTarifaire(Base, TimestampMixin):
    """Grille de frais définie par filière et niveau.

    Les montants sont des données de configuration métier : aucune valeur n'est
    créée automatiquement au premier lancement. ``total_annuel`` est calculé à
    partir des valeurs saisies par l'établissement.
    """

    __tablename__ = "grilles_tarifaires"
    __table_args__ = (
        UniqueConstraint("filiere", "niveau", name="uq_grilles_tarifaires_filiere_niveau"),
    )

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    filiere_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("filieres.id", ondelete="SET NULL"), nullable=True, index=True
    )
    filiere: Mapped[str] = mapped_column(String(255), nullable=False)
    niveau: Mapped[str] = mapped_column(String(100), nullable=False)
    droits_inscription: Mapped[float] = mapped_column(Float, nullable=False)
    scolarite_mensuelle: Mapped[float] = mapped_column(Float, nullable=False)
    nombre_mois: Mapped[int] = mapped_column(nullable=False)
    actif: Mapped[bool] = mapped_column(nullable=False, default=True)

    @property
    def total_annuel(self) -> float:
        return round(self.droits_inscription + (self.scolarite_mensuelle * self.nombre_mois), 2)

    def __repr__(self) -> str:
        return f"<GrilleTarifaire {self.filiere!r} / {self.niveau!r}>"


class Facture(Base, TimestampMixin):
    __tablename__ = "factures"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    numero_facture: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    etudiant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("etudiants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("sessions_academiques.id", ondelete="CASCADE"), nullable=False, index=True
    )
    montant_total: Mapped[float] = mapped_column(Float, nullable=False)
    montant_paye: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    date_emission: Mapped[date] = mapped_column(Date, nullable=False)
    date_echeance: Mapped[date] = mapped_column(Date, nullable=False)
    statut: Mapped[str] = mapped_column(String(30), nullable=False, default="emise")  # emise, partielle, payee, echue
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    etudiant: Mapped["Etudiant"] = relationship("Etudiant", lazy="selectin")
    session: Mapped["SessionAcademique"] = relationship("SessionAcademique", lazy="selectin")
    paiements: Mapped[List["Paiement"]] = relationship("Paiement", back_populates="facture")

    @property
    def reste_a_payer(self) -> float:
        return max(0.0, round(self.montant_total - self.montant_paye, 2))

    def __repr__(self) -> str:
        return f"<Facture '{self.numero_facture}' total={self.montant_total} statut='{self.statut}'>"


class Paiement(Base, TimestampMixin):
    __tablename__ = "paiements"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    facture_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("factures.id", ondelete="SET NULL"), nullable=True, index=True
    )
    etudiant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("etudiants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("sessions_academiques.id", ondelete="CASCADE"), nullable=False, index=True
    )
    periode_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("periodes_paiement.id", ondelete="SET NULL"), nullable=True, index=True
    )
    montant: Mapped[float] = mapped_column(Float, nullable=False)
    date_paiement: Mapped[date] = mapped_column(Date, nullable=False)
    mode_paiement: Mapped[str] = mapped_column(String(50), nullable=False, default="Espèces")  # Espèces, Wave, Orange Money, Chèque, Virement
    reference: Mapped[str] = mapped_column(String(100), nullable=False)
    statut: Mapped[str] = mapped_column(String(30), nullable=False, default="valide")  # valide, en_attente, echoue
    encaisse_par_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True
    )

    facture: Mapped[Optional["Facture"]] = relationship("Facture", back_populates="paiements")
    etudiant: Mapped["Etudiant"] = relationship("Etudiant", lazy="selectin")
    session: Mapped["SessionAcademique"] = relationship("SessionAcademique", lazy="selectin")
    periode: Mapped[Optional["PeriodePaiement"]] = relationship("PeriodePaiement", lazy="selectin")
    recu: Mapped[Optional["Recu"]] = relationship("Recu", back_populates="paiement", uselist=False)

    def __repr__(self) -> str:
        return f"<Paiement ref='{self.reference}' montant={self.montant}>"


class Recu(Base, TimestampMixin):
    __tablename__ = "recus"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    numero_recu: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    paiement_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("paiements.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    date_emission: Mapped[date] = mapped_column(Date, nullable=False)
    donnees_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    paiement: Mapped["Paiement"] = relationship("Paiement", back_populates="recu")

    def __repr__(self) -> str:
        return f"<Recu num='{self.numero_recu}' date={self.date_emission}>"
