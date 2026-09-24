"""Schémas Pydantic du workflow d'admissions."""

from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.etudiant import EtudiantResponse
from app.schemas.session import SessionAcademiqueResponse
from app.schemas.structure import FiliereResponse


class StatutCandidature(str, Enum):
    NOUVELLE = "nouvelle"
    EN_VERIFICATION = "en_verification"
    COMPLETE = "complete"
    ACCEPTEE = "acceptee"
    REFUSEE = "refusee"
    LISTE_ATTENTE = "liste_attente"
    CONVERTI = "converti"
    ANNULEE = "annulee"


class StatutPiece(str, Enum):
    REQUISE = "requise"
    RECUE = "recue"
    VALIDEE = "validee"
    REJETEE = "rejetee"


class TypeDecision(str, Enum):
    ACCEPTEE = "acceptee"
    REFUSEE = "refusee"
    LISTE_ATTENTE = "liste_attente"


class CandidatureBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nom: str = Field(..., min_length=1, max_length=100)
    prenom: str = Field(..., min_length=1, max_length=100)
    sexe: Optional[str] = Field(None, max_length=10)
    date_naissance: Optional[date] = None
    email: EmailStr
    telephone: Optional[str] = Field(None, max_length=50)
    adresse: Optional[str] = Field(None, max_length=500)
    filiere_id: str = Field(..., min_length=1, max_length=50)
    niveau: str = Field(..., min_length=1, max_length=50)
    session_id: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
    source: Optional[str] = Field(None, max_length=100)


class CandidatureCreate(CandidatureBase):
    date_demande: Optional[date] = None


class CandidatureUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nom: Optional[str] = Field(None, min_length=1, max_length=100)
    prenom: Optional[str] = Field(None, min_length=1, max_length=100)
    sexe: Optional[str] = Field(None, max_length=10)
    date_naissance: Optional[date] = None
    email: Optional[EmailStr] = None
    telephone: Optional[str] = Field(None, max_length=50)
    adresse: Optional[str] = Field(None, max_length=500)
    filiere_id: Optional[str] = Field(None, min_length=1, max_length=50)
    niveau: Optional[str] = Field(None, min_length=1, max_length=50)
    session_id: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
    source: Optional[str] = Field(None, max_length=100)


class PieceCandidatureCreate(BaseModel):
    type: str = Field(..., min_length=2, max_length=100)
    nom_fichier: Optional[str] = Field(None, max_length=255)
    commentaire: Optional[str] = None


class PieceCandidatureUpdate(BaseModel):
    nom_fichier: Optional[str] = Field(None, max_length=255)
    statut: Optional[StatutPiece] = None
    commentaire: Optional[str] = None


class PieceCandidatureResponse(BaseModel):
    id: str
    candidature_id: str
    type: str
    nom_fichier: Optional[str] = None
    fichier_disponible: bool = False
    statut: StatutPiece
    date_depot: Optional[datetime] = None
    commentaire: Optional[str] = None
    valide_par_id: Optional[int] = None
    date_validation: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DecisionAdmissionCreate(BaseModel):
    decision: TypeDecision
    motif: Optional[str] = None


class DecisionAdmissionResponse(BaseModel):
    id: str
    candidature_id: str
    decision: TypeDecision
    motif: Optional[str] = None
    decisionnaire_id: int
    date_decision: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CandidatureResponse(CandidatureBase):
    id: str
    reference: str
    statut: StatutCandidature
    date_demande: date
    created_by_id: Optional[int] = None
    etudiant_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    filiere: Optional[FiliereResponse] = None
    session: Optional[SessionAcademiqueResponse] = None
    pieces: List[PieceCandidatureResponse] = Field(default_factory=list)
    decisions: List[DecisionAdmissionResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class VueAdmissionsFiltres(BaseModel):
    search: Optional[str] = Field(None, max_length=120)
    statut: Optional[StatutCandidature] = None
    filiere_id: Optional[str] = Field(None, max_length=50)
    session_id: Optional[str] = Field(None, max_length=50)

    model_config = ConfigDict(str_strip_whitespace=True)


class VueAdmissionsCreate(BaseModel):
    nom: str = Field(..., min_length=1, max_length=100)
    filtres: VueAdmissionsFiltres = Field(default_factory=VueAdmissionsFiltres)

    model_config = ConfigDict(str_strip_whitespace=True)


class VueAdmissionsUpdate(BaseModel):
    nom: Optional[str] = Field(None, min_length=1, max_length=100)
    filtres: Optional[VueAdmissionsFiltres] = None

    model_config = ConfigDict(str_strip_whitespace=True)


class VueAdmissionsResponse(BaseModel):
    id: str
    nom: str
    filtres: VueAdmissionsFiltres
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActionGroupee(str, Enum):
    METTRE_EN_VERIFICATION = "mettre_en_verification"
    MARQUER_COMPLETE = "marquer_complete"
    ANNULER = "annuler"


class BulkCandidatureAction(BaseModel):
    ids: List[str] = Field(..., min_length=1, max_length=100)
    action: ActionGroupee
    commentaire: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(str_strip_whitespace=True)


class BulkActionError(BaseModel):
    candidature_id: str
    message: str


class BulkCandidatureActionResponse(BaseModel):
    updated_ids: List[str] = Field(default_factory=list)
    errors: List[BulkActionError] = Field(default_factory=list)


class CandidaturePage(BaseModel):
    items: List[CandidatureResponse]
    total: int
    page: int
    page_size: int
    pages: int
    counts: dict[str, int] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class CandidatureStatusUpdate(BaseModel):
    statut: StatutCandidature
    commentaire: Optional[str] = None


class CandidatureConversionResponse(BaseModel):
    candidature: CandidatureResponse
    etudiant: EtudiantResponse
