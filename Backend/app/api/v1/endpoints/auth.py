"""
Authentication Endpoints :
- POST /login : Connexion avec email et mot de passe, génération du token JWT
- GET /me : Profil de l'utilisateur actuellement connecté
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db, get_current_active_user
from app.core.config import settings
from app.core.security import verify_password, create_access_token, get_password_hash
from app.models.utilisateur import Utilisateur
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import CurrentProfileUpdate, PasswordChange, UserResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse, summary="Authentification utilisateur")
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authentifie un utilisateur avec son email et son mot de passe.
    Retourne un jeton JWT Bearer et le profil utilisateur.
    """
    email = payload.email.lower().strip()
    stmt = select(Utilisateur).where(Utilisateur.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Adresse email ou mot de passe incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Votre compte utilisateur a été désactivé. Veuillez contacter l'administrateur."
        )

    # Mise à jour date dernière connexion
    user.last_login = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    # Génération du token
    token = create_access_token(
        subject=user.id,
        claims={"email": user.email, "role": user.role}
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse, summary="Profil utilisateur connecté")
async def get_current_user_profile(
    current_user: Utilisateur = Depends(get_current_active_user)
):
    """Retourne les informations du profil de l'utilisateur actuellement authentifié."""
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse, summary="Modifier son profil")
async def update_current_user_profile(
    payload: CurrentProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_active_user),
):
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(current_user, field, value or None)
    await db.commit()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT, summary="Modifier son mot de passe")
async def change_current_password(
    payload: PasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_active_user),
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mot de passe actuel incorrect.")
    current_user.hashed_password = get_password_hash(payload.new_password)
    await db.commit()
