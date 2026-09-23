"""
Dépendances FastAPI (Injection de dépendances) :
- Session de base de données asynchrone (get_db)
- Authentification JWT et utilisateur courant (get_current_user)
- Contrôle d'accès basé sur les rôles RBAC (require_role)
"""

from typing import AsyncGenerator, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.security import decode_access_token
from app.models.utilisateur import Utilisateur, UserRole


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Fournit une session SQLAlchemy asynchrone avec commit/rollback automatique."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> Utilisateur:
    """Valide le jeton JWT et retourne l'utilisateur courant."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants d'authentification invalides ou session expirée.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if not user_id:
        raise credentials_exception

    stmt = select(Utilisateur).where(Utilisateur.id == int(user_id))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Utilisateur = Depends(get_current_user)
) -> Utilisateur:
    """Vérifie que le compte utilisateur est actif."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce compte utilisateur est désactivé."
        )
    return current_user


class RoleChecker:
    """Vérifie que l'utilisateur possède l'un des rôles requis."""
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: Utilisateur = Depends(get_current_active_user)) -> Utilisateur:
        if user.is_superuser:
            return user
        if user.role not in [role.value for role in self.allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissions insuffisantes pour effectuer cette action."
            )
        return user


require_admin = RoleChecker([UserRole.ADMIN])
require_pedagogie = RoleChecker([UserRole.ADMIN, UserRole.DIRECTEUR_ETUDES])
require_enseignant = RoleChecker([UserRole.ADMIN, UserRole.DIRECTEUR_ETUDES, UserRole.ENSEIGNANT])
require_comptabilite = RoleChecker([UserRole.ADMIN, UserRole.COMPTABILITE])
require_secretariat = RoleChecker([UserRole.ADMIN, UserRole.DIRECTEUR_ETUDES, UserRole.SECRETARIAT])
