"""
Schémas Pydantic V2 pour les Étudiants.
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict, Field


class EtudiantBase(BaseModel):
    nom: str = Field(..., example="Dupont")
    prenom: str = Field(..., example="Marie")
    sexe: Optional[str] = None
    email: Optional[EmailStr] = Field(None, example="marie.dupont@email.com")
    telephone: Optional[str] = Field(None, example="+225 07 00 00 00")
    date_naissance: Optional[date] = None
    adresse: Optional[str] = None
    filiere: str = Field(..., example="Génie Logiciel")
    filiere_id: Optional[str] = None
    niveau: str = Field(..., example="Licence 3")
    statut: str
    photo_url: Optional[str] = None
    date_inscription: Optional[date] = None
    session_id: Optional[str] = None


class EtudiantCreate(BaseModel):
    matricule: Optional[str] = Field(None, example="2026-GL-0042")
    nom: str = Field(..., example="Dupont")
    prenom: str = Field(..., example="Marie")
    sexe: Optional[str] = None
    email: Optional[EmailStr] = Field(None, example="marie.dupont@email.com")
    telephone: Optional[str] = Field(None, example="+225 07 00 00 00")
    date_naissance: Optional[date] = None
    adresse: Optional[str] = None
    filiere: str = Field(..., example="Génie Logiciel")
    filiere_id: Optional[str] = None
    niveau: str = Field(..., example="Licence 3")
    statut: str
    photo_url: Optional[str] = None
    date_inscription: Optional[date] = None
    session_id: Optional[str] = None


class EtudiantUpdate(BaseModel):
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
    statut: Optional[str] = None
    photo_url: Optional[str] = None
    session_id: Optional[str] = None


class EtudiantInscriptionRequest(BaseModel):
    session_id: str
    filiere_id: Optional[str] = None
    filiere: Optional[str] = None
    niveau: Optional[str] = None


class EtudiantResponse(EtudiantBase):
    id: str
    matricule: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
