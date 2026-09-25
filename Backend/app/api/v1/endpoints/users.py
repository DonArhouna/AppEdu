"""Administration des comptes utilisateurs.

Les guards historiques (``require_admin`` / ``require_academic_staff``) sont
remplaces par ``require_permission("users.manage")`` :

- ADMIN legacy passe toujours (raccourci de transition porte par le guard) ;
- les roles legacy qui consultaient deja l'annuaire le conservent explicitement
  via ``legacy_roles``, donc aucune regression de comportement ;
- un role dynamique portant ``users.manage`` accorde le meme acces.

Garde-fou anti-escalade : ``utilisateurs.role`` reste la source d'autorite des
guards statiques.  Seul ADMIN legacy peut creer un compte ADMIN ou modifier le
role ou l'activation d'un compte, afin qu'un role dynamique ``users.manage``
ne puisse pas s'auto-attribuer des pouvoirs.
"""

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permission, require_users_manage
from app.core.security import get_password_hash
from app.models.etudiant import Etudiant
from app.models.utilisateur import Utilisateur, UserRole
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.audit_service import record_audit_event
from app.services.user_security import (
    LastActiveAdministratorError,
    assert_not_last_active_administrator,
)

router = APIRouter()

#: La lecture de l'annuaire etait historiquement ouverte a tous les roles staff :
#: ils sont donc listes explicitement pour ne rien retirer a personne.
require_users_read = require_permission(
    "users.manage",
    legacy_roles=[
        UserRole.ADMIN,
        UserRole.DIRECTEUR_ETUDES,
        UserRole.SECRETARIAT,
        UserRole.ENSEIGNANT,
        UserRole.COMPTABILITE,
    ],
)


def _security_snapshot(user: Utilisateur) -> dict[str, Any]:
    return {
        "role": user.role,
        "is_active": user.is_active,
        "etudiant_id": user.etudiant_id,
    }


async def _validate_student_link(
    db: AsyncSession,
    etudiant_id: str | None,
    role: str,
    *,
    exclude_user_id: int | None = None,
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

    duplicate_stmt = select(Utilisateur.id).where(
        Utilisateur.etudiant_id == etudiant_id,
    )
    if exclude_user_id is not None:
        duplicate_stmt = duplicate_stmt.where(Utilisateur.id != exclude_user_id)
    duplicate = await db.execute(duplicate_stmt.limit(1))
    if duplicate.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce dossier étudiant est déjà lié à un autre compte utilisateur.",
        )


def _raise_last_admin_conflict(exc: LastActiveAdministratorError) -> None:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=str(exc),
    ) from exc


def _assert_can_manage_legacy_projection(
    actor: Utilisateur,
    *,
    target_role: str,
    touches_projection: bool,
) -> None:
    """Reserve la projection legacy ``utilisateurs.role`` a ADMIN legacy.

    Tant que les guards statiques lisent cette colonne, un role dynamique
    ``users.manage`` ne doit pas pouvoir s'auto-promouvoir : la regle est donc
    appliquee cote ecriture, pas seulement cote lecture du guard.
    """

    if not touches_projection:
        return
    if actor.role == UserRole.ADMIN.value:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            "Seul un compte de role legacy ADMIN peut creer un compte ADMIN "
            "ou modifier le role ou l'activation d'un compte tant que la "
            "projection utilisateurs.role fait autorite."
        ),
    )


@router.get("/", response_model=List[UserResponse], summary="Lister les utilisateurs")
async def list_users(
    role: Optional[str] = None,
    active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    _staff=Depends(require_users_read),
):
    if _staff.role != UserRole.ADMIN.value and (role or "").upper() != UserRole.ENSEIGNANT.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Les rôles non-administrateurs ne peuvent consulter que le référentiel des enseignants.",
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
    admin: Utilisateur = Depends(require_users_manage),
):
    email = str(payload.email).lower().strip()
    existing = await db.execute(select(Utilisateur).where(Utilisateur.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cet email est déjà utilisé.")
    if len(payload.password) < 8:
        raise HTTPException(status_code=422, detail="Le mot de passe doit contenir au moins 8 caractères.")
    # La creation d'un compte fixe sa projection legacy : elle est reservee a
    # ADMIN tant que les guards statiques s'appuient sur ``utilisateurs.role``.
    _assert_can_manage_legacy_projection(
        admin,
        target_role=payload.role.value,
        touches_projection=True,
    )
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
    await db.flush()
    await record_audit_event(
        db,
        actor_id=admin.id,
        actor_email=admin.email,
        action="security.user.created",
        resource_type="user",
        resource_id=user.id,
        details={"role": user.role, "is_active": user.is_active},
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserResponse, summary="Modifier un utilisateur")
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: Utilisateur = Depends(require_users_manage),
):
    user = await db.get(Utilisateur, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    data = payload.model_dump(exclude_unset=True)
    for protected_field in ("role", "is_active"):
        if protected_field in data and data[protected_field] is None:
            raise HTTPException(
                status_code=422,
                detail=f"Le champ '{protected_field}' ne peut pas être nul.",
            )

    # ``role``/``is_active`` pilotent la projection legacy lue par les guards
    # statiques : leur modification reste reservee a ADMIN legacy.
    _assert_can_manage_legacy_projection(
        admin,
        target_role=str(data.get("role", user.role)),
        touches_projection=("role" in data) or ("is_active" in data),
    )

    password = data.pop("password", None)
    if password is not None:
        if len(password) < 8:
            raise HTTPException(status_code=422, detail="Le mot de passe doit contenir au moins 8 caractères.")

    if "role" in data:
        data["role"] = UserRole(data["role"]).value

    target_role = data.get("role", user.role)
    target_is_active = data.get("is_active", user.is_active)
    if admin.id == user.id and (
        target_is_active is False or target_role != UserRole.ADMIN.value
    ):
        raise HTTPException(
            status_code=400,
            detail="Vous ne pouvez pas retirer vos propres droits administrateur.",
        )

    try:
        await assert_not_last_active_administrator(
            db,
            user,
            target_role=target_role,
            target_is_active=target_is_active,
        )
    except LastActiveAdministratorError as exc:
        _raise_last_admin_conflict(exc)

    if "etudiant_id" in data or "role" in data:
        target_student_id = data.get("etudiant_id", user.etudiant_id)
        await _validate_student_link(
            db,
            target_student_id,
            target_role,
            exclude_user_id=user.id,
        )

    before = _security_snapshot(user)
    changed_fields = sorted(data.keys())
    for field, value in data.items():
        if field in {"nom", "prenom"} and value is not None:
            value = value.strip()
        setattr(user, field, value)
    if password is not None:
        user.hashed_password = get_password_hash(password)
        changed_fields.append("password")

    # ``is_superuser`` reste une projection legacy, jamais une autorité.
    user.is_superuser = user.role == UserRole.ADMIN.value

    after = _security_snapshot(user)
    await record_audit_event(
        db,
        actor_id=admin.id,
        actor_email=admin.email,
        action=(
            "security.user.password_changed"
            if changed_fields == ["password"]
            else "security.user.updated"
        ),
        resource_type="user",
        resource_id=user.id,
        details={
            "changed_fields": sorted(set(changed_fields)),
            "before": before,
            "after": after,
        },
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer un utilisateur")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: Utilisateur = Depends(require_users_manage),
):
    user = await db.get(Utilisateur, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    if admin.id == user.id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas supprimer votre propre compte.")

    try:
        await assert_not_last_active_administrator(db, user)
    except LastActiveAdministratorError as exc:
        _raise_last_admin_conflict(exc)

    await record_audit_event(
        db,
        actor_id=admin.id,
        actor_email=admin.email,
        action="security.user.deleted",
        resource_type="user",
        resource_id=user.id,
        details=_security_snapshot(user),
    )
    await db.delete(user)
    await db.commit()
