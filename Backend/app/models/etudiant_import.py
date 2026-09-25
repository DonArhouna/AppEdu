"""
Import massif d'etudiants : lots et lignes.

Le module ne duplique aucune donnee metier.  Un *lot* conserve le fichier
analyse, son rapport et son resultat ; une *ligne* conserve la donnee source,
les erreurs, les avertissements et l'etudiant finalement cree ou mis a jour.

L'import est toujours en deux temps :

1. ``analyse``  : lecture, resolution des referentiels, rapport ligne a ligne.
   **Aucune ecriture metier.**  L'admin voit ce qui passera et ce qui echouera.
2. ``valider``  : ecriture des seules lignes valides, dans la transaction de
   l'appelant.  Une ligne en erreur n'annule pas les autres, et le rapport
   conserve le detail.

Aucune donnee n'est inventee : un import ne cree ni filiere, ni session, ni
classe, ni niveau.  Une reference inconnue produit une erreur de ligne, pas
une creation silencieuse.
"""

from typing import List, Optional

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

#: JSON portable : JSONB sur PostgreSQL, JSON ailleurs (SQLite des tests).
JSONType = JSON().with_variant(JSONB, "postgresql")

#: Statuts d'un lot.
STATUT_ANALYSE = "analyse"
STATUT_VALIDE = "valide"
STATUT_TERMINE = "termine"
STATUT_ANNULE = "annule"
STATUT_ERREUR = "erreur"

#: Statuts d'une ligne.
LIGNE_VALIDE = "valide"
LIGNE_ERREUR = "erreur"
LIGNE_IGNORE = "ignore"
LIGNE_IMPORTEE = "importee"
LIGNE_MISE_A_JOUR = "mise_a_jour"

#: Actions decidees par l'analyse.
ACTION_CREER = "creer"
ACTION_MAJ = "mettre_a_jour"
ACTION_RIEN = "aucune"


class EtudiantImportBatch(Base, TimestampMixin):
    """Un depot de fichier analyse, puis eventuellement valide."""

    __tablename__ = "etudiants_import_batches"
    __table_args__ = (
        Index("ix_etudiants_import_batches_statut", "statut", unique=False),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nom_fichier: Mapped[str] = mapped_column(String(255), nullable=False)
    #: ``csv`` ou ``xlsx`` : le format reellement lu.
    format_source: Mapped[str] = mapped_column(String(10), nullable=False)
    statut: Mapped[str] = mapped_column(String(20), nullable=False)

    nb_lignes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nb_creer: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nb_mettre_a_jour: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nb_erreurs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nb_avertissements: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nb_importes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nb_ignorees: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    #: Colonnes reconnues et colonnes ignorees, pour expliquer le rapport.
    colonnes: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    #: Regle de cumul retenue a l'analyse : ``creation`` ou ``mise_a_jour``.
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="creation")
    #: Message terminal en cas d'echec global du depot.
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    cree_par_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True
    )

    rows: Mapped[List["EtudiantImportRow"]] = relationship(
        "EtudiantImportRow",
        back_populates="batch",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="EtudiantImportRow.ligne",
    )

    def __repr__(self) -> str:  # pragma: no cover - confort de debug
        return f"<EtudiantImportBatch {self.id} {self.nom_fichier} {self.statut}>"


class EtudiantImportRow(Base):
    """Une ligne source du fichier, avec son diagnostic et son resultat."""

    __tablename__ = "etudiants_import_rows"
    __table_args__ = (
        Index("ix_etudiants_import_rows_batch", "batch_id", unique=False),
        Index("uq_etudiants_import_rows_batch_ligne", "batch_id", "ligne", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("etudiants_import_batches.id", ondelete="CASCADE"), nullable=False
    )
    #: Numero de ligne tel que vu dans le fichier (1 = premiere ligne de donnees).
    ligne: Mapped[int] = mapped_column(Integer, nullable=False)
    statut: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False, default=ACTION_RIEN)

    #: Valeurs normalisees et resolues, pretes pour l'ecriture.
    donnees: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    #: Ligne brute telle que lue, pour diagnostic.
    brut: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    erreurs: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    avertissements: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)

    matricule: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    etudiant_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("etudiants.id", ondelete="SET NULL"), nullable=True
    )

    batch: Mapped[EtudiantImportBatch] = relationship(
        "EtudiantImportBatch", back_populates="rows"
    )

    def __repr__(self) -> str:  # pragma: no cover - confort de debug
        return f"<EtudiantImportRow {self.batch_id}:{self.ligne} {self.statut}>"


__all__ = [
    "EtudiantImportBatch",
    "EtudiantImportRow",
    "JSONType",
    "STATUT_ANALYSE",
    "STATUT_VALIDE",
    "STATUT_TERMINE",
    "STATUT_ANNULE",
    "STATUT_ERREUR",
    "LIGNE_VALIDE",
    "LIGNE_ERREUR",
    "LIGNE_IGNORE",
    "LIGNE_IMPORTEE",
    "LIGNE_MISE_A_JOUR",
    "ACTION_CREER",
    "ACTION_MAJ",
    "ACTION_RIEN",
]
