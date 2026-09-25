"""
Modèle Etudiant :
Gestion des données académiques et administratives des étudiants.
Rattaché optionnellement à une Filière et à une Session Académique.
"""

from datetime import date
from typing import List, Optional
from sqlalchemy import String, Date, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class Etudiant(Base, TimestampMixin):
    __tablename__ = "etudiants"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    matricule: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    prenom: Mapped[str] = mapped_column(String(100), nullable=False)
    sexe: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    telephone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    date_naissance: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    adresse: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Filière & Niveau
    filiere: Mapped[str] = mapped_column(String(100), nullable=False)
    filiere_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("filieres.id", ondelete="SET NULL"), nullable=True, index=True
    )
    niveau: Mapped[str] = mapped_column(String(50), nullable=False)
    statut: Mapped[str] = mapped_column(String(30), nullable=False)
    photo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    date_inscription: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Rattachement à une session académique
    session_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("sessions_academiques.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Rattachement canonique à une Classe.  Cette colonne est volontairement
    # nullable : les anciennes fiches restent lisibles et ne sont pas
    # rétro-architecturées par la migration.
    classe_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("classes.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    session: Mapped[Optional["SessionAcademique"]] = relationship("SessionAcademique", lazy="selectin")
    filiere_obj: Mapped[Optional["Filiere"]] = relationship("Filiere", lazy="selectin")
    classe: Mapped[Optional["Classe"]] = relationship("Classe", lazy="selectin")
    inscriptions: Mapped[List["Inscription"]] = relationship(
        "Inscription",
        back_populates="etudiant",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Etudiant matricule='{self.matricule}' nom='{self.nom}' prenom='{self.prenom}'>"
