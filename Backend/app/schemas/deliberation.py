"""Schemas de la deliberation : regles, seance de jury, decisions."""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

#: Les statuts d'une decision. Meme vocabulaire que le service : ces
#: libelles sont les valeurs possibles d'une decision, pas un reglement.
STATUTS = ("Admis", "Rattrapage", "Ajourné")


# ---------------------------------------------------------------------------
# Regles de deliberation
# ---------------------------------------------------------------------------
class MentionBareme(BaseModel):
    """Une mention et la moyenne minimale pour l'obtenir."""

    libelle: str = Field(..., min_length=1, max_length=50)
    seuil_min: float = Field(..., ge=0, le=20)

    @field_validator("libelle")
    @classmethod
    def _non_vide(cls, valeur: str) -> str:
        nettoye = valeur.strip()
        if not nettoye:
            raise ValueError("Le libelle de la mention ne peut pas etre vide.")
        return nettoye


class ReglesDeliberationOut(BaseModel):
    """Regles en vigueur, avec leur etat de confirmation."""

    model_config = ConfigDict(from_attributes=True)

    seuil_validation_moyenne: float
    seuil_eliminatoire: float
    seuil_rattrapage_minimale: float
    seuil_passage_conditionnel_ects: int
    compensation_autorisee: bool
    bareme_mentions: List[MentionBareme]
    #: ``False`` = valeurs de depart issues du moteur, jamais revues par
    #: l'institut. Une deliberation ne devrait pas s'appuyer dessus.
    confirmee: bool = False
    confirme_par: Optional[str] = None
    confirme_le: Optional[datetime] = None


class ReglesDeliberationMaj(BaseModel):
    """Modification du reglement, avec validation explicite."""

    seuil_validation_moyenne: float = Field(..., ge=0, le=20)
    seuil_eliminatoire: float = Field(..., ge=0, le=20)
    seuil_rattrapage_minimale: float = Field(..., ge=0, le=20)
    seuil_passage_conditionnel_ects: int = Field(..., ge=0)
    compensation_autorisee: bool
    bareme_mentions: List[MentionBareme] = Field(..., min_length=1)
    #: L'institut valide explicitement son reglement. Sans cette case, les
    #: valeurs restent « a confirmer » et l'ecran le signale.
    confirme: bool = Field(
        False, description="L'institut declare valider ce reglement."
    )

    @field_validator("seuil_rattrapage_minimale")
    @classmethod
    def _rattrapage_sous_validation(cls, valeur: float, info) -> float:
        # Un seuil de rattrapage superieur au seuil de validation rendrait la
        # zone « admis » vide : c'est presque toujours une saisie erronee.
        validation = info.data.get("seuil_validation_moyenne")
        if validation is not None and valeur > validation:
            raise ValueError(
                "Le seuil de rattrapage ne peut pas depasser le seuil de "
                "validation : sinon aucun etudiant ne pourrait etre admis."
            )
        return valeur

    @field_validator("bareme_mentions")
    @classmethod
    def _seuils_decroissants(cls, valeur: List[MentionBareme]) -> List[MentionBareme]:
        seuils = [entree.seuil_min for entree in valeur]
        if len(set(seuils)) != len(seuils):
            raise ValueError("Deux mentions partagent le meme seuil de moyenne.")
        libelles = [entree.libelle.lower() for entree in valeur]
        if len(set(libelles)) != len(libelles):
            raise ValueError("Le bareme contient deux mentions de meme nom.")
        return valeur


# ---------------------------------------------------------------------------
# Seance de jury
# ---------------------------------------------------------------------------
class MembreJury(BaseModel):
    """Un membre du jury. Ni le nom ni la qualite ne sont devines."""

    nom: str = Field(..., min_length=2, max_length=150)
    qualite: Optional[str] = Field(None, max_length=100)

    @field_validator("nom")
    @classmethod
    def _nom_retenu(cls, valeur: str) -> str:
        return valeur.strip()


class DeliberationCreation(BaseModel):
    """Ouverture d'une seance de jury."""

    classe_id: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    date_deliberation: date
    president: str = Field(..., min_length=2, max_length=150)
    membres: List[MembreJury] = Field(..., min_length=1)
    lieu: Optional[str] = Field(None, max_length=255)

    @field_validator("president")
    @classmethod
    def _president_retenu(cls, valeur: str) -> str:
        nettoye = valeur.strip()
        if len(nettoye) < 2:
            raise ValueError("Le president de jury doit etre nomme.")
        return nettoye


class PropositionEtudiant(BaseModel):
    """Ce que le moteur propose. Ce n'est pas une decision."""

    etudiant_id: str
    matricule: str
    nom: str
    prenom: str
    filiere: Optional[str] = None
    moyenne_generale: float
    ects_acquis: int
    ects_total: int
    proposition_statut: str
    proposition_mention: Optional[str] = None
    moyennes_ue: Dict[str, Any] = Field(default_factory=dict)
    notes_eliminatoires: List[Any] = Field(default_factory=list)
    matieres_hors_ue: List[Any] = Field(default_factory=list)
    avertissements: List[str] = Field(default_factory=list)
    #: Ce que le jury a reellement decide, si la seance est en cours.
    decision_statut: Optional[str] = None
    decision_mention: Optional[str] = None
    motif_ecart: Optional[str] = None
    ecart: bool = False


class DecisionOut(BaseModel):
    """Une decision enregistree, avec la proposition qui l'a inspiree."""

    model_config = ConfigDict(from_attributes=True)

    etudiant_id: str
    matricule: Optional[str] = None
    nom: Optional[str] = None
    prenom: Optional[str] = None
    proposition_statut: str
    proposition_mention: Optional[str] = None
    statut: str
    mention: Optional[str] = None
    motif_ecart: Optional[str] = None
    ecart: bool = False
    moyenne_generale: float
    ects_acquis: int
    ects_total: int
    moyennes_ue: Dict[str, Any] = Field(default_factory=dict)
    notes_eliminatoires: List[Any] = Field(default_factory=list)
    decide_le: Optional[datetime] = None


class DeliberationOut(BaseModel):
    """Une seance de jury et son etat."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    classe_id: str
    classe_nom: Optional[str] = None
    session_id: str
    session_nom: Optional[str] = None
    date_deliberation: date
    lieu: Optional[str] = None
    president: str
    membres: List[Dict[str, Any]] = Field(default_factory=list)
    statut: str
    regles: Dict[str, Any] = Field(default_factory=dict)
    close_le: Optional[datetime] = None
    created_at: Optional[datetime] = None
    nb_inscrits: int = 0
    nb_decisions: int = 0


class DeliberationDetail(DeliberationOut):
    """Seance complete : regles figees, propositions et decisions."""

    propositions: List[PropositionEtudiant] = Field(default_factory=list)
    decisions: List[DecisionOut] = Field(default_factory=list)
    avertissements: List[str] = Field(default_factory=list)


class DecisionPrise(BaseModel):
    """Decision du jury pour un etudiant."""

    statut: str = Field(..., description="Admis, Rattrapage ou Ajourné.")
    mention: Optional[str] = None
    motif_ecart: Optional[str] = Field(
        None,
        description=(
            "Obligatoire des que la decision s'ecarte de la proposition du "
            "moteur : sans motif, le verdict serait inexplicable."
        ),
    )

    @field_validator("statut")
    @classmethod
    def _statut_connu(cls, valeur: str) -> str:
        retenu = valeur.strip()
        if retenu not in STATUTS:
            raise ValueError(
                f"Statut inconnu : « {retenu} ». Valeurs acceptees : "
                f"{', '.join(STATUTS)}."
            )
        return retenu


class DeliberationCloture(BaseModel):
    """Arret du verdict d'une seance."""

    confirmation: str = Field(
        ..., description="Doit valoir « arreter » : une cloture est irreversible."
    )


__all__ = [
    "DecisionOut",
    "DecisionPrise",
    "DeliberationCloture",
    "DeliberationCreation",
    "DeliberationDetail",
    "DeliberationOut",
    "MentionBareme",
    "MembreJury",
    "PropositionEtudiant",
    "ReglesDeliberationMaj",
    "ReglesDeliberationOut",
    "STATUTS",
]
