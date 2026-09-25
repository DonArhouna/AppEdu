"""
Schémas Pydantic V2 pour la Pédagogie :
- Cours / Emplois du temps
- Examens
- Notes & Saisie en lot
- Absences
- Délibération LMD / ECTS
"""

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.services.deliberation_engine import (
    DeliberationConfig,
    ECUEResult,
    UEResult,
    EtudiantDeliberationResult,
    PromotionDeliberationStats,
    PromotionDeliberationResult,
)


# ---------------------------------------------------------------------------
# Cours
# ---------------------------------------------------------------------------
class CoursBase(BaseModel):
    matiere_id: str
    enseignant_id: Optional[int] = None
    enseignant_nom: Optional[str] = None
    salle: str = Field(..., example="Amphi A")
    jour_semaine: str = Field(..., example="Lundi")
    heure_debut: str = Field(..., example="08:00")
    heure_fin: str = Field(..., example="10:00")
    type_cours: str


class CoursCreate(CoursBase):
    id: Optional[str] = None


class CoursUpdate(BaseModel):
    matiere_id: Optional[str] = None
    enseignant_id: Optional[int] = None
    enseignant_nom: Optional[str] = None
    salle: Optional[str] = None
    jour_semaine: Optional[str] = None
    heure_debut: Optional[str] = None
    heure_fin: Optional[str] = None
    type_cours: Optional[str] = None


class CoursResponse(CoursBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Examen
# ---------------------------------------------------------------------------
class ExamenBase(BaseModel):
    nom: str = Field(..., example="Examen Final Algorithmique")
    session_id: str
    matiere_id: str
    type_examen: str = Field("Examen Final", example="Examen Final")
    date_examen: date
    duree_minutes: int = Field(120, example=120)
    coefficient: float = Field(..., gt=0.0)


class ExamenCreate(ExamenBase):
    id: Optional[str] = None


class ExamenResponse(ExamenBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Note
# ---------------------------------------------------------------------------
class NoteBase(BaseModel):
    etudiant_id: str
    matiere_id: str
    examen_id: Optional[str] = None
    session_id: Optional[str] = None
    valeur: float = Field(..., ge=0.0, le=20.0, example=15.5)
    coefficient: float = Field(..., gt=0.0)
    appreciation: Optional[str] = None
    statut: str = Field("Validé", example="Validé")


class NoteCreate(NoteBase):
    id: Optional[str] = None


class NoteBulkItem(BaseModel):
    etudiant_id: str
    valeur: float = Field(..., ge=0.0, le=20.0)
    coefficient: float = Field(..., gt=0.0)
    appreciation: Optional[str] = None


class NoteBulkCreate(BaseModel):
    matiere_id: str
    examen_id: Optional[str] = None
    session_id: Optional[str] = None
    notes: List[NoteBulkItem]


class NoteUpdate(BaseModel):
    matiere_id: Optional[str] = None
    examen_id: Optional[str] = None
    session_id: Optional[str] = None
    valeur: Optional[float] = Field(None, ge=0.0, le=20.0)
    coefficient: Optional[float] = Field(None, gt=0.0)
    appreciation: Optional[str] = None
    statut: Optional[str] = None


class NoteResponse(NoteBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Absence
# ---------------------------------------------------------------------------
class AbsenceBase(BaseModel):
    etudiant_id: str
    cours_id: Optional[str] = None
    matiere_id: Optional[str] = None
    session_id: Optional[str] = None
    date_absence: date
    duree_heures: float = Field(..., gt=0.0)
    justifiee: bool
    motif: Optional[str] = None


class AbsenceCreate(AbsenceBase):
    id: Optional[str] = None


class AbsenceResponse(AbsenceBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Requêtes de Délibération
# ---------------------------------------------------------------------------
class DeliberationSingleRequest(BaseModel):
    etudiant: dict
    config: Optional[DeliberationConfig] = None


class DeliberationPromotionRequest(BaseModel):
    etudiants: List[dict]
    config: Optional[DeliberationConfig] = None
