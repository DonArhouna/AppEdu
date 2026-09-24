"""
Modèles Structure Académique :
- Campus : Sites physiques de l'établissement
- Departement : Départements d'enseignement rattachés à un campus
- Filiere : Programmes de formation rattachés à un département
- UniteEnseignement (UE) : Blocs de compétences avec crédits ECTS
- Matiere (ECUE) : Matières composant les UEs avec coefficients et volumes horaires
"""

from typing import List, Optional
from sqlalchemy import String, Integer, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class Campus(Base, TimestampMixin):
    __tablename__ = "campuses"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    adresse: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ville: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    responsable: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    telephone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relations
    departements: Mapped[List["Departement"]] = relationship(
        "Departement", back_populates="campus", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Campus code='{self.code}' nom='{self.nom}'>"


class Departement(Base, TimestampMixin):
    __tablename__ = "departements"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    campus_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("campuses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    responsable: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    # Relations
    campus: Mapped[Optional["Campus"]] = relationship("Campus", back_populates="departements")
    filieres: Mapped[List["Filiere"]] = relationship(
        "Filiere", back_populates="departement", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Departement code='{self.code}' nom='{self.nom}'>"


class Filiere(Base, TimestampMixin):
    __tablename__ = "filieres"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    departement_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("departements.id", ondelete="SET NULL"), nullable=True, index=True
    )
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    diplome: Mapped[str] = mapped_column(String(50), nullable=False)
    duree: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relations
    departement: Mapped[Optional["Departement"]] = relationship("Departement", back_populates="filieres")
    unites_enseignement: Mapped[List["UniteEnseignement"]] = relationship(
        "UniteEnseignement", back_populates="filiere", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Filiere code='{self.code}' nom='{self.nom}'>"


class UniteEnseignement(Base, TimestampMixin):
    __tablename__ = "unites_enseignement"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    filiere_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("filieres.id", ondelete="CASCADE"), nullable=True, index=True
    )
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False)  # ECTS
    coefficient: Mapped[float] = mapped_column(Float, nullable=False)
    heures: Mapped[int] = mapped_column(Integer, nullable=False)
    semestre: Mapped[str] = mapped_column(String(20), nullable=False)  # S1..S6
    niveau: Mapped[str] = mapped_column(String(50), nullable=False)
    responsable: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    # Relations
    filiere: Mapped[Optional["Filiere"]] = relationship("Filiere", back_populates="unites_enseignement")
    matieres: Mapped[List["Matiere"]] = relationship(
        "Matiere", back_populates="ue", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<UniteEnseignement code='{self.code}' credits={self.credits}>"


class Matiere(Base, TimestampMixin):
    __tablename__ = "matieres"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    ue_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("unites_enseignement.id", ondelete="CASCADE"), nullable=True, index=True
    )
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False)
    coefficient: Mapped[float] = mapped_column(Float, nullable=False)
    heures_cm: Mapped[int] = mapped_column(Integer, nullable=False)
    heures_td: Mapped[int] = mapped_column(Integer, nullable=False)
    heures_tp: Mapped[int] = mapped_column(Integer, nullable=False)
    enseignant_nom: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relations
    ue: Mapped[Optional["UniteEnseignement"]] = relationship("UniteEnseignement", back_populates="matieres")

    def __repr__(self) -> str:
        return f"<Matiere code='{self.code}' nom='{self.nom}'>"
