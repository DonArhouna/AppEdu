"""Resolution d'autorite RBAC dynamique.

Regles du modele :

- **Aucun heritage.** Un role n'herite d'aucun autre role ; il n'accorde que les
  permissions portees par ses lignes ``rbac_role_permissions``.
- **Allow-only.** Une permission absente est refusee ; il n'existe ni negation
  ni regle « tout sauf ».
- **Transaction-safe.** Aucune fonction de ce module n'ouvre ni ne commit de
  transaction : toutes lisent dans la transaction de l'appelant afin qu'une
  affectation et la reponse qu'elle produit soient atomiques.
- **``utilisateurs.role`` reste une projection.** Elle n'est jamais lue ici
  comme une autorite ; elle est seulement reportee dans le JSON pour que les
  guards statiques continuent de fonctionner pendant la transition.
"""

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    LEGACY_ROLE_TO_SYSTEM_CODE,
    SYSTEM_CODE_TO_LEGACY_ROLE,
    SYSTEM_ROLE_CODES,
)
from app.models.rbac import Permission, Role, RolePermission, UserRoleAssignment
from app.models.utilisateur import Utilisateur, UserRole


#: Raret du role legacy qui ouvre toutes les permissions pendant la transition.
LEGACY_ADMIN_ROLE: str = UserRole.ADMIN.value


def is_legacy_admin(user: Utilisateur) -> bool:
    """Vrai si l'utilisateur porte le role legacy ADMIN.

    ``is_superuser`` n'est volontairement pas consulte : c'est une projection
    historique, jamais une autorite.
    """

    return (user.role or "").upper() == LEGACY_ADMIN_ROLE


@dataclass(frozen=True)
class EffectiveAuthorization:
    """Autorite effective d'un compte, resolue depuis les tables RBAC."""

    user_id: int
    legacy_role: str
    legacy_role_is_admin: bool
    role_codes: tuple[str, ...] = ()
    role_labels: tuple[str, ...] = ()
    permission_codes: tuple[str, ...] = ()
    permission_domains: tuple[str, ...] = ()
    authz_version: Optional[str] = None

    def has_permission(self, permission_code: str) -> bool:
        """Autorite allow-only, avec repli explicite sur ADMIN legacy."""

        if self.legacy_role_is_admin:
            return True
        return permission_code in self.permission_codes

    def to_payload(self) -> dict:
        return {
            "user_id": self.user_id,
            "role": self.legacy_role,
            "roles": list(self.role_codes),
            "role_labels": list(self.role_labels),
            "permissions": list(self.permission_codes),
            "permission_domains": list(self.permission_domains),
            "authz_version": self.authz_version,
        }


async def list_effective_role_codes(
    db: AsyncSession, user_id: int
) -> list[tuple[str, str]]:
    """Retourne ``(code, libelle)`` des roles actifs portes par l'utilisateur.

    L'ordre est deterministe (``ordre`` puis ``code``) afin que le JSON de
    ``/auth/me`` soit stable et cacheable.
    """

    result = await db.execute(
        select(Role.code, Role.libelle)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
        .where(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.actif.is_(True),
            Role.actif.is_(True),
        )
        .order_by(Role.ordre.asc(), Role.code.asc())
    )
    return [(row[0], row[1]) for row in result.all()]


async def list_effective_permission_codes(db: AsyncSession, user_id: int) -> list[str]:
    """Retourne les codes de permissions effectivement portes par l'utilisateur.

    Seules les permissions actives, portees par des roles actifs, attaches par
    une affectation active sont retenues.  Aucune hierarchie n'est parcourue.
    """

    result = await db.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
        .where(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.actif.is_(True),
            Role.actif.is_(True),
            Permission.actif.is_(True),
        )
        .distinct()
        .order_by(Permission.code.asc())
    )
    return [row[0] for row in result.all()]


async def resolve_authz_version(db: AsyncSession, user_id: int) -> Optional[str]:
    """Retourne la date ISO de la derniere modification d.authorite du compte.

    Cette valeur est exposee par ``/auth/me`` pour qu'un client puisse
    invalider son cache de permissions sans recharger la liste complete.  Elle
    vaut ``None`` tant qu'aucune affectation dynamique n'existe.
    """

    assignments_max = (
        select(func.max(UserRoleAssignment.updated_at))
        .where(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.actif.is_(True),
        )
        .scalar_subquery()
    )
    roles_max = (
        select(func.max(Role.updated_at))
        .select_from(Role)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
        .where(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.actif.is_(True),
            Role.actif.is_(True),
        )
        .scalar_subquery()
    )
    grants_max = (
        select(func.max(RolePermission.updated_at))
        .select_from(RolePermission)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == RolePermission.role_id)
        .where(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.actif.is_(True),
        )
        .scalar_subquery()
    )
    permissions_max = (
        select(func.max(Permission.updated_at))
        .select_from(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == RolePermission.role_id)
        .where(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.actif.is_(True),
            Permission.actif.is_(True),
        )
        .scalar_subquery()
    )

    row = (
        await db.execute(
            select(assignments_max, roles_max, grants_max, permissions_max)
        )
    ).one()
    candidates = [value for value in row if value is not None]
    if not candidates:
        return None
    return max(candidates).isoformat()


async def effective_permissions(
    db: AsyncSession, user: Utilisateur | int
) -> EffectiveAuthorization:
    """Resout l'autorite effective d'un compte, sans heritage de roles."""

    user_id = user if isinstance(user, int) else user.id
    legacy_role = "" if isinstance(user, int) else (user.role or "")

    roles = await list_effective_role_codes(db, user_id)
    permissions = await list_effective_permission_codes(db, user_id)
    version = await resolve_authz_version(db, user_id)

    return EffectiveAuthorization(
        user_id=user_id,
        legacy_role=legacy_role,
        legacy_role_is_admin=(legacy_role or "").upper() == LEGACY_ADMIN_ROLE,
        role_codes=tuple(code for code, _label in roles),
        role_labels=tuple(label for _code, label in roles),
        permission_codes=tuple(permissions),
        permission_domains=tuple(
            dict.fromkeys(code.partition(".")[0] for code in permissions)
        ),
        authz_version=version,
    )


async def role_permission_codes(db: AsyncSession, role_id: int) -> list[str]:
    """Codes de permissions accordes a un role, tries pour un JSON stable."""

    result = await db.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id, Permission.actif.is_(True))
        .order_by(Permission.code.asc())
    )
    return [row[0] for row in result.all()]


async def list_active_roles(db: AsyncSession) -> list[Role]:
    """Roles actifs, dans l'ordre d'affichage."""

    result = await db.execute(select(Role).order_by(Role.ordre.asc(), Role.code.asc()))
    return list(result.scalars().all())


def system_code_to_legacy_role(code: str) -> Optional[str]:
    """Projection legacy d'un role systeme (``None`` si non projete)."""

    return SYSTEM_CODE_TO_LEGACY_ROLE.get(code)


def legacy_role_to_system_code(legacy_role: str) -> Optional[str]:
    """Role systeme correspondant a un role legacy, s'il existe."""

    return LEGACY_ROLE_TO_SYSTEM_CODE.get((legacy_role or "").upper())


def is_system_role_code(code: str) -> bool:
    """Vrai si ``code`` designe un des six roles livres par la migration."""

    return code in SYSTEM_ROLE_CODES


def normalize_permission_codes(codes: Iterable[str]) -> list[str]:
    """Normalise, deduplique et trie une liste de codes de permissions."""

    return sorted({(code or "").strip().lower() for code in codes if (code or "").strip()})


def role_permission_map(
    roles: Sequence[Role], permissions_by_role: dict[int, list[str]]
) -> dict[str, list[str]]:
    """Construit la projection ``code de role -> permissions`` pour le JSON."""

    return {
        role.code: sorted(permissions_by_role.get(role.id, []))
        for role in roles
    }


__all__ = [
    "LEGACY_ADMIN_ROLE",
    "EffectiveAuthorization",
    "effective_permissions",
    "is_legacy_admin",
    "is_system_role_code",
    "legacy_role_to_system_code",
    "list_active_roles",
    "list_effective_permission_codes",
    "list_effective_role_codes",
    "normalize_permission_codes",
    "resolve_authz_version",
    "role_permission_codes",
    "role_permission_map",
    "system_code_to_legacy_role",
]
