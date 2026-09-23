"""
Schémas Pydantic V2 pour la Structure Académique :
- Campus
- Departement
- Filiere
- UniteEnseignement (UE)
- Matiere (ECUE)
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Matière (ECUE)
# ---------------------------------------------------------------------------
class MatiereBase(BaseModel):
    nom: str = Field(..., example="Base de données relationnelles")
    code: str = Field(..., example="INF201")
    credits: int = Field(3, example=3)
    coefficient: float = Field(1.5, example=1.5)
    heures_cm: int = Field(20, example=20)
    heures_td: int = Field(15, example=15)
    heures_tp: int = Field(10, example=10)
    enseignant_nom: Optional[str] = Field(None, example="Dr. Diallo")
    description: Optional[str] = None


class MatiereCreate(MatiereBase):
    id: Optional[str] = None
    ue_id: Optional[str] = None


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
    credits: int = Field(6, example=6)
    coefficient: float = Field(3.0, example=3.0)
    heures: int = Field(45, example=45)
    semestre: str = Field("S1", example="S1")
    niveau: str = Field("Licence 3", example="Licence 3")
    responsable: Optional[str] = Field(None, example="Prof. Koné")


class UECreate(UEBase):
    id: Optional[str] = None
    filiere_id: Optional[str] = None
    matieres: Optional[List[MatiereCreate]] = None


class UEUpdate(BaseModel):
    nom: Optional[str] = None
    code: Optional[str] = None
    credits: Optional[int] = None
    coefficient: Optional[float] = None
    heures: Optional[int] = None
    semestre: Optional[str] = None
    niveau: Optional[str] = None
    responsable: Optional[str] = None
    filiere_id: Optional[str] = None


class UEResponse(UEBase):
    id: str
    filiere_id: Optional[str] = None
    matieres: List[MatiereResponse] = []
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
    diplome: str = Field("Licence", example="Licence")
    duree: int = Field(3, example=3)


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
    filieres: List[FiliereResponse] = []
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
    departements: List[DepartementResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
