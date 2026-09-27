"""Regle de fabrication des matricules, propre a l'etablissement.

La table ne porte que la **donnee** : un modele, une largeur de compteur, un
demarrage. La logique — validation, apercu, recherche du prochain numero — vit
dans ``app.services.matricule_service``, comme le reste du regle metier.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import select

from app.models.base import Base

#: Reproduit la regle codee en dur davant le parametre. Un institut qui n'a rien
#: regle doit obtenir exactement le comportement historique : c'est la garantie
#: que l'ajout de cette table ne change aucun matricule existant.
MODELE_DEPART = "{annee}-{filiere}-{numero}"
LARGEUR_DEPART = 4
DEMARRAGE_DEPART = 1


class ParametresMatricule(Base):
    """Nomenclature en vigueur pour les matricules de l'etablissement."""

    __tablename__ = "parametres_matricule"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    etablissement_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("etablissements.id", ondelete="CASCADE"), nullable=False
    )
    #: Modele du matricule. Seul ``{numero}`` est obligatoire.
    modele: Mapped[str] = mapped_column(String(120), nullable=False)
    #: Nombre de chiffres du compteur : 4 produit ``0001``.
    largeur_numero: Mapped[int] = mapped_column(
        Integer, nullable=False, default=LARGEUR_DEPART
    )
    #: Premier numero attribue. Permet a un institut de reprendre ailleurs.
    demarrage: Mapped[int] = mapped_column(Integer, nullable=False, default=DEMARRAGE_DEPART)
    maj_par_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    etablissement = relationship("Etablissement", lazy="selectin")
    maj_par = relationship("Utilisateur", lazy="selectin")

    __table_args__ = (
        # Une seule nomenclature par etablissement. Sans cela, deux lignes
        # pourraient fixer des regles differentes, et la lecture "la premiere"
        # deviendrait arbitraire.
        UniqueConstraint(
            "etablissement_id", name="uq_parametres_matricule_etablissement"
        ),
    )

    def __repr__(self) -> str:
        return f"<ParametresMatricule modele={self.modele!r}>"


__all__ = [
    "DEMARRAGE_DEPART",
    "LARGEUR_DEPART",
    "MODELE_DEPART",
    "ParametresMatricule",
]
