"""Administration des comptes utilisateurs."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin, require_academic_staff
from app.core.security import get_password_hash
from app.models.etudiant import Etudiant
from app.models.utilisateur import Utilisateur, UserRole
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter()


async def _validate_student_link(
    db: AsyncSession,
    etudiant_id: str | None,
    role: str,
) -> None:
    """Valide le lien optionnel compte étudiant sans exposer les autres dossiers."""

    if etudiant_id is None:
        return
    if role != UserRole.ETUDIANT.value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Un compte non étudiant ne peut pas être lié à un dossier étudiant.",
        )
    if await db.get(Etudiant, etudiant_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le dossier étudiant sélectionné n'existe pas.",
        )


@router.get("/", response_model=List[UserResponse], summary="Lister les utilisateurs")
async def list_users(
    role: Optional[str] = None,
    active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    _staff=Depends(require_academic_staff),
):
    if _staff.role != UserRole.ADMIN.value and (role or "").upper() != UserRole.ENSEIGNANT.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Les rôles.non-administrateurs ne peuvent consulter que le référentiel des enseignants.",
        )
    stmt = select(Utilisateur)
    if role:
        stmt = stmt.where(Utilisateur.role == role.upper())
    if active is not None:
        stmt = stmt.where(Utilisateur.is_active == active)
    stmt = stmt.order_by(Utilisateur.nom.asc(), Utilisateur.prenom.asc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Créer un utilisateur")
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    email = str(payload.email).lower()
    existing = await db.execute(select(Utilisateur).where(Utilisateur.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cet email est déjà utilisé.")
    if len(payload.password) < 8:
        raise HTTPException(status_code=422, detail="Le mot de passe doit contenir au moins 8 caractères.")
    await _validate_student_link(db, payload.etudiant_id, payload.role.value)
    user = Utilisateur(
        email=email,
        hashed_password=get_password_hash(payload.password),
        nom=payload.nom.strip(),
        prenom=payload.prenom.strip(),
        telephone=payload.telephone,
        role=payload.role.value,
        is_active=payload.is_active,
        etudiant_id=payload.etudiant_id,
        is_superuser=payload.role == UserRole.ADMIN,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserResponse, summary="Modifier un utilisateur")
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: Utilisateur = Depends(require_admin),
):
    user = await db.get(Utilisateur, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    data = payload.model_dump(exclude_unset=True)
    password = data.pop("password", None)
    if password is not None:
        if len(password) < 8:
            raise HTTPException(status_code=422, detail="Le mot de passe doit contenir au moins 8 caractères.")
        user.hashed_password = get_password_hash(password)
    if data.get("role"):
        data["role"] = UserRole(data["role"]).value
    if "etudiant_id" in data or "role" in data:
        target_role = data.get("role", user.role)
        target_student_id = data.get("etudiant_id", user.etudiant_id)
        await _validate_student_link(db, target_student_id, target_role)
    for field, value in data.items():
        if field in {"nom", "prenom"} and value is not None:
            value = value.strip()
        setattr(user, field, value)
    if data.get("role"):
        user.is_superuser = user.role == UserRole.ADMIN.value
    if admin.id == user.id and user.is_active is False:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas désactiver votre propre compte.")
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer un utilisateur")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: Utilisateur = Depends(require_admin),
):
    user = await db.get(Utilisateur, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    if admin.id == user.id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas supprimer votre propre compte.")
    await db.delete(user)
    await db.commit()
