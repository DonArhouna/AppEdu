"""
Schémas Pydantic V2 pour l'authentification et les tokens JWT.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr
from app.schemas.user import UserResponse


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    exp: Optional[int] = None
