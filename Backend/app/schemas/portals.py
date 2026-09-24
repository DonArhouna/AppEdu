"""Schémas des portails auto-service étudiant et enseignant.

Ces réponses sont volontairement dédiées aux portails : elles évitent qu'un
utilisateur puisse composer un dashboard en appelant les endpoints globaux du
personnel et garantissent que les données sont filtrées côté serveur.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.etudiant import EtudiantResponse
from app.schemas.finance import FactureResponse
from app.schemas.pedagogie import AbsenceResponse, CoursResponse, NoteResponse
from app.schemas.session import SessionAcademiqueResponse
from app.schemas.structure import MatiereResponse


class PortalEtudiantResponse(BaseModel):
    """Agrégat strictement limité au dossier étudiant authentifié."""

    etudiant: EtudiantResponse
    notes: List[NoteResponse] = Field(default_factory=list)
    absences: List[AbsenceResponse] = Field(default_factory=list)
    factures: List[FactureResponse] = Field(default_factory=list)
    cours: List[CoursResponse] = Field(default_factory=list)
    matieres: List[MatiereResponse] = Field(default_factory=list)
    sessions: List[SessionAcademiqueResponse] = Field(default_factory=list)
    devise: Optional[str] = None


class PortalEnseignantResponse(BaseModel):
    """Agrégat strictement limité aux cours du enseignant authentifié."""

    cours: List[CoursResponse] = Field(default_factory=list)
    matieres: List[MatiereResponse] = Field(default_factory=list)
    notes: List[NoteResponse] = Field(default_factory=list)
    etudiants: List[EtudiantResponse] = Field(default_factory=list)
