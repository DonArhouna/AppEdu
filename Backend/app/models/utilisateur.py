"""
Modèle Utilisateur : Gestion des comptes, authentification et rôles RBAC.
"""

from enum import Enum
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    DIRECTEUR_ETUDES = "DIRECTEUR_ETUDES"
    SECRETARIAT = "SECRETARIAT"
    COMPTABILITE = "COMPTABILITE"
    ENSEIGNANT = "ENSEIGNANT"
    ETUDIANT = "ETUDIANT"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class Utilisateur(Base, TimestampMixin):
    __tablename__ = "utilisateurs"
    __table_args__ = (
        Index("uq_utilisateurs_etudiant_id", "etudiant_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Authentification
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Identité
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    prenom: Mapped[str] = mapped_column(String(100), nullable=False)
    telephone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # Lien optionnel vers le dossier métier pour les portails auto-service.
    etudiant_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("etudiants.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Rôle RBAC : ADMIN | DIRECTEUR_ETUDES | SECRETARIAT | COMPTABILITE | ENSEIGNANT | ETUDIANT
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Statut
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def full_name(self) -> str:
        return f"{self.prenom} {self.nom}".strip()

    def __repr__(self) -> str:
        return f"<Utilisateur id={self.id} email='{self.email}' role='{self.role}'>"
