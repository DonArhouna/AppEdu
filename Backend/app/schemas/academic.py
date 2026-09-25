"""Schémas Pydantic du socle académique normalisé."""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.session import SessionAcademiqueResponse


class _AcademicNameMixin(BaseModel):
    """Accepte ``nom`` et ``libelle`` sans créer deux colonnes concurrentes."""

    model_config = ConfigDict(str_strip_whitespace=True, populate_by_name=True)

    nom: Optional[str] = Field(None, min_length=1, max_length=150)
    libelle: Optional[str] = Field(None, min_length=1, max_length=150)

    @model_validator(mode="after")
    def _synchronize_name(self):
        if self.nom is None:
            self.nom = self.libelle
        if self.libelle is None:
            self.libelle = self.nom
        if not self.nom:
            raise ValueError("Le nom du référentiel est obligatoire.")
        return self


class CycleBase(_AcademicNameMixin):
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    ordre: int = Field(default=0, ge=0)
    actif: bool = True


class CycleCreate(CycleBase):
    id: Optional[str] = None


class CycleUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    code: Optional[str] = Field(None, min_length=1, max_length=50)
    nom: Optional[str] = Field(None, min_length=1, max_length=150)
    libelle: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None
    ordre: Optional[int] = Field(None, ge=0)
    actif: Optional[bool] = None


class CycleSummary(BaseModel):
    id: str
    code: str
    nom: str
    libelle: Optional[str] = None
    ordre: int = 0
    actif: bool = True

    model_config = ConfigDict(from_attributes=True)


class CycleResponse(CycleBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NiveauBase(_AcademicNameMixin):
    code: str = Field(..., min_length=1, max_length=20)
    cycle_id: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    ordre: int = Field(default=0, ge=0)
    actif: bool = True


class NiveauCreate(NiveauBase):
    id: Optional[str] = None


class NiveauUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    code: Optional[str] = Field(None, min_length=1, max_length=20)
    nom: Optional[str] = Field(None, min_length=1, max_length=150)
    libelle: Optional[str] = Field(None, min_length=1, max_length=150)
    cycle_id: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    ordre: Optional[int] = Field(None, ge=0)
    actif: Optional[bool] = None


class NiveauSummary(BaseModel):
    id: str
    code: str
    nom: str
    libelle: Optional[str] = None
    cycle_id: str
    cycle: Optional[CycleSummary] = None
    ordre: int = 0
    actif: bool = True

    model_config = ConfigDict(from_attributes=True)


class NiveauResponse(NiveauBase):
    id: str
    cycle: Optional[CycleSummary] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FiliereSummary(BaseModel):
    """Projection de la filiere exposee dans une classe."""

    id: str
    code: str
    nom: str
    departement_id: Optional[str] = None
    diplome: Optional[str] = None
    duree: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ClasseBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nom: Optional[str] = Field(None, max_length=150)
    actif: bool = True


class ClasseCreate(ClasseBase):
    id: Optional[str] = None
    filiere_id: str = Field(..., min_length=1, max_length=50)
    niveau_id: str = Field(..., min_length=1, max_length=50)


class ClasseUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    filiere_id: Optional[str] = Field(None, min_length=1, max_length=50)
    niveau_id: Optional[str] = Field(None, min_length=1, max_length=50)
    nom: Optional[str] = Field(None, max_length=150)
    actif: Optional[bool] = None


class ClasseResponse(ClasseBase):
    id: str
    filiere_id: str
    niveau_id: str
    cycle_id: Optional[str] = None
    filiere: Optional[FiliereSummary] = None
    niveau: Optional[NiveauSummary] = None
    cycle: Optional[CycleSummary] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EtudiantInscriptionSummary(BaseModel):
    id: str
    matricule: str
    nom: str
    prenom: str

    model_config = ConfigDict(from_attributes=True)


class InscriptionSummary(BaseModel):
    id: str
    etudiant_id: str
    classe_id: str
    session_id: str
    statut: str
    actif: bool = False
    date_inscription: date
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InscriptionBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    etudiant_id: str = Field(..., min_length=1, max_length=50)
    classe_id: str = Field(..., min_length=1, max_length=50)
    session_id: str = Field(..., min_length=1, max_length=50)
    statut: str = Field(default="active", min_length=1, max_length=30)
    date_inscription: Optional[date] = None


class InscriptionCreate(InscriptionBase):
    id: Optional[str] = None
    actif: Optional[bool] = None


class InscriptionUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    classe_id: Optional[str] = Field(None, min_length=1, max_length=50)
    statut: Optional[str] = Field(None, min_length=1, max_length=30)
    date_inscription: Optional[date] = None


class InscriptionResponse(InscriptionBase):
    id: str
    actif: bool = True
    etudiant: Optional[EtudiantInscriptionSummary] = None
    classe: Optional[ClasseResponse] = None
    session: Optional[SessionAcademiqueResponse] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModeleLMDChargeRequest(BaseModel):
    """Parametres volontairement optionnels : l'action HTTP est la confirmation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    confirmer: bool = True


class ModeleLMDChargeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cycles: List[CycleResponse] = Field(default_factory=list)
    niveaux: List[NiveauResponse] = Field(default_factory=list)
    cycles_crees: int = 0
    niveaux_crees: int = 0
    total_cycles: int = 0
    total_niveaux: int = 0
    created: bool = False
    idempotent: bool = True


# Alias de lecture frequent dans les contrats APIheterogenes.
FiliereResume = FiliereSummary
NiveauResume = NiveauSummary
CycleResume = CycleSummary


__all__ = [
    "CycleBase",
    "CycleCreate",
    "CycleUpdate",
    "CycleSummary",
    "CycleResponse",
    "NiveauBase",
    "NiveauCreate",
    "NiveauUpdate",
    "NiveauSummary",
    "NiveauResponse",
    "FiliereSummary",
    "FiliereResume",
    "NiveauResume",
    "CycleResume",
    "ClasseBase",
    "ClasseCreate",
    "ClasseUpdate",
    "ClasseResponse",
    "EtudiantInscriptionSummary",
    "InscriptionSummary",
    "InscriptionBase",
    "InscriptionCreate",
    "InscriptionUpdate",
    "InscriptionResponse",
    "ModeleLMDChargeRequest",
    "ModeleLMDChargeResponse",
]
