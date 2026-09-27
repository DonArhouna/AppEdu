"""
Deliberation : le verdict du jury, enfin enregistre.

Avant cet increment, la deliberation etait **calculee a la volee** et
**jamais enregistree**. Aucun proces-verbal, aucune date, aucun jury. C'est
volontiers : on ne peut pas attester d'une decision qui n'existe nulle part.

Trois objects :

1. ``ReglesDeliberation`` : le reglement de l'institut. Les seuils
   etaient codes en dur et dupliques dans le frontend ; un reglement
   academique n'est pas une constante technique. ``confirme_le`` distingue un
   reglement valide d'une valeur de depart jamais revue.

2. ``Deliberation`` : une seance de jury pour une promotion (classe +
   session), avec sa date, son lieu, son president et ses membres. Les regles
   sont **figees** dans la seance : modifier le reglement plus tard ne doit
   pas reecrire l'historique d'un jury deja tenu.

3. ``DeliberationDecision`` : ce que le jury a **decide**, avec la proposition
   du moteur conservee a cote. Un ecart entre les deux exige un motif : sans
   lui, la decision serait inexpliquee. Une decision calculee n'est jamais
   presentee comme une decision de jury.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

#: JSON portable : JSONB sur PostgreSQL, JSON ailleurs.
JSONType = JSON().with_variant(JSONB, "postgresql")


# ---------------------------------------------------------------------------
# Vocabulaire de decision
# ---------------------------------------------------------------------------
#: Ces libelles ne sont pas un reglement : ce sont les **valeurs possibles**
#: d'une decision. Le reglement (quelles moyennes-feat quelles mentions) vit
#: dans ``ReglesDeliberation``.
STATUTS = ("Admis", "Rattrapage", "Ajourne")

#: Mention obligatoire selon le statut : on n'attribue pas « Tres Bien » a un
#: ajourne. Le controle est applique a l'ecriture, pas seulement a l'affichage.
MENTIONS_PAR_STATUT: Dict[str, tuple] = {
    "Admis": (),          # rempli depuis le bareme des mentions
    "Rattrapage": ("Rattrapage",),
    "Ajourne": ("Ajourne",),
}


class ReglesDeliberation(Base):
    """Reglement de deliberation en vigueur pour l'etablissement."""

    __tablename__ = "regles_deliberation"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    etablissement_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("etablissements.id", ondelete="CASCADE"),
        nullable=False,
    )
    seuil_validation_moyenne: Mapped[float] = mapped_column(Float, nullable=False)
    seuil_eliminatoire: Mapped[float] = mapped_column(Float, nullable=False)
    #: Sous cette moyenne, l'etudiant est ajourne : le rattrapage n'est pas
    #: ouvert. Cette valeur etait en dur (8,5) dans le moteur d'origine.
    seuil_rattrapage_minimale: Mapped[float] = mapped_column(Float, nullable=False)
    seuil_passage_conditionnel_ects: Mapped[int] = mapped_column(Integer, nullable=False)
    compensation_autorisee: Mapped[bool] = mapped_column(Boolean, nullable=False)
    #: ``[{"libelle": ..., "seuil_min": ...}]``, du seuil le plus eleve au
    #: plus bas. Une mention est attribuee des que la moyenne l'atteint.
    bareme_mentions: Mapped[List[Dict[str, Any]]] = mapped_column(
        "bareme_mentions", JSONType, nullable=False
    )
    #: Renseignes quand l'institut valide son reglement. ``NULL`` = valeurs
    #: de depart, jamais revues — la deliberation ne peut pas s'appuyer dessus.
    confirme_par_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True
    )
    confirme_par_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    confirme_le: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("uq_regles_deliberation_etablissement", "etablissement_id", unique=True),
    )

    @property
    def confirmees(self) -> bool:
        """Le reglement a-t-il ete explicitement valide par l'institut ?"""

        return self.confirme_le is not None

    def mention_pour(self, moyenne: float) -> Optional[str]:
        """Mention correspondant a une moyenne, d'apres le bareme en vigueur."""

        for entree in sorted(
            self.bareme_mentions, key=lambda e: float(e.get("seuil_min", 0)), reverse=True
        ):
            if moyenne >= float(entree.get("seuil_min", 0)):
                libelle = str(entree.get("libelle") or "").strip()
                return libelle or None
        return None

    def __repr__(self) -> str:
        return (
            f"<ReglesDeliberation etablissement={self.etablissement_id} "
            f"seuil={self.seuil_validation_moyenne} confirmee={self.confirmees}>"
        )


class Deliberation(Base):
    """Une seance de jury pour une promotion et une session."""

    __tablename__ = "deliberations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    etablissement_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("etablissements.id", ondelete="CASCADE"),
        nullable=False,
    )
    classe_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("sessions_academiques.id", ondelete="CASCADE"),
        nullable=False,
    )
    date_deliberation: Mapped[date] = mapped_column(Date, nullable=False)
    lieu: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    president: Mapped[str] = mapped_column(String(150), nullable=False)
    #: ``[{"nom": ..., "qualite": ...}]``. La composition est saisie, jamais
    #: devinee : un PV qui inventerait les membres du jury n'aurait aucune valeur.
    membres: Mapped[List[Dict[str, Any]]] = mapped_column(
        "membres", JSONType, nullable=False, default=list
    )
    #: ``brouillon`` (seance en cours) ou ``close`` (verdict arrete).
    statut: Mapped[str] = mapped_column(String(20), nullable=False)
    #: Regles en vigueur au moment de la seance, figees telles quelles.
    regles: Mapped[Dict[str, Any]] = mapped_column("regles", JSONType, nullable=False)
    close_le: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    close_par_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    classe = relationship("Classe", lazy="selectin")
    session = relationship("SessionAcademique", lazy="selectin")
    decisions = relationship(
        "DeliberationDecision",
        back_populates="deliberation",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # Un jury ne se tient pas deux fois pour la meme promotion et session.
        Index("uq_deliberations_promotion", "classe_id", "session_id", unique=True),
    )

    @property
    def close(self) -> bool:
        return self.statut == "close"

    def __repr__(self) -> str:
        return (
            f"<Deliberation classe={self.classe_id} session={self.session_id} "
            f"date={self.date_deliberation} statut={self.statut}>"
        )


class DeliberationDecision(Base):
    """Decision du jury pour un etudiant, et la proposition qui l'a inspiree."""

    __tablename__ = "deliberation_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    deliberation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("deliberations.id", ondelete="CASCADE"),
        nullable=False,
    )
    etudiant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("etudiants.id", ondelete="CASCADE"), nullable=False
    )

    # Ce que le moteur propose...
    proposition_statut: Mapped[str] = mapped_column(String(30), nullable=False)
    proposition_mention: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # ...et ce que le jury a decide.
    statut: Mapped[str] = mapped_column(String(30), nullable=False)
    mention: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    #: Motif obligatoire des que la decision s'ecarte de la proposition.
    motif_ecart: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Elements de calcul conserves : le PV et l'attestation s'appuient dessus,
    # pas sur un recalcul ulterieur qui pourrait differer.
    moyenne_generale: Mapped[float] = mapped_column(Float, nullable=False)
    ects_acquis: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ects_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    moyennes_ue: Mapped[Dict[str, Any]] = mapped_column(
        "moyennes_ue", JSONType, nullable=False, default=dict
    )
    notes_eliminatoires: Mapped[List[Any]] = mapped_column(
        "notes_eliminatoires", JSONType, nullable=False, default=list
    )
    decide_le: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    decide_par_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    deliberation = relationship("Deliberation", back_populates="decisions")
    etudiant = relationship("Etudiant", lazy="selectin")

    __table_args__ = (
        Index(
            "uq_deliberation_decisions_etudiant",
            "deliberation_id",
            "etudiant_id",
            unique=True,
        ),
        Index("ix_deliberation_decisions_etudiant", "etudiant_id"),
    )

    @property
    def ecart_proposition(self) -> bool:
        """Le jury s'est-il ecarte de la proposition du moteur ?"""

        return (
            self.statut != self.proposition_statut
            or (self.mention or "") != (self.proposition_mention or "")
        )

    @property
    def admis(self) -> bool:
        return self.statut == "Admis"

    def __repr__(self) -> str:
        return (
            f"<DeliberationDecision etudiant={self.etudiant_id} "
            f"statut={self.statut} mention={self.mention}>"
        )


__all__ = [
    "Deliberation",
    "DeliberationDecision",
    "ReglesDeliberation",
    "MENTIONS_PAR_STATUT",
    "STATUTS",
]
