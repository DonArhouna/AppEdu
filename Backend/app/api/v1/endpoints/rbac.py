"""Administration du RBAC dynamique (prefixe ``/api/v1/rbac``).

Toutes les routes exigent la permission dynamique ``roles.manage`` (via
``require_rbac_admin``), ce qui laisse passer ADMIN legacy pour la transition
sans jamais consulter ``is_superuser``.

Aucune operation n'ecrit dans ``utilisateurs.role`` sauf demande explicite via
``aligner_role_legacy`` : la colonne reste une projection historique que les
guards statiques existants continuent de lire.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_rbac_admin
from app.models.rbac import Permission, Role, RolePermission, UserRoleAssignment
from app.models.utilisateur import Utilisateur, UserRole
from app.schemas.rbac import (
    EffectivePermissionsResponse,
    PermissionCreate,
    PermissionResponse,
    PermissionUpdate,
    RbacUserResponse,
    RoleCreate,
    RolePermissionAdd,
    RolePermissionsSet,
    RoleResponse,
    RoleUpdate,
    RoleUsersAssign,
    RoleUsersResponse,
    UserRoleAssignmentResponse,
)
from app.services.audit_service import record_audit_event
from app.services.rbac_service import (
    effective_permissions,
    is_system_role_code,
    role_permission_codes,
    system_code_to_legacy_role,
)

router = APIRouter()

#: Rang de privilege des roles legacy.  Utilise uniquement pour interdire
#: l'alignement d'un role systeme moins hierarchique que le role deja porte :
#: une affectation ne doit jamais pouvoir retirer un droit a un compte.
_LEGACY_ROLE_RANK = {
    UserRole.ETUDIANT.value: 10,
    UserRole.COMPTABILITE.value: 20,
    UserRole.ENSEIGNANT.value: 20,
    UserRole.SECRETARIAT.value: 30,
    UserRole.DIRECTEUR_ETUDES.value: 40,
    UserRole.ADMIN.value: 50,
}


def _legacy_role_rank(role: Optional[str]) -> int:
    return _LEGACY_ROLE_RANK.get((role or "").upper(), -1)


# ---------------------------------------------------------------------------
# Helpers de chargement
# ---------------------------------------------------------------------------
async def _get_permission(db: AsyncSession, code: str) -> Permission:
    result = await db.execute(
        select(Permission).where(Permission.code == code.strip().lower())
    )
    permission = result.scalar_one_or_none()
    if permission is None:
        raise HTTPException(status_code=404, detail="Permission introuvable.")
    return permission


async def _get_role(db: AsyncSession, code: str) -> Role:
    result = await db.execute(select(Role).where(Role.code == code.strip().upper()))
    role = result.scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=404, detail="Role introuvable.")
    return role


async def _resolve_permissions(
    db: AsyncSession, codes: List[str]
) -> dict[str, Permission]:
    """Charge un lot de permissions et refuse toute entree inconnue ou inactive."""

    if not codes:
        return {}
    result = await db.execute(select(Permission).where(Permission.code.in_(codes)))
    found = {item.code: item for item in result.scalars().all()}
    manquantes = [code for code in codes if code not in found]
    if manquantes:
        raise HTTPException(
            status_code=422,
            detail=(
                "Permissions inconnues : "
                + ", ".join(manquantes)
                + ". Créez-les d'abord dans le catalogue."
            ),
        )
    inactives = sorted(code for code, item in found.items() if not item.actif)
    if inactives:
        raise HTTPException(
            status_code=422,
            detail="Permissions inactives refusées : " + ", ".join(inactives) + ".",
        )
    return found


async def _active_assignment_counts(
    db: AsyncSession, role_ids: List[int]
) -> dict[int, int]:
    if not role_ids:
        return {}
    result = await db.execute(
        select(UserRoleAssignment.role_id, func.count(UserRoleAssignment.id))
        .where(
            UserRoleAssignment.role_id.in_(role_ids),
            UserRoleAssignment.actif.is_(True),
        )
        .group_by(UserRoleAssignment.role_id)
    )
    return {row[0]: int(row[1]) for row in result.all()}


async def _serialize_roles(
    db: AsyncSession, roles: List[Role]
) -> List[RoleResponse]:
    counts = await _active_assignment_counts(db, [role.id for role in roles])
    payloads: List[RoleResponse] = []
    for role in roles:
        response = RoleResponse.model_validate(role)
        response.permissions = await role_permission_codes(db, role.id)
        response.utilisateurs = counts.get(role.id, 0)
        payloads.append(response)
    return payloads


async def _serialize_role(db: AsyncSession, role: Role) -> RoleResponse:
    return (await _serialize_roles(db, [role]))[0]


def _assignment_payload(link: UserRoleAssignment) -> UserRoleAssignmentResponse:
    return UserRoleAssignmentResponse(
        user_id=link.user_id,
        role_id=link.role_id,
        role_code=link.role.code,
        role_libelle=link.role.libelle,
        role_systeme=link.role.systeme,
        actif=link.actif,
        motif=link.motif,
        attribue_par=link.attribue_par,
        created_at=link.created_at,
        updated_at=link.updated_at,
    )


async def _audit(
    db: AsyncSession,
    actor: Utilisateur,
    *,
    action: str,
    resource_type: str,
    resource_id: Optional[str],
    details: Optional[dict] = None,
) -> None:
    await record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
    )


# ---------------------------------------------------------------------------
# Catalogue de permissions
# ---------------------------------------------------------------------------
@router.get(
    "/permissions",
    response_model=List[PermissionResponse],
    summary="Lister le catalogue de permissions",
)
async def list_permissions(
    domaine: Optional[str] = Query(None, max_length=50),
    actif: Optional[bool] = None,
    systeme: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    _actor: Utilisateur = Depends(require_rbac_admin),
):
    """Catalogue complet, filtreable par domaine, activation et origine."""

    stmt = select(Permission)
    if domaine:
        stmt = stmt.where(Permission.domaine == domaine.strip().lower())
    if actif is not None:
        stmt = stmt.where(Permission.actif.is_(actif))
    if systeme is not None:
        stmt = stmt.where(Permission.systeme.is_(systeme))
    result = await db.execute(stmt.order_by(Permission.code.asc()))
    return list(result.scalars().all())


@router.post(
    "/permissions",
    response_model=PermissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une permission",
)
async def create_permission(
    payload: PermissionCreate,
    db: AsyncSession = Depends(get_db),
    actor: Utilisateur = Depends(require_rbac_admin),
):
    """Crée une permission hors catalogue livré par la migration.

    Les permissions techniques livrées par la migration portent ``systeme=True``
    : leur code est immuable et elles ne peuvent être ni supprimées ni
    désactivées.  Une permission créée ici est modifiable et supprimable tant
    qu'aucun rôle ne la porte.
    """

    code = payload.code
    existing = await db.execute(select(Permission).where(Permission.code == code))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409,
            detail="Ce code de permission est déjà utilisé par le catalogue.",
        )

    domaine, _, action = code.partition(".")
    permission = Permission(
        code=code,
        domaine=domaine,
        action=action,
        libelle=payload.libelle.strip(),
        description=payload.description,
        systeme=False,
        actif=payload.actif,
    )
    db.add(permission)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409, detail="Ce code de permission est déjà utilisé."
        ) from exc

    await _audit(
        db,
        actor,
        action="security.rbac.permission.created",
        resource_type="rbac_permission",
        resource_id=permission.code,
        details={"code": permission.code, "domaine": permission.domaine},
    )
    await db.commit()
    await db.refresh(permission)
    return permission


@router.get(
    "/permissions/{code}",
    response_model=PermissionResponse,
    summary="Détail d'une permission",
)
async def get_permission(
    code: str,
    db: AsyncSession = Depends(get_db),
    _actor: Utilisateur = Depends(require_rbac_admin),
):
    return await _get_permission(db, code)


@router.patch(
    "/permissions/{code}",
    response_model=PermissionResponse,
    summary="Modifier une permission",
)
async def update_permission(
    code: str,
    payload: PermissionUpdate,
    db: AsyncSession = Depends(get_db),
    actor: Utilisateur = Depends(require_rbac_admin),
):
    """Met à jour les métadonnées d'interface d'une permission.

    Le ``code`` est immuable : il est référencé par les grants et par le
    frontend.  Une permission système ne peut pas être désactivée.
    """

    permission = await _get_permission(db, code)
    data = payload.model_dump(exclude_unset=True)
    if "actif" in data and data["actif"] is False and permission.systeme:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"La permission système {permission.code} ne peut pas être "
                "désactivée. Retirez-la des rôles qui la portent si nécessaire."
            ),
        )
    if "libelle" in data and not data["libelle"]:
        raise HTTPException(status_code=422, detail="Le libellé ne peut pas être vide.")
    for field, value in data.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(permission, field, value)

    await _audit(
        db,
        actor,
        action="security.rbac.permission.updated",
        resource_type="rbac_permission",
        resource_id=permission.code,
        details={"changed_fields": sorted(data.keys())},
    )
    await db.commit()
    await db.refresh(permission)
    return permission


@router.delete(
    "/permissions/{code}",
    summary="Supprimer une permission",
)
async def delete_permission(
    code: str,
    db: AsyncSession = Depends(get_db),
    actor: Utilisateur = Depends(require_rbac_admin),
):
    """Supprime une permission non système et non utilisée.

    Une permission du catalogue technique est protégée : la migration l'a posée
    comme garde-fou des guards, la retirer en silence casserait l'accès sans
    trace.  Une permission portée par un rôle est également refusée.
    """

    permission = await _get_permission(db, code)
    if permission.systeme:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"La permission {permission.code} appartient au catalogue "
                "technique et ne peut pas être supprimée."
            ),
        )

    usage = await db.execute(
        select(func.count(RolePermission.id)).where(
            RolePermission.permission_id == permission.id
        )
    )
    if int(usage.scalar() or 0) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"La permission {permission.code} est encore accordée à un rôle. "
                "Retirez-la de ces rôles avant de la supprimer."
            ),
        )

    code_ref = permission.code
    await _audit(
        db,
        actor,
        action="security.rbac.permission.deleted",
        resource_type="rbac_permission",
        resource_id=code_ref,
    )
    await db.delete(permission)
    await db.commit()
    return {"supprime": True, "code": code_ref}


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------
@router.get("/roles", response_model=List[RoleResponse], summary="Lister les rôles")
async def list_roles(
    actif: Optional[bool] = None,
    systeme: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    _actor: Utilisateur = Depends(require_rbac_admin),
):
    stmt = select(Role)
    if actif is not None:
        stmt = stmt.where(Role.actif.is_(actif))
    if systeme is not None:
        stmt = stmt.where(Role.systeme.is_(systeme))
    result = await db.execute(stmt.order_by(Role.ordre.asc(), Role.code.asc()))
    return await _serialize_roles(db, list(result.scalars().all()))


@router.post(
    "/roles",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un rôle",
)
async def create_role(
    payload: RoleCreate,
    db: AsyncSession = Depends(get_db),
    actor: Utilisateur = Depends(require_rbac_admin),
):
    """Crée un rôle dynamique libre, créé sans aucune permission.

    Le rôle naît vide : l'octroi de permissions est une action séparée et
    explicite, ce qui évite tout héritage implicite.
    """

    code = payload.code
    if is_system_role_code(code):
        raise HTTPException(
            status_code=409,
            detail=f"Le code {code} est réservé aux rôles système.",
        )
    existing = await db.execute(select(Role).where(Role.code == code))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Ce code de rôle est déjà utilisé.")

    role = Role(
        code=code,
        libelle=payload.libelle.strip(),
        description=payload.description,
        ordre=payload.ordre,
        systeme=False,
        actif=payload.actif,
    )
    db.add(role)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Ce code de rôle est déjà utilisé.") from exc

    await _audit(
        db,
        actor,
        action="security.rbac.role.created",
        resource_type="rbac_role",
        resource_id=role.code,
        details={"code": role.code, "ordre": role.ordre},
    )
    await db.commit()
    await db.refresh(role)
    return await _serialize_role(db, role)


@router.get("/roles/{code}", response_model=RoleResponse, summary="Détail d'un rôle")
async def get_role(
    code: str,
    db: AsyncSession = Depends(get_db),
    _actor: Utilisateur = Depends(require_rbac_admin),
):
    return await _serialize_role(db, await _get_role(db, code))


@router.put("/roles/{code}", response_model=RoleResponse, summary="Modifier un rôle")
async def update_role(
    code: str,
    payload: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    actor: Utilisateur = Depends(require_rbac_admin),
):
    """Met à jour libellé, description, ordre et activation d'un rôle.

    Le ``code`` et l'indicateur ``systeme`` restent immuables.  Un rôle système
    peut être désactivé : ses porteurs perdent alors ses permissions sans que le
    rôle ne soit supprimé.
    """

    role = await _get_role(db, code)
    data = payload.model_dump(exclude_unset=True)
    if "libelle" in data and not data["libelle"]:
        raise HTTPException(status_code=422, detail="Le libellé ne peut pas être vide.")
    for field, value in data.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(role, field, value)

    await _audit(
        db,
        actor,
        action="security.rbac.role.updated",
        resource_type="rbac_role",
        resource_id=role.code,
        details={"changed_fields": sorted(data.keys())},
    )
    await db.commit()
    await db.refresh(role)
    return await _serialize_role(db, role)


@router.delete("/roles/{code}", summary="Supprimer un rôle")
async def delete_role(
    code: str,
    db: AsyncSession = Depends(get_db),
    actor: Utilisateur = Depends(require_rbac_admin),
):
    """Supprime un rôle dynamique libre, non système et non affecté.

    Les six rôles livrés par la migration ne sont jamais supprimés : les
    désactiver suffit à retirer leurs permissions sans casser les références.
    Un rôle encore porté par un compte est refusé afin de ne pas retirer un
    accès en silence.
    """

    role = await _get_role(db, code)
    if role.systeme:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Le rôle {role.code} est un rôle système et ne peut pas être "
                "supprimé. Désactivez-le pour retirer ses permissions."
            ),
        )

    usage = await db.execute(
        select(func.count(UserRoleAssignment.id)).where(
            UserRoleAssignment.role_id == role.id,
            UserRoleAssignment.actif.is_(True),
        )
    )
    if int(usage.scalar() or 0) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Le rôle {role.code} est encore affecté à des utilisateurs. "
                "Retirez-le de ces comptes avant de le supprimer."
            ),
        )

    code_ref = role.code
    await _audit(
        db,
        actor,
        action="security.rbac.role.deleted",
        resource_type="rbac_role",
        resource_id=code_ref,
    )
    await db.delete(role)
    await db.commit()
    return {"supprime": True, "code": code_ref}


# ---------------------------------------------------------------------------
# Permissions d'un rôle
# ---------------------------------------------------------------------------
@router.get(
    "/roles/{code}/permissions",
    response_model=List[PermissionResponse],
    summary="Permissions accordées à un rôle",
)
async def list_role_permissions(
    code: str,
    db: AsyncSession = Depends(get_db),
    _actor: Utilisateur = Depends(require_rbac_admin),
):
    """Permissions liées au rôle, permissions inactives incluses.

    Lister une permission désactivée reste possible : elle peut encore être
    portée par le rôle, elle ne produit simplement plus d'accès.
    """

    role = await _get_role(db, code)
    result = await db.execute(
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role.id)
        .order_by(Permission.code.asc())
    )
    return list(result.scalars().all())


@router.put(
    "/roles/{code}/permissions",
    response_model=RoleResponse,
    summary="Remplacer les permissions d'un rôle",
)
async def set_role_permissions(
    code: str,
    payload: RolePermissionsSet,
    db: AsyncSession = Depends(get_db),
    actor: Utilisateur = Depends(require_rbac_admin),
):
    """Remplace l'intégralité des permissions d'un rôle (PUT idempotent).

    Chaque permission reçue est ajoutée si absente ; toute permission absente
    de la liste est retirée.  Le modèle reste allow-only et sans héritage :
    retirer une permission retire réellement l'accès, sans exception ni masquage
    implicite.
    """

    role = await _get_role(db, code)
    found = await _resolve_permissions(db, list(payload.permissions))

    current = await db.execute(
        select(RolePermission).where(RolePermission.role_id == role.id)
    )
    existing_links = list(current.scalars().all())
    existing_permission_ids = {link.permission_id for link in existing_links}

    keep_ids = {item.id for item in found.values()}
    for link in existing_links:
        if link.permission_id not in keep_ids:
            await db.delete(link)

    added: List[str] = []
    for permission in found.values():
        if permission.id in existing_permission_ids:
            continue
        db.add(
            RolePermission(
                role_id=role.id,
                permission_id=permission.id,
                attribue_par=actor.id,
                motif=payload.motif,
            )
        )
        added.append(permission.code)

    await db.flush()
    await _audit(
        db,
        actor,
        action="security.rbac.role.permissions_set",
        resource_type="rbac_role",
        resource_id=role.code,
        details={
            "ajoutees": sorted(added),
            "permissions": list(payload.permissions),
        },
    )
    await db.commit()
    await db.refresh(role)
    return await _serialize_role(db, role)


@router.post(
    "/roles/{code}/permissions",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter une permission à un rôle",
)
async def add_role_permission(
    code: str,
    payload: RolePermissionAdd,
    db: AsyncSession = Depends(get_db),
    actor: Utilisateur = Depends(require_rbac_admin),
):
    """Ajoute une permission à un rôle, de manière idempotente."""

    role = await _get_role(db, code)
    found = await _resolve_permissions(db, [payload.permission])
    permission = found[payload.permission]

    result = await db.execute(
        select(RolePermission).where(
            RolePermission.role_id == role.id,
            RolePermission.permission_id == permission.id,
        )
    )
    link = result.scalar_one_or_none()
    if link is None:
        db.add(
            RolePermission(
                role_id=role.id,
                permission_id=permission.id,
                attribue_par=actor.id,
                motif=payload.motif,
            )
        )
    else:
        link.attribue_par = actor.id
        if payload.motif:
            link.motif = payload.motif

    await _audit(
        db,
        actor,
        action="security.rbac.role.permission_added",
        resource_type="rbac_role",
        resource_id=role.code,
        details={"permission": permission.code},
    )
    await db.commit()
    await db.refresh(role)
    return await _serialize_role(db, role)


@router.delete(
    "/roles/{code}/permissions/{permission_code}",
    response_model=RoleResponse,
    summary="Retirer une permission d'un rôle",
)
async def remove_role_permission(
    code: str,
    permission_code: str,
    db: AsyncSession = Depends(get_db),
    actor: Utilisateur = Depends(require_rbac_admin),
):
    role = await _get_role(db, code)
    permission = await _get_permission(db, permission_code)
    result = await db.execute(
        select(RolePermission).where(
            RolePermission.role_id == role.id,
            RolePermission.permission_id == permission.id,
        )
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(
            status_code=404,
            detail="Cette permission n'est pas accordée à ce rôle.",
        )
    await db.delete(link)
    await _audit(
        db,
        actor,
        action="security.rbac.role.permission_removed",
        resource_type="rbac_role",
        resource_id=role.code,
        details={"permission": permission.code},
    )
    await db.commit()
    await db.refresh(role)
    return await _serialize_role(db, role)


# ---------------------------------------------------------------------------
# Affectation de rôles à des utilisateurs
# ---------------------------------------------------------------------------
@router.post(
    "/roles/{code}/users",
    response_model=RoleUsersResponse,
    summary="Affecter un rôle à des utilisateurs",
)
async def assign_role_to_users(
    code: str,
    payload: RoleUsersAssign,
    db: AsyncSession = Depends(get_db),
    actor: Utilisateur = Depends(require_rbac_admin),
):
    """Affecte (ou réactive) un rôle à une liste de comptes.

    L'opération est idempotente : un compte déjà porteur du rôle est listé dans
    ``deja_affectes`` au lieu de provoquer une erreur.

    ``aligner_role_legacy`` écrit explicitement la projection
    ``utilisateurs.role``.  L'écriture est refusée si le rôle n'a pas
    d'équivalent legacy, et si le compte porte déjà un rôle legacy plus
    hiérarchique : une affectation ne doit jamais pouvoir retirer un droit.
    """

    role = await _get_role(db, code)
    if not role.actif:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Le rôle {role.code} est désactivé.",
        )

    legacy_role = system_code_to_legacy_role(role.code)
    if payload.aligner_role_legacy and legacy_role is None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Le rôle {role.code} n'a pas d'équivalent legacy : la projection "
                "utilisateurs.role ne peut pas être alignée."
            ),
        )

    unique_ids = sorted(set(payload.user_ids))
    result = await db.execute(select(Utilisateur).where(Utilisateur.id.in_(unique_ids)))
    users = {user.id: user for user in result.scalars().all()}
    manquants = [user_id for user_id in unique_ids if user_id not in users]
    if manquants:
        raise HTTPException(
            status_code=422,
            detail="Utilisateurs introuvables : " + ", ".join(map(str, manquants)) + ".",
        )

    existing = await db.execute(
        select(UserRoleAssignment).where(
            UserRoleAssignment.role_id == role.id,
            UserRoleAssignment.user_id.in_(unique_ids),
        )
    )
    existing_by_user = {link.user_id: link for link in existing.scalars().all()}
    deja_affectes = [user_id for user_id in unique_ids if user_id in existing_by_user]

    legacy_aligne: Optional[str] = None

    for user_id in unique_ids:
        user = users[user_id]
        link = existing_by_user.get(user_id)
        if link is None:
            link = UserRoleAssignment(
                user_id=user_id,
                role_id=role.id,
                actif=True,
                attribue_par=actor.id,
                motif=payload.motif,
            )
            db.add(link)
        else:
            link.actif = True
            link.attribue_par = actor.id
            if payload.motif:
                link.motif = payload.motif
        link.role = role
        await db.flush()

        if payload.aligner_role_legacy and legacy_role:
            current_rank = _legacy_role_rank(user.role)
            target_rank = _legacy_role_rank(legacy_role)
            if current_rank > target_rank:
                # Aucune lecture d'attribut ORM apres ce point : le rollback est
                # laisse a la dependance ``get_db``, qui expire la session.
                user_email = user.email
                user_role = user.role
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Le compte {user_email} porte déjà le rôle legacy "
                        f"{user_role}, plus hiérarchique que {legacy_role}. "
                        "Affectez le rôle sans alignement pour ne pas "
                        "rétrograder ses droits legacy."
                    ),
                )
            if user.role != legacy_role:
                user.role = legacy_role
                user.is_superuser = legacy_role == UserRole.ADMIN.value
                legacy_aligne = legacy_role

    await _audit(
        db,
        actor,
        action="security.rbac.role.assigned",
        resource_type="rbac_role",
        resource_id=role.code,
        details={
            "users": unique_ids,
            "deja_affectes": deja_affectes,
            "aligner_role_legacy": payload.aligner_role_legacy,
            "role_legacy_projete": legacy_aligne,
        },
    )
    await db.commit()

    # Les reponses sont construites apres le commit : ``created_at`` et
    # ``updated_at`` sont des valeurs par defaut serveur, donc lues au commit.
    reponses: List[UserRoleAssignmentResponse] = []
    relecture = await db.execute(
        select(UserRoleAssignment).where(
            UserRoleAssignment.role_id == role.id,
            UserRoleAssignment.user_id.in_(unique_ids),
        )
    )
    for link in sorted(relecture.scalars().all(), key=lambda item: item.user_id):
        link.role = role
        reponses.append(_assignment_payload(link))

    return RoleUsersResponse(
        role_code=role.code,
        affectes=unique_ids,
        deja_affectes=deja_affectes,
        reponses=reponses,
        legacy_role_aligne=legacy_aligne,
    )


@router.get(
    "/roles/{code}/users",
    response_model=List[UserRoleAssignmentResponse],
    summary="Utilisateurs porteurs d'un rôle",
)
async def list_role_users(
    code: str,
    actif: Optional[bool] = Query(
        None,
        description=(
            "Filtre l'état des affectations. Sans filtre, les affectations "
            "inactives (historiquement conservées) sont aussi listées."
        ),
    ),
    db: AsyncSession = Depends(get_db),
    _actor: Utilisateur = Depends(require_rbac_admin),
):
    role = await _get_role(db, code)
    stmt = select(UserRoleAssignment).where(UserRoleAssignment.role_id == role.id)
    if actif is not None:
        stmt = stmt.where(UserRoleAssignment.actif.is_(actif))
    result = await db.execute(stmt.order_by(UserRoleAssignment.user_id.asc()))
    links = list(result.scalars().all())
    for link in links:
        link.role = role
    return [_assignment_payload(link) for link in links]


@router.delete(
    "/roles/{code}/users/{user_id}",
    response_model=RoleUsersResponse,
    summary="Retirer un rôle d'un utilisateur",
)
async def remove_role_from_user(
    code: str,
    user_id: int,
    aligner_role_legacy: bool = Query(
        False,
        description=(
            "Projette le rôle système sur utilisateurs.role au moment du "
            "retrait. Refusé pour un rôle sans équivalent legacy."
        ),
    ),
    db: AsyncSession = Depends(get_db),
    actor: Utilisateur = Depends(require_rbac_admin),
):
    """Retire (ou désactive) une affectation utilisateur-rôle.

    La ligne d'affectation est conservée et marquée inactive : l'historique
    reste consultable et une réattribution ultérieure est idempotente.

    ``utilisateurs.role`` n'est modifiée que si ``aligner_role_legacy=true``.
    Sans ce drapeau — le mode attendu pendant la transition — les deux couches
    restent indépendantes.
    """

    role = await _get_role(db, code)
    result = await db.execute(
        select(UserRoleAssignment).where(
            UserRoleAssignment.role_id == role.id,
            UserRoleAssignment.user_id == user_id,
        )
    )
    link = result.scalar_one_or_none()
    # Une affectation déjà désactivée est historiquement conservée mais
    # n'existe plus en droit : la réponse est 404, pas un 200 sans effet.
    if link is None or not link.actif:
        raise HTTPException(status_code=404, detail="Ce compte ne porte pas ce rôle.")

    legacy_aligne: Optional[str] = None
    if aligner_role_legacy:
        legacy_role = system_code_to_legacy_role(role.code)
        if legacy_role is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Le rôle {role.code} n'a pas d'équivalent legacy : la projection "
                    "utilisateurs.role ne peut pas être alignée."
                ),
            )
        user = await db.get(Utilisateur, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
        if user.role == legacy_role:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Ce compte porte déjà ce rôle legacy. Choisissez explicitement "
                    "une autre valeur de projection avant de l'aligner."
                ),
            )
        user.role = legacy_role
        user.is_superuser = legacy_role == UserRole.ADMIN.value
        legacy_aligne = legacy_role

    link.actif = False
    await db.flush()
    await _audit(
        db,
        actor,
        action="security.rbac.role.unassigned",
        resource_type="rbac_role",
        resource_id=role.code,
        details={"user_id": user_id, "aligner_role_legacy": aligner_role_legacy},
    )
    await db.commit()
    return RoleUsersResponse(
        role_code=role.code,
        affectes=[],
        deja_affectes=[user_id],
        reponses=[],
        legacy_role_aligne=legacy_aligne,
    )


# ---------------------------------------------------------------------------
# Vue utilisateurs / rôles
# ---------------------------------------------------------------------------
@router.get(
    "/users/roles",
    response_model=List[RbacUserResponse],
    summary="Rôles et permissions effectifs par utilisateur",
)
async def list_users_roles(
    role_code: Optional[str] = Query(
        None, max_length=50, description="Filtre sur un code de rôle dynamique."
    ),
    db: AsyncSession = Depends(get_db),
    _actor: Utilisateur = Depends(require_rbac_admin),
):
    """Retourne pour chaque compte ses rôles dynamiques et ses permissions.

    La liste des comptes est résolue en jointure, puis chaque autorisation est
    résolue par ``effective_permissions`` : aucune matrice n'est materialisée en
    mémoire, la réponse est la projection réelle de la base.
    """

    normalized = role_code.strip().upper() if role_code else None
    stmt = select(Utilisateur).order_by(Utilisateur.nom.asc(), Utilisateur.prenom.asc())
    if normalized:
        subquery = (
            select(UserRoleAssignment.user_id)
            .join(Role, Role.id == UserRoleAssignment.role_id)
            .where(
                Role.code == normalized,
                UserRoleAssignment.actif.is_(True),
                Role.actif.is_(True),
            )
        )
        stmt = stmt.where(Utilisateur.id.in_(subquery))

    result = await db.execute(stmt)
    payloads: List[RbacUserResponse] = []
    for user in result.scalars().all():
        authorization = await effective_permissions(db, user)
        if normalized and normalized not in authorization.role_codes:
            continue
        payloads.append(
            RbacUserResponse(
                id=user.id,
                email=user.email,
                nom=user.nom,
                prenom=user.prenom,
                role=user.role,
                is_active=bool(user.is_active),
                roles=list(authorization.role_codes),
                role_labels=list(authorization.role_labels),
                permissions=list(authorization.permission_codes),
                authz_version=authorization.authz_version,
            )
        )
    return payloads


@router.get(
    "/users/{user_id}/permissions",
    response_model=EffectivePermissionsResponse,
    summary="Permissions effectives d'un utilisateur",
)
async def get_user_effective_permissions(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _actor: Utilisateur = Depends(require_rbac_admin),
):
    """Résout l'autorité effective d'un compte, sans héritage de rôles.

    Le résultat est purement consultatif : il n'accorde rien.  Seuls les guards
    (``require_permission``) décident d'un accès.
    """

    user = await db.get(Utilisateur, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    authorization = await effective_permissions(db, user)
    return EffectivePermissionsResponse(
        user_id=authorization.user_id,
        role=authorization.legacy_role,
        legacy_role_is_admin=authorization.legacy_role_is_admin,
        roles=list(authorization.role_codes),
        role_labels=list(authorization.role_labels),
        permissions=list(authorization.permission_codes),
        permission_domains=list(authorization.permission_domains),
        authz_version=authorization.authz_version,
    )


__all__ = ["router"]
