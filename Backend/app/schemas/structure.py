"""
Schémas Pydantic V2 pour la Structure Académique :
- Campus
- Departement
- Filiere
- UniteEnseignement (UE)
- Matiere (ECUE)
"""

from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Matière (ECUE)
# ---------------------------------------------------------------------------
class MatiereBase(BaseModel):
    nom: str = Field(..., example="Base de données relationnelles")
    code: str = Field(..., example="INF201")
    credits: int = Field(..., ge=0)
    coefficient: float = Field(..., ge=0)
    heures_cm: int = Field(..., ge=0)
    heures_td: int = Field(..., ge=0)
    heures_tp: int = Field(..., ge=0)
    enseignant_nom: Optional[str] = Field(None, example="Dr. Diallo")
    description: Optional[str] = None


class MatiereCreate(MatiereBase):
    id: Optional[str] = None
    ue_id: str


class MatiereUpdate(BaseModel):
    nom: Optional[str] = None
    code: Optional[str] = None
    credits: Optional[int] = None
    coefficient: Optional[float] = None
    heures_cm: Optional[int] = None
    heures_td: Optional[int] = None
    heures_tp: Optional[int] = None
    enseignant_nom: Optional[str] = None
    description: Optional[str] = None
    ue_id: Optional[str] = None


class MatiereResponse(MatiereBase):
    id: str
    ue_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Unité d'Enseignement (UE)
# ---------------------------------------------------------------------------
class UEBase(BaseModel):
    nom: str = Field(..., example="Systèmes d'Information & Génie Logiciel")
    code: str = Field(..., example="UE-INF301")
    credits: int = Field(..., ge=0)
    coefficient: float = Field(..., ge=0)
    heures: int = Field(..., ge=0)
    semestre: Optional[str] = Field(None, example="S1")
    #: Rattachement structurel au semestre. Nullable : une UE creee avant la
    #: gestion des semestres n'a pas de semestre, et une UE hors programme n'en
    #: a pas toujours. Elle apparait alors sur aucun bulletin — c'est signale,
    #: pas masque.
    semestre_id: Optional[str] = None
    #: ``semestrielle`` (defaut) ou ``annuelle``.
    #:
    #: Une UE annuelle est evaluee **une fois pour l'annee** : elle n'entre
    #: dans aucune moyenne de semestre, et ne parait que du recapitulatif
    #: annuel. Nullable pour la compatibilite : une requete d'API anterieure a
    #: ce champ reste valide, et l'absence vaut « semestrielle ».
    regime: Optional[Literal["semestrielle", "annuelle"]] = None
    niveau: str
    responsable: Optional[str] = Field(None, example="Prof. Koné")


class UECreate(UEBase):
    id: Optional[str] = None
    filiere_id: str
    matieres: Optional[List[MatiereCreate]] = None


class UEUpdate(BaseModel):
    nom: Optional[str] = None
    code: Optional[str] = None
    credits: Optional[int] = None
    coefficient: Optional[float] = None
    heures: Optional[int] = None
    semestre: Optional[str] = None
    semestre_id: Optional[str] = None
    regime: Optional[Literal["semestrielle", "annuelle"]] = None
    niveau: Optional[str] = None
    responsable: Optional[str] = None
    filiere_id: Optional[str] = None


class UEResponse(UEBase):
    id: str
    filiere_id: Optional[str] = None
    matieres: List[MatiereResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Filière
# ---------------------------------------------------------------------------
class FiliereBase(BaseModel):
    nom: str = Field(..., example="Génie Logiciel")
    code: str = Field(..., example="GL")
    description: Optional[str] = None
    diplome: str
    duree: int = Field(..., ge=1)


class FiliereCreate(FiliereBase):
    id: Optional[str] = None
    departement_id: Optional[str] = None


class FiliereUpdate(BaseModel):
    nom: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    diplome: Optional[str] = None
    duree: Optional[int] = None
    departement_id: Optional[str] = None


class FiliereResponse(FiliereBase):
    id: str
    departement_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Département
# ---------------------------------------------------------------------------
class DepartementBase(BaseModel):
    nom: str = Field(..., example="Génie Informatique")
    code: str = Field(..., example="GI")
    description: Optional[str] = None
    responsable: Optional[str] = Field(None, example="Dr. Kouassi")


class DepartementCreate(DepartementBase):
    id: Optional[str] = None
    campus_id: Optional[str] = None


class DepartementUpdate(BaseModel):
    nom: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    responsable: Optional[str] = None
    campus_id: Optional[str] = None


class DepartementResponse(DepartementBase):
    id: str
    campus_id: Optional[str] = None
    filieres: List[FiliereResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Campus
# ---------------------------------------------------------------------------
class CampusBase(BaseModel):
    nom: str = Field(..., example="Campus Principal")
    code: str = Field(..., example="CAMP-PRI")
    description: Optional[str] = None
    adresse: Optional[str] = None
    ville: Optional[str] = Field(None, example="Abidjan")
    responsable: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None


class CampusCreate(CampusBase):
    id: Optional[str] = None


class CampusUpdate(BaseModel):
    nom: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    adresse: Optional[str] = None
    ville: Optional[str] = None
    responsable: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None


class CampusResponse(CampusBase):
    id: str
    departements: List[DepartementResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
