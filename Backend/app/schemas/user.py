"""
Schémas Pydantic V2 pour les Utilisateurs.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from app.models.utilisateur import UserRole, UserStatus


class UserBase(BaseModel):
    email: EmailStr
    nom: str
    prenom: str
    telephone: Optional[str] = None
    role: UserRole
    is_active: bool = True


class UserCreate(UserBase):
    password: str
    etudiant_id: Optional[str] = None


class UserUpdate(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    telephone: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None
    etudiant_id: Optional[str] = None


class CurrentProfileUpdate(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    telephone: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class UserResponse(UserBase):
    id: int
    is_superuser: bool
    etudiant_id: Optional[str] = None
    avatar_url: Optional[str] = None
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
