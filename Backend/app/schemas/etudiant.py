"""Schémas Pydantic V2 pour les étudiants.

Les champs texte historiques restent exposes.  ``classe_id`` et
``session_id`` ajoutent le chemin canonique Classe + Session sans supprimer ni
réécrire les anciennes colonnes.
"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, ConfigDict, Field

from app.schemas.academic import ClasseResponse, InscriptionSummary


class EtudiantBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nom: str = Field(..., example="Dupont")
    prenom: str = Field(..., example="Marie")
    sexe: Optional[str] = None
    email: Optional[EmailStr] = Field(None, example="marie.dupont@email.com")
    telephone: Optional[str] = Field(None, example="+225 07 00 00 00")
    date_naissance: Optional[date] = None
    adresse: Optional[str] = None

    # Colonnes legacy/projection.  Elles sont optionnelles dans les schemas
    # d'entree afin d'accepter Classe + Session; l'endpoint les derives alors
    # des objets normalises avant l'ecriture.
    filiere: Optional[str] = Field(None, example="Génie Logiciel")
    filiere_id: Optional[str] = None
    niveau: Optional[str] = Field(None, example="L1")
    classe_id: Optional[str] = None
    statut: str = "Inscrit"
    photo_url: Optional[str] = None
    date_inscription: Optional[date] = None
    session_id: Optional[str] = None


class EtudiantCreate(EtudiantBase):
    matricule: Optional[str] = Field(None, example="2026-GL-0042")


class EtudiantUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nom: Optional[str] = None
    prenom: Optional[str] = None
    sexe: Optional[str] = None
    email: Optional[EmailStr] = None
    telephone: Optional[str] = None
    date_naissance: Optional[date] = None
    adresse: Optional[str] = None
    filiere: Optional[str] = None
    filiere_id: Optional[str] = None
    niveau: Optional[str] = None
    classe_id: Optional[str] = Field(None, min_length=1, max_length=50)
    statut: Optional[str] = None
    photo_url: Optional[str] = None
    session_id: Optional[str] = None


class EtudiantInscriptionRequest(BaseModel):
    """Chemin canonique recommended : ``classe_id`` + ``session_id``.

    Les champs texte restent acceptes pour le chemin legacy, mais un
    ``classe_id`` sans session est refuse : on ne fabrique pas une inscription
    historique sans session.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    session_id: Optional[str] = None
    classe_id: Optional[str] = Field(None, min_length=1, max_length=50)
    filiere_id: Optional[str] = None
    filiere: Optional[str] = None
    niveau: Optional[str] = None


class EtudiantSummaryResponse(BaseModel):
    """Projection minimale sans données personnelles détaillées."""

    id: str
    matricule: str
    nom: str
    prenom: str
    filiere: Optional[str] = None
    filiere_id: Optional[str] = None
    niveau: Optional[str] = None
    classe_id: Optional[str] = None
    classe: Optional[ClasseResponse] = None
    statut: str
    session_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EtudiantResponse(EtudiantBase):
    id: str
    matricule: str
    classe: Optional[ClasseResponse] = None
    inscriptions: List[InscriptionSummary] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "EtudiantBase",
    "EtudiantCreate",
    "EtudiantUpdate",
    "EtudiantInscriptionRequest",
    "EtudiantSummaryResponse",
    "EtudiantResponse",
]
