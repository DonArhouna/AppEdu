"""Schemas des relances de facturation."""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CreanceEtudiant(BaseModel):
    """Une facture echue non soldee, telle qu'elle est au moment de la lecture."""

    facture_id: str
    numero: str
    date_echeance: date
    description: Optional[str] = None
    montant_total: float
    montant_regle: float
    reste: float
    retard_jours: int


class RelanceAnterieure(BaseModel):
    """La derniere relance connue, pour eviter de relancer deux fois de suite."""

    model_config = ConfigDict(from_attributes=True)

    niveau: int
    date_relance: date
    moyen: str
    montant_reclame: float


class ARelancer(BaseModel):
    """Un etudiant dont la dette merite un suivi."""

    etudiant_id: str
    matricule: str
    nom: str
    prenom: str
    filiere: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    creances: List[CreanceEtudiant] = Field(default_factory=list)
    nb_creances: int
    total_du: float
    #: Retard de la plus ancienne echeance.
    retard_jours: int
    anciennete_jours: int
    #: Numero de la prochaine relance si elle est faite aujourd'hui.
    niveau_suivant: int
    nb_relances: int
    derniere_relance: Optional[RelanceAnterieure] = None
    jours_depuis_derniere: Optional[int] = None


class SyntheseRelances(BaseModel):
    """Vue d'ensemble des creances a suivre."""

    date_calcul: date
    devise: str = ""
    nb_etudiants: int
    nb_creances: int
    total_du: float
    # Paliers repris de la balance agee, pour que les deux vues concordent.
    retard_1_30: float
    retard_31_60: float
    retard_plus_60: float
    items: List[ARelancer] = Field(default_factory=list)


class RelanceCreation(BaseModel):
    """Constat d'une relance faite par le secretariat."""

    etudiant_id: str = Field(..., min_length=1)
    moyen: str = Field(..., min_length=2, max_length=30)
    date_relance: Optional[date] = Field(
        None,
        description="Date de la relance. Par defaut, aujourd'hui : c'est le cas le plus fréquent.",
    )
    session_id: Optional[str] = None
    message: Optional[str] = Field(None, max_length=2000)

    @field_validator("message")
    @classmethod
    def _message_propre(cls, valeur: Optional[str]) -> Optional[str]:
        if valeur is None:
            return None
        nettoye = valeur.strip()
        return nettoye or None


class RelanceOut(BaseModel):
    """Une relance enregistree, avec l'instantane de ce qui etait reclame."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    etudiant_id: str
    matricule: Optional[str] = None
    nom: Optional[str] = None
    prenom: Optional[str] = None
    session_id: Optional[str] = None
    niveau: int
    date_relance: date
    moyen: str
    montant_reclame: float
    retard_jours: int
    message: Optional[str] = None
    solde_apres: Optional[float] = None
    relance_par_email: Optional[str] = None
    created_at: Optional[datetime] = None
    nb_factures: int = 0
    factures_concernees: List[Dict[str, Any]] = Field(default_factory=list)
    #: Un encaissement a-t-il suivi la relance ?
    resolue: bool = False


class RelanceEnregistree(BaseModel):
    """Reponse a une relance : ce qui a ete consigne, et son effet."""

    relance: RelanceOut
    #: Niveau atteint, montant reclame, anciennete constatee.
    resume: Dict[str, Any] = Field(default_factory=dict)


class SoldeSuivi(BaseModel):
    """Constat du solde apres une relance."""

    etudiant_id: str
    niveau: int
    solde_apres: float
    nb_relances_concernees: int


__all__ = [
    "ARelancer",
    "CreanceEtudiant",
    "RelanceAnterieure",
    "RelanceCreation",
    "RelanceEnregistree",
    "RelanceOut",
    "SoldeSuivi",
    "SyntheseRelances",
]
