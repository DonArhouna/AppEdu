"""
Documents officiels : tracabilite d'emission.

Un document officiel n'est pas un simple PDF : c'est un acte administratif.
L'etablissement doit pouvoir prouver ce qu'il a delivre, a qui, quand, par
qui, et sur la base de quelles donnees.  Cette table est donc le registre
d'emission.

Le PDF lui-meme vit sur le disque (comme les pieces d'admission) : PostgreSQL
ne conserve que le chemin relatif et l'empreinte SHA-256.

Le champ ``donnees`` conserve l'instantane des donnees au moment de
l'emission.  Un duplicata reedite avec les donnees actuelles : c'est le
comportement attendu d'un duplicata, et l'instantane initial reste
consultable.
"""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

#: JSON portable : JSONB sur PostgreSQL, JSON ailleurs.
JSONType = JSON().with_variant(JSONB, "postgresql")


class DocumentOfficiel(Base, TimestampMixin):
    """Un document officiel emis, avec son fichier et sa tracabilite."""

    __tablename__ = "documents_officiels"
    __table_args__ = (
        # Un numero est unique par type : deux certificats ne peuvent pas
        # porter le meme numero, meme si l'etablissement renumerote.
        Index("uq_documents_officiels_numero", "type_document", "numero", unique=True),
        Index("ix_documents_officiels_etudiant", "etudiant_id", unique=False),
        Index("ix_documents_officiels_type", "type_document", unique=False),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    #: Code du catalogue : ``certificat_scolarite``, ``releve_notes``, ``quitus_financier``.
    type_document: Mapped[str] = mapped_column(String(50), nullable=False)
    #: Numero lisible et sequentiel : ``CERT-2026-0001``.
    numero: Mapped[str] = mapped_column(String(50), nullable=False)

    etudiant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("etudiants.id", ondelete="CASCADE"), nullable=False
    )
    #: Session de rattachement lorsque le document en depend.
    session_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("sessions_academiques.id", ondelete="SET NULL"), nullable=True
    )
    annee: Mapped[int] = mapped_column(Integer, nullable=False)

    #: Chemin relatif du PDF dans le dossier de runtime.
    fichier: Mapped[str] = mapped_column(String(500), nullable=False)
    #: Empreinte du PDF : detecte toute alteration du document emis.
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    taille_octets: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    #: Instantane des donnees au moment de l'emission.
    donnees: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    #: Champs obligatoires qui ne pouvaient pas etre documentes.
    reserves: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)

    #: ``duplicata`` : le document remplace un document perdu ou detruuit.
    remplace_document_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("documents_officiels.id", ondelete="SET NULL"), nullable=True
    )
    motif_duplicata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    emis_par_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True
    )
    emis_le: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    #: Delivrance physique constatee par l'administration.
    delivre_le: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    etudiant: Mapped["Etudiant"] = relationship("Etudiant", lazy="selectin")
    session: Mapped[Optional["SessionAcademique"]] = relationship(
        "SessionAcademique", lazy="selectin"
    )

    def __repr__(self) -> str:  # pragma: no cover - confort de debug
        return f"<DocumentOfficiel {self.numero} type={self.type_document}>"


__all__ = ["DocumentOfficiel", "JSONType"]
