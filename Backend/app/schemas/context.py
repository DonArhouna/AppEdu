"""Schémas du contexte global d'année académique."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.session import SessionAcademiqueResponse


def validate_academic_year(value: str) -> str:
    value = value.strip()
    parts = value.split("-")
    if len(parts) != 2 or not all(part.isdigit() and len(part) == 4 for part in parts):
        raise ValueError("L'année académique doit être au format AAAA-AAAA.")
    if int(parts[1]) != int(parts[0]) + 1:
        raise ValueError("L'année académique doit couvrir deux années consécutives.")
    return value


class AcademicContextUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    annee_academique: str = Field(..., description="Année au format AAAA-AAAA")
    session_id: Optional[str] = Field(None, max_length=50)

    @field_validator("annee_academique")
    @classmethod
    def check_year(cls, value: str) -> str:
        return validate_academic_year(value)


class AcademicContextResponse(BaseModel):
    annee_academique: str
    session_id: Optional[str] = None
    session: Optional[SessionAcademiqueResponse] = None
    configuree: bool
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
