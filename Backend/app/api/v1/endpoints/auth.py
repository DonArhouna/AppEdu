"""
Authentication Endpoints :
- POST /login : Connexion avec email et mot de passe, génération du token JWT
- GET /me : Profil de l'utilisateur actuellement connecté, augmenté des rôles
  dynamiques et des permissions effectives
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_active_user, get_db, legacy_permissions_for
from app.core.config import settings
from app.core.security import verify_password, create_access_token, get_password_hash
from app.models.utilisateur import Utilisateur, UserRole
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.rbac import CurrentUserResponse
from app.schemas.user import CurrentProfileUpdate, PasswordChange, UserResponse
from app.services.rbac_service import effective_permissions

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


@router.get("/me", response_model=CurrentUserResponse, summary="Profil utilisateur connecté")
async def get_current_user_profile(
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_active_user),
):
    """Retourne le profil de l'utilisateur actuellement authentifié.

    Le contrat historique est intégralement préservé : ``role`` reste la
    projection legacy et ``is_superuser`` reste la projection historique.
    Quatre champs additifs exposent l'autorité :

    - ``roles``                  : codes des rôles dynamiques actifs portés ;
    - ``permissions``            : autorité dynamique **pure** (allow-only) ;
    - ``permissions_effectives`` : droits **réellement exerçables**, c'est-à-dire
      l'union des permissions dynamiques et de la fenêtre de compatibilité du
      rôle legacy.  C'est le champ que l'interface doit utiliser pour afficher
      un menu ou ouvrir une vue, sans maintenir de matrice locale ;
    - ``authz_version``          : horodatage de la dernière modification
      d'autorité, à utiliser pour invalider un cache côté client.

    Les permissions sont résolues dans la transaction de la requête : la
    réponse est atomique avec l'état de la base au moment de la lecture.
    """
    profile = CurrentUserResponse.model_validate(current_user)
    authorization = await effective_permissions(db, current_user)
    profile.roles = list(authorization.role_codes)
    profile.permissions = list(authorization.permission_codes)
    # Fenêtre legacy issue de la même table de guards que les endpoints : le
    # client ne peut donc ni inventer ni manquer un droit.
    profile.permissions_effectives = sorted(
        set(authorization.permission_codes)
        | set(legacy_permissions_for(current_user.role))
        | ({"dashboard.read"} if current_user.role == UserRole.ADMIN.value else set())
    )
    profile.authz_version = authorization.authz_version
    return profile


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
