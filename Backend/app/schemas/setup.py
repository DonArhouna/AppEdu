"""
Schémas Pydantic V2 pour le Setup Wizard.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from app.schemas.user import UserResponse


class EtablissementSetupInput(BaseModel):
    nom: str = Field(..., example="Institut Africain de Management")
    code: str = Field(..., example="IAM-DK")
    adresse: Optional[str] = Field(None, example="Point E, Dakar, Sénégal")
    telephone: Optional[str] = Field(None, example="+221 33 869 36 36")
    email: Optional[EmailStr] = Field(None, example="contact@iam.sn")
    site_web: Optional[str] = Field(None, example="https://iam.sn")
    devise: str = Field("FCFA", example="FCFA")
    license_key: Optional[str] = Field(None, example="EMP-LIC-2026-IAMDK")


class AdminSetupInput(BaseModel):
    nom: str = Field(..., example="Directeur")
    prenom: str = Field(..., example="Admin")
    email: EmailStr = Field(..., example="admin@iam.sn")
    password: str = Field(..., min_length=6, example="Admin@2026!")
    telephone: Optional[str] = Field(None, example="+221 77 000 00 00")


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
    version: str = "1.0.0"
    tenant_mode: str = "standalone"
    database_connected: bool = False
    details: Optional[str] = None


class SetupInitRequest(BaseModel):
    etablissement: EtablissementSetupInput
    admin: AdminSetupInput
    database: Optional[DatabaseSetupInput] = None
    init_default_academic_session: bool = True


class SetupInitResponse(BaseModel):
    success: bool
    message: str
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
