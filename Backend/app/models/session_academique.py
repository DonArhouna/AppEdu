"""
Modèles SessionAcademique & PeriodePaiement :
Gestion des calendriers annuels et découpage dynamique des tranches de paiement.
"""

from datetime import date
from typing import List, Optional
from sqlalchemy import String, Date, Float, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class SessionAcademique(Base, TimestampMixin):
    __tablename__ = "sessions_academiques"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    annee_academique: Mapped[str] = mapped_column(String(20), nullable=False)
    date_debut: Mapped[date] = mapped_column(Date, nullable=False)
    date_fin: Mapped[date] = mapped_column(Date, nullable=False)
    statut: Mapped[str] = mapped_column(String(20), nullable=False)  # active | planifiee | cloturee
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relation 1-N vers les périodes de paiement
    periodes: Mapped[List["PeriodePaiement"]] = relationship(
        "PeriodePaiement",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="PeriodePaiement.ordre"
    )
    # Les inscriptions sont historiques : aucune suppression en cascade.
    inscriptions: Mapped[List["Inscription"]] = relationship(
        "Inscription",
        back_populates="session",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<SessionAcademique id='{self.id}' nom='{self.nom}' code='{self.code}'>"


class PeriodePaiement(Base, TimestampMixin):
    __tablename__ = "periodes_paiement"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(50), ForeignKey("sessions_academiques.id", ondelete="CASCADE"), nullable=False)
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    mois: Mapped[str] = mapped_column(String(30), nullable=False)
    date_echeance: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    montant_estime: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pourcentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ordre: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relation N-1 vers la session
    session: Mapped["SessionAcademique"] = relationship("SessionAcademique", back_populates="periodes")

    def __repr__(self) -> str:
        return f"<PeriodePaiement id='{self.id}' nom='{self.nom}' mois='{self.mois}' ordre={self.ordre}>"
