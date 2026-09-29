"""
Schémas Pydantic V2 pour l'authentification et les tokens JWT.

Le contrat du login reste identique — ``access_token``, ``token_type``,
``expires_in``, ``user`` — augmenté d'un champ optionnel : ``refresh_token``.
Rien n'oblige un client existant à le lire ; le client qui le lit gagne la
session glissante et la révocation (lot 2).
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
    #: Présent dès que le serveur émet une session révocable. Optionnel pour
    #: ne casser aucun client existant : un client qui l'ignore se comporte
    #: exactement comme avant, avec des jetons d'une heure.
    refresh_token: Optional[str] = None


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    exp: Optional[int] = None


# ---------------------------------------------------------------------------
# Sessions révocables (lot 2)
# ---------------------------------------------------------------------------
class RefreshRequest(BaseModel):
    #: Le jeton de rafraîchissement, opaque : le serveur n'y lit rien, il le
    #: compare à son empreinte. Un jeton inconnu, expiré ou déjà tourné est
    #: le même refus.
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    #: La rotation rend un NOUVEAU jeton à chaque appel : garder l'ancien
    #: après rotation est le signal d'un vol, et le serveur l'a déjà révoqué.
    refresh_token: str


class LogoutRequest(BaseModel):
    #: Sans jeton, la requête déconnecte toutes les sessions du compte — la
    #: déconnexion « partout » d'un poste partagé.
    refresh_token: Optional[str] = None


class SessionResponse(BaseModel):
    """Une session du compte, telle que l'écran « mes sessions » la lit."""

    id: str
    created_at: str
    expires_at: str
    last_used_at: Optional[str] = None
    #: La session à laquelle la réponse est destinée, pour que l'écran
    #: désigne « cette » machine sans deviner.
    actuelle: bool = False


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]
    total: int
