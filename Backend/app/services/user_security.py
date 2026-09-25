"""Invariants de sécurité pour l'administration des utilisateurs."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.utilisateur import Utilisateur, UserRole


class LastActiveAdministratorError(RuntimeError):
    """Levée lorsqu'une opération supprimerait le dernier administrateur actif."""


async def assert_not_last_active_administrator(
    db: AsyncSession,
    target: Utilisateur,
    *,
    target_role: str | None = None,
    target_is_active: bool | None = None,
) -> None:
    """Verrouille les administrateurs actifs avant de retirer son accès.

    Le verrou est trié par identifiant afin que deux opérations concurrentes
    ne puissent pas supprimer simultanément les deux derniers administrateurs.
    Sur PostgreSQL, ``FOR UPDATE`` sérialise la vérification jusqu'au commit de la
    transaction appelante.
    """

    if target.role != UserRole.ADMIN.value or not target.is_active:
        return

    next_role = target_role if target_role is not None else target.role
    next_is_active = target_is_active if target_is_active is not None else target.is_active
    if next_role == UserRole.ADMIN.value and next_is_active:
        return

    result = await db.execute(
        select(Utilisateur.id)
        .where(
            Utilisateur.role == UserRole.ADMIN.value,
            Utilisateur.is_active.is_(True),
        )
        .order_by(Utilisateur.id)
        .with_for_update()
    )
    active_admin_ids = list(result.scalars().all())
    if len(active_admin_ids) <= 1:
        raise LastActiveAdministratorError(
            "Le dernier administrateur actif ne peut pas être rétrogradé, "
            "désactivé ou supprimé."
        )
