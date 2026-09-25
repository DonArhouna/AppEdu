"""Modèles du workflow d'admissions.

Le workflow est volontairement transactionnel : une pièce représente ses
métadonnées, son statut et le chemin relatif d'un éventuel fichier local. Les
octets sont écrits par le service de stockage, jamais dans PostgreSQL.
"""

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Candidature(Base, TimestampMixin):
    __tablename__ = "candidatures"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    reference: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)

    # Identité et contact du candidat
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    prenom: Mapped[str] = mapped_column(String(100), nullable=False)
    sexe: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    date_naissance: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    telephone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    adresse: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Programme et session visés
    filiere_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("filieres.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    niveau: Mapped[str] = mapped_column(String(50), nullable=False)
    # Références normalisées, ajoutées sans modifier les projections texte
    # historiques.  Elles restent optionnelles pour ne pas inventer de
    # correspondance pour les anciennes candidatures.
    niveau_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("niveaux.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    classe_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("classes.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("sessions_academiques.id", ondelete="SET NULL"), nullable=True, index=True
    )

    statut: Mapped[str] = mapped_column(String(30), nullable=False, default="nouvelle", index=True)
    date_demande: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Liens de traçabilité et de conversion
    created_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    etudiant_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("etudiants.id", ondelete="SET NULL"), nullable=True, unique=True, index=True
    )

    filiere: Mapped["Filiere"] = relationship("Filiere", lazy="selectin")
    niveau_obj: Mapped[Optional["Niveau"]] = relationship(
        "Niveau",
        foreign_keys=[niveau_id],
        lazy="selectin",
    )
    classe: Mapped[Optional["Classe"]] = relationship(
        "Classe",
        foreign_keys=[classe_id],
        lazy="selectin",
    )
    session: Mapped[Optional["SessionAcademique"]] = relationship(
        "SessionAcademique", lazy="selectin"
    )
    etudiant: Mapped[Optional["Etudiant"]] = relationship("Etudiant", lazy="selectin")
    created_by: Mapped[Optional["Utilisateur"]] = relationship(
        "Utilisateur", foreign_keys=[created_by_id], lazy="selectin"
    )
    pieces: Mapped[List["PieceCandidature"]] = relationship(
        "PieceCandidature",
        back_populates="candidature",
        cascade="all, delete-orphan",
        order_by="PieceCandidature.created_at",
    )
    decisions: Mapped[List["DecisionAdmission"]] = relationship(
        "DecisionAdmission",
        back_populates="candidature",
        cascade="all, delete-orphan",
        order_by="DecisionAdmission.date_decision.desc()",
    )

    def __repr__(self) -> str:
        return f"<Candidature reference={self.reference!r} statut={self.statut!r}>"


class PieceCandidature(Base, TimestampMixin):
    __tablename__ = "pieces_candidature"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    candidature_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("candidatures.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    nom_fichier: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    chemin_stockage: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    statut: Mapped[str] = mapped_column(String(30), nullable=False, default="requise", index=True)
    date_depot: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    commentaire: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    valide_par_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True
    )
    date_validation: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    candidature: Mapped[Candidature] = relationship("Candidature", back_populates="pieces")
    valide_par: Mapped[Optional["Utilisateur"]] = relationship(
        "Utilisateur", foreign_keys=[valide_par_id], lazy="selectin"
    )

    @property
    def fichier_disponible(self) -> bool:
        """Indique qu'un chemin de fichier local est associé à la pièce."""
        return bool(self.chemin_stockage)

    def __repr__(self) -> str:
        return f"<PieceCandidature type={self.type!r} statut={self.statut!r}>"


class DecisionAdmission(Base, TimestampMixin):
    __tablename__ = "decisions_admission"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    candidature_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("candidatures.id", ondelete="CASCADE"), nullable=False, index=True
    )
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    motif: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decisionnaire_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("utilisateurs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    date_decision: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    candidature: Mapped[Candidature] = relationship("Candidature", back_populates="decisions")
    decisionnaire: Mapped["Utilisateur"] = relationship(
        "Utilisateur", foreign_keys=[decisionnaire_id], lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<DecisionAdmission decision={self.decision!r}>"
