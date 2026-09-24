"""
Modèle Etablissement : Paramètres généraux de la structure scolaire, licence et état du setup.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class Etablissement(Base, TimestampMixin):
    __tablename__ = "etablissements"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    
    # Identité Établissement
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    sigle: Mapped[str] = mapped_column(
        "code", String(50), nullable=False, unique=True, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    telephone: Mapped[str] = mapped_column(String(50), nullable=False)
    adresse: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    pays: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    devise: Mapped[str] = mapped_column(String(10), nullable=False)
    
    # Licence & Activation
    licence_cle: Mapped[Optional[str]] = mapped_column("license_key", String(255), nullable=True)
    licence_statut: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Scellement du Setup Initial
    is_configured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    date_configuration: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Contexte global d'année académique, piloté par l'API.
    annee_academique_active: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    session_active_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("sessions_academiques.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    session_active: Mapped[Optional["SessionAcademique"]] = relationship(
        "SessionAcademique",
        foreign_keys=[session_active_id],
        lazy="selectin",
    )

    @property
    def code(self) -> str:
        return self.sigle

    @code.setter
    def code(self, value: str):
        self.sigle = value

    @property
    def license_key(self) -> Optional[str]:
        return self.licence_cle

    @license_key.setter
    def license_key(self, value: Optional[str]):
        self.licence_cle = value

    def __repr__(self) -> str:
        return f"<Etablissement id={self.id} nom='{self.nom}' configured={self.is_configured}>"
