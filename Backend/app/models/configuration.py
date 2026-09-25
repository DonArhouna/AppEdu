"""Configuration institutionnelle versionnee.

L'identite d'un etablissement (nom, sigle, adresse, contacts, devise) et son
logo ne sont pas des constantes : ils changent. Un certificat de mars et un
certificat de septembre doivent pouvoir etre distingues, et l'etablissement
doit pouvoir repondre a « qui a change l'adresse, et quand ? ».

Chaque ecriture produit donc une **version** :

- ``version`` : numerotation sequentielle, unique par etablissement ;
- ``nature`` : ce qui a ete touche (identite ou branding) ;
- ``modifications`` : champ par champ, l'ancienne valeur — l'historique se
  lit sans avoir a rejouer toute la chronologie ;
- ``instantane`` : l'etat complet apres ecriture, pour restaurer ;
- ``logo_present`` : si un logo existait a cette version, meme si le fichier
  a disparu depuis (un logo perdu est une information de traçabilite).

Le logo lui-meme n'est pas dans cette table : c'est un fichier, il vit dans
``storage/etablissement`` comme les autres pieces.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

#: JSON portable : JSONB sur PostgreSQL, JSON ailleurs.
JSONType = JSON().with_variant(JSONB, "postgresql")


class ConfigurationVersion(Base):
    """Une version de la configuration institutionnelle."""

    __tablename__ = "configuration_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    etablissement_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("etablissements.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    nature: Mapped[str] = mapped_column(String(30), nullable=False)
    modifications: Mapped[Dict[str, Any]] = mapped_column(
        "modifications", JSONType, nullable=False, default=dict
    )
    instantane: Mapped[Dict[str, Any]] = mapped_column(
        "instantane", JSONType, nullable=False, default=dict
    )
    logo_present: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    modifie_par_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True
    )
    modifie_par_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    etablissement = relationship("Etablissement", lazy="selectin")
    #: Relation avec l'utilisateur, sans exposer son mot de passe ni ses roles.
    auteur = relationship("Utilisateur", lazy="selectin")

    __table_args__ = (
        Index("uq_configuration_versions_numero", "etablissement_id", "version", unique=True),
        Index("ix_configuration_versions_etablissement", "etablissement_id", "version"),
    )

    def __repr__(self) -> str:
        return (
            f"<ConfigurationVersion etablissement={self.etablissement_id} "
            f"version={self.version} nature={self.nature}>"
        )
