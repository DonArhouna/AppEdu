"""
Modèles Structure Académique :
- Campus : Sites physiques de l'établissement
- Departement : Départements d'enseignement rattachés à un campus
- Filiere : Programmes de formation rattachés à un département
- UniteEnseignement (UE) : Blocs de compétences avec crédits ECTS
- Matiere (ECUE) : Matières composant les UEs avec coefficients et volumes horaires
"""

import uuid
from datetime import date
from typing import List, Optional
from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
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


#: Une UE ne compte que dans le semestre auquel elle est rattachee. C'est le
#: regime de tout ce qui existait avant la gestion des reglages d'enseignement
#: annuel.
REGIME_SEMESTRIELLE = "semestrielle"

#: Une UE annuelle est suivie sur toute l'annee : elle figure sur tous les
#: semestres de la session, et elle est notee sur chacun.
REGIME_ANNUELLE = "annuelle"

REGIMES = (REGIME_SEMESTRIELLE, REGIME_ANNUELLE)


class Semestre(Base, TimestampMixin):
    """Un semestre d'une session : son numero, son libelle, ses dates.

    Le numero donne l'ordre — c'est lui qui dit quel semestre precede quel
    autre — et le libelle ce que l'institut ecrit. Les deux sont necessaires :
    l'un sans l'autre, soit le bulletin affiche « 1 », soit il suppose que
    « S1 » et « s1 » designent la meme chose.
    """

    __tablename__ = "semestres"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("sessions_academiques.id", ondelete="CASCADE"), nullable=False
    )
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    libelle: Mapped[str] = mapped_column(String(50), nullable=False)
    date_debut: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    date_fin: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    session = relationship("SessionAcademique", lazy="selectin")
    # Pas de ``back_populates`` vers l'UE : la colonne ``semestre`` de l'UE
    # porte ce nom, et une relation de meme nom la masquerait.

    __table_args__ = (
        # Deux « semestre 1 » dans la meme session rendraient la moyenne par
        # semestre ambigue : on ne saurait pas laquelle des deux lire.
        UniqueConstraint("session_id", "numero", name="uq_semestres_session_numero"),
        Index("ix_semestres_session", "session_id", "numero"),
    )

    def __repr__(self) -> str:
        return f"<Semestre {self.libelle} ({self.session_id})>"


class UniteEnseignement(Base, TimestampMixin):
    __tablename__ = "unites_enseignement"
    __table_args__ = (Index("ix_unites_enseignement_semestre", "semestre_id"),)

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    filiere_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("filieres.id", ondelete="CASCADE"), nullable=True, index=True
    )
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False)  # ECTS
    coefficient: Mapped[float] = mapped_column(Float, nullable=False)
    heures: Mapped[int] = mapped_column(Integer, nullable=False)
    #: Libelle d'affichage du semestre. **Nullable** : une UE annuelle se
    #: retrouve sur tous les semestres et n'en designe aucun. Ce n'est plus la
    #: source de structure — ``semestre_id`` l'est.
    semestre: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # Rattachement structurel au semestre. Nullable : une UE sans semestre
    # est signalee, pas devinee.
    semestre_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("semestres.id", ondelete="SET NULL"), nullable=True
    )
    #: ``semestrielle`` (defaut) ou ``annuelle``.
    #:
    #: Une UE annuelle est suivie sur toute l'annee : elle figure sur **tous**
    #: les semestres de la session, et elle est notee sur chacun. C'est la
    #: difference d'avec une UE simplement oubliee de son semestre — celle-la
    #: sortira des bulletins, celle-ci y entre deux fois.
    regime: Mapped[str] = mapped_column(
        String(20), nullable=False, default=REGIME_SEMESTRIELLE, server_default=REGIME_SEMESTRIELLE
    )
    niveau: Mapped[str] = mapped_column(String(50), nullable=False)
    responsable: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    # Relations
    filiere: Mapped[Optional["Filiere"]] = relationship("Filiere", back_populates="unites_enseignement")
    # **Pas de relation nommee ``semestre``** : la colonne porte deja ce nom, et
    # une relation de meme nom la masque — la colonne disparait des
    # metadonnees et de toute lecture. Le lien se lit par ``semestre_id``, ou
    # par une jointure explicite la ou le semestre est necessaire (bulletin).
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
