"""
Modèle Utilisateur : Gestion des comptes, authentification et rôles RBAC.
"""

from enum import Enum
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Integer
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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Authentification
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Identité
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    prenom: Mapped[str] = mapped_column(String(100), nullable=False)
    telephone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Rôle RBAC : ADMIN | DIRECTEUR_ETUDES | SECRETARIAT | COMPTABILITE | ENSEIGNANT | ETUDIANT
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="ADMIN")
    
    # Statut
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def full_name(self) -> str:
        return f"{self.prenom} {self.nom}".strip()

    def __repr__(self) -> str:
        return f"<Utilisateur id={self.id} email='{self.email}' role='{self.role}'>"
