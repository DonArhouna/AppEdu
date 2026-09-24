"""
Schémas Pydantic V2 pour le Setup Wizard.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from app.schemas.user import UserResponse


class EtablissementSetupInput(BaseModel):
    nom: str = Field(..., min_length=2)
    code: str = Field(..., min_length=2, max_length=50)
    adresse: Optional[str] = None
    telephone: Optional[str] = None
    email: EmailStr
    site_web: Optional[str] = None
    devise: str = Field(..., min_length=3, max_length=10)
    license_key: Optional[str] = None


class AdminSetupInput(BaseModel):
    nom: str = Field(..., min_length=2)
    prenom: str = Field(..., min_length=2)
    email: EmailStr
    password: str = Field(..., min_length=8)
    telephone: Optional[str] = None


class DatabaseSetupInput(BaseModel):
    host: Optional[str] = "localhost"
    port: Optional[int] = 5432
    user: Optional[str] = "postgres"
    password: Optional[str] = "postgres"
    database: Optional[str] = "edumanagepro"


class SetupStatusResponse(BaseModel):
    is_configured: bool
    etablissement_nom: Optional[str] = None
    etablissement_code: Optional[str] = None
    devise: Optional[str] = None
    version: str = "1.0.0"
    tenant_mode: str = "standalone"
    database_connected: bool = False
    details: Optional[str] = None


class SetupInitRequest(BaseModel):
    etablissement: EtablissementSetupInput
    admin: AdminSetupInput
    database: Optional[DatabaseSetupInput] = None


class SetupInitResponse(BaseModel):
    success: bool
    message: str
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
