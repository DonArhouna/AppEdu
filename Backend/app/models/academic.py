"""Socle académique normalisé.

Le modèle historique conserve encore des colonnes texte sur les étudiants et les
candidatures.  Ce module ajoute les entités de référence et le lien
d'inscription sans/backfill implicite : les anciennes données restent telles
qu'elles sont jusqu'à une operation métier explicite.
"""

from datetime import date
from typing import List, Optional

from sqlalchemy import Boolean, Date, ForeignKey, Index, String, Text, UniqueConstraint, text, true
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym, validates

from app.models.base import Base, TimestampMixin


class Cycle(Base, TimestampMixin):
    """Cycle de diplôme (par exemple Licence ou Master).

    Les cycles ne sont pas initialises au demarrage de l'application.  Ils sont
    crees par un administrateur ou par l'action explicite de chargement LMD.
    """

    __tablename__ = "cycles"
    __table_args__ = (
        Index("uq_cycles_code", "code", unique=True),
    )

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ordre: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())

    niveaux: Mapped[List["Niveau"]] = relationship(
        "Niveau",
        back_populates="cycle",
        lazy="selectin",
    )

    # Alias metier requetable sans ajouter une colonne concurrente.
    libelle = synonym("nom")

    def __repr__(self) -> str:
        return f"<Cycle code={self.code!r} nom={self.nom!r}>"


class Niveau(Base, TimestampMixin):
    """Niveau reutilisable d'un cycle (L1, L2, M1, ...)."""

    __tablename__ = "niveaux"
    __table_args__ = (
        UniqueConstraint("cycle_id", "code", name="uq_niveaux_cycle_code"),
        Index("ix_niveaux_cycle_id", "cycle_id", unique=False),
    )

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    cycle_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("cycles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ordre: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())

    cycle: Mapped["Cycle"] = relationship("Cycle", back_populates="niveaux", lazy="selectin")
    classes: Mapped[List["Classe"]] = relationship(
        "Classe",
        back_populates="niveau",
        lazy="selectin",
    )

    libelle = synonym("nom")

    def __repr__(self) -> str:
        return f"<Niveau code={self.code!r} cycle_id={self.cycle_id!r}>"


class Classe(Base, TimestampMixin):
    """Classe metier reutilisable : une filiere associee a un niveau."""

    __tablename__ = "classes"
    __table_args__ = (
        UniqueConstraint("filiere_id", "niveau_id", name="uq_classes_filiere_niveau"),
        Index("ix_classes_filiere_niveau", "filiere_id", "niveau_id", unique=False),
        Index("ix_classes_filiere_id", "filiere_id", unique=False),
        Index("ix_classes_niveau_id", "niveau_id", unique=False),
    )

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    filiere_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("filieres.id", ondelete="RESTRICT"),
        nullable=False,
    )
    niveau_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("niveaux.id", ondelete="RESTRICT"),
        nullable=False,
    )
    nom: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())

    filiere: Mapped["Filiere"] = relationship("Filiere", lazy="selectin")
    niveau: Mapped["Niveau"] = relationship("Niveau", back_populates="classes", lazy="selectin")
    inscriptions: Mapped[List["Inscription"]] = relationship(
        "Inscription",
        back_populates="classe",
        lazy="selectin",
    )

    @property
    def cycle_id(self) -> Optional[str]:
        return self.niveau.cycle_id if self.niveau is not None else None

    @property
    def cycle(self) -> Optional["Cycle"]:
        return self.niveau.cycle if self.niveau is not None else None

    def __repr__(self) -> str:
        return f"<Classe id={self.id!r} filiere_id={self.filiere_id!r} niveau_id={self.niveau_id!r}>"


class Inscription(Base, TimestampMixin):
    """Rattachement historique et canonique d'un etudiant a une promotion.

    Une promotion est volontairement absente de cette version : elle sera la
    vue future ``Classe + Session``.  Ici, la ligne d'inscription conserve le
    triplet et son etat, ce qui permet de conserver les traces.
    """

    __tablename__ = "inscriptions"
    __table_args__ = (
        # SQLite et PostgreSQL supportent tous deux les index partiels.  Le
        # predicat est explicite dans chaque dialecte pour rester portable.
        Index(
            "uq_inscriptions_etudiant_session_active",
            "etudiant_id",
            "session_id",
            unique=True,
            sqlite_where=text("actif = 1"),
            postgresql_where=text("actif IS TRUE"),
        ),
        Index("ix_inscriptions_etudiant_id", "etudiant_id", unique=False),
        Index("ix_inscriptions_classe_id", "classe_id", unique=False),
        Index("ix_inscriptions_session_id", "session_id", unique=False),
        Index("ix_inscriptions_statut", "statut", unique=False),
    )

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    etudiant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("etudiants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    classe_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("classes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    session_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("sessions_academiques.id", ondelete="RESTRICT"),
        nullable=False,
    )
    actif: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )
    statut: Mapped[str] = mapped_column(
        String(30), nullable=False, default="active", server_default="active", index=False
    )
    date_inscription: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)

    etudiant: Mapped["Etudiant"] = relationship(
        "Etudiant",
        back_populates="inscriptions",
        lazy="selectin",
    )
    classe: Mapped["Classe"] = relationship("Classe", back_populates="inscriptions", lazy="selectin")
    session: Mapped["SessionAcademique"] = relationship(
        "SessionAcademique",
        back_populates="inscriptions",
        lazy="selectin",
    )

    @validates("statut")
    def _synchronise_actif(self, _key: str, value: str) -> str:
        """Garde la colonne booléenne cohérente pour les constructions ORM."""
        self.__dict__["actif"] = (value or "").lower() == "active"
        return value

    @property
    def est_active(self) -> bool:
        """Alias métier tolerant aux anciennes lignes au statut textuel."""
        return bool(self.actif) or (self.statut or "").lower() == "active"

    def __repr__(self) -> str:
        return f"<Inscription etudiant_id={self.etudiant_id!r} session_id={self.session_id!r} statut={self.statut!r}>"


__all__ = ["Cycle", "Niveau", "Classe", "Inscription"]
