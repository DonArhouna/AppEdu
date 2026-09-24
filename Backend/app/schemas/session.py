"""
Schémas Pydantic V2 pour les Sessions Académiques et Périodes de Paiement.
"""

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Période de Paiement
# ---------------------------------------------------------------------------
class PeriodePaiementBase(BaseModel):
    nom: str = Field(..., example="Tranche 1 - Octobre")
    mois: str = Field(..., example="Octobre")
    date_echeance: Optional[date] = None
    montant_estime: Optional[float] = None
    pourcentage: Optional[float] = None
    ordre: int


class PeriodePaiementCreate(PeriodePaiementBase):
    id: Optional[str] = None


class PeriodePaiementResponse(PeriodePaiementBase):
    id: str
    session_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Session Académique
# ---------------------------------------------------------------------------
class SessionAcademiqueBase(BaseModel):
    nom: str
    code: str
    annee_academique: str
    date_debut: date
    date_fin: date
    statut: str
    description: Optional[str] = None


class SessionAcademiqueCreate(SessionAcademiqueBase):
    id: Optional[str] = None
    periodes: Optional[List[PeriodePaiementCreate]] = None


class SessionAcademiqueUpdate(BaseModel):
    nom: Optional[str] = None
    code: Optional[str] = None
    annee_academique: Optional[str] = None
    date_debut: Optional[date] = None
    date_fin: Optional[date] = None
    statut: Optional[str] = None
    description: Optional[str] = None
    periodes: Optional[List[PeriodePaiementCreate]] = None


class SessionAcademiqueResponse(SessionAcademiqueBase):
    id: str
    periodes: List[PeriodePaiementResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
