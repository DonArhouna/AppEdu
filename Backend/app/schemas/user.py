"""
Schémas Pydantic V2 pour les Utilisateurs.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict
from app.models.utilisateur import UserRole, UserStatus


class UserBase(BaseModel):
    email: EmailStr
    nom: str
    prenom: str
    telephone: Optional[str] = None
    role: UserRole = UserRole.ADMIN
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    telephone: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    id: int
    is_superuser: bool
    avatar_url: Optional[str] = None
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
