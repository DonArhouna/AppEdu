"""
RBAC dynamique : permissions, roles, et leurs affectations.

Le modele est strictement additif et coexiste avec la colonne legacy
``utilisateurs.role`` :

- ``utilisateurs.role`` reste la projection historique utilisee par les guards
  statiques existants.  Elle n'est jamais lue comme une autorite.
- Les tables ci-dessous portent l'autorisation dynamique reelle : un role
  dynamique ne herite d'aucun autre role et n'accorde que les permissions
  explicitement associees (modele allow-only, sans heritage ni negation).

Aucun compte utilisateur n'est cree par ce module.  La resolution d'autorite
vit dans ``app/services/rbac_service.py``.
"""

from typing import List, Optional

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Permission(Base, TimestampMixin):
    """Permission technique du catalogue (``domaine.action``).

    Les entrees du catalogue livrees par la migration portent ``systeme=True``
    : leur code est immuable et leur suppression est refusee.  Une permission
    ajoutee par un administrateur porte ``systeme=False``.
    """

    __tablename__ = "rbac_permissions"
    __table_args__ = (
        Index("uq_rbac_permissions_code", "code", unique=True),
        Index("ix_rbac_permissions_domaine", "domaine", unique=False),
        Index("ix_rbac_permissions_actif", "actif", unique=False),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Le code est immuable : il est reference par les grants et par le frontend.
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    domaine: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    # ``libelle``/``description`` sont des metadonnees d'interface.
    libelle: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    systeme: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    actif: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )

    role_links: Mapped[List["RolePermission"]] = relationship(
        "RolePermission",
        back_populates="permission",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Permission code={self.code!r} systeme={self.systeme} actif={self.actif}>"


class Role(Base, TimestampMixin):
    """Role dynamique, sans heritage.

    Une permission n'est accordee a un role que par une ligne de
    ``rbac_role_permissions``.  Aucun role parent, aucune hierarchie, aucune
    hierarchie de privileges implicite.
    """

    __tablename__ = "rbac_roles"
    __table_args__ = (
        Index("uq_rbac_roles_code", "code", unique=True),
        Index("ix_rbac_roles_systeme", "systeme", unique=False),
        Index("ix_rbac_roles_actif", "actif", unique=False),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Identifiant technique stable du role (existant des la migration).
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    libelle: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ordre: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    # ``systeme=True`` : role livre par la migration, protege contre la
    # suppression.  La desactivation reste possible.
    systeme: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    actif: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )

    permission_links: Mapped[List["RolePermission"]] = relationship(
        "RolePermission",
        back_populates="role",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    user_links: Mapped[List["UserRoleAssignment"]] = relationship(
        "UserRoleAssignment",
        back_populates="role",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Role code={self.code!r} systeme={self.systeme} actif={self.actif}>"


class RolePermission(Base, TimestampMixin):
    """Affectation d'une permission a un role (grants allow-only)."""

    __tablename__ = "rbac_role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_rbac_role_permissions"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rbac_roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    permission_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rbac_permissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attribue_par: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("utilisateurs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    motif: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    role: Mapped["Role"] = relationship("Role", back_populates="permission_links")
    permission: Mapped["Permission"] = relationship(
        "Permission", back_populates="role_links"
    )

    def __repr__(self) -> str:
        return f"<RolePermission role_id={self.role_id} permission_id={self.permission_id}>"


class UserRoleAssignment(Base, TimestampMixin):
    """Affectation d'un role dynamique a un compte utilisateur.

    Le nom de la classe differe volontairement de l'enumeration legacy
    ``UserRole`` de ``app.models.utilisateur`` afin d'eviter toute collision
    d'import.  La table ne modifie jamais ``utilisateurs.role`` : cette
    projection legacy est/ecrite uniquement par une action explicite.
    """

    __tablename__ = "rbac_user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_rbac_user_roles"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("utilisateurs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rbac_roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actif: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    attribue_par: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("utilisateurs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    motif: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Aucune relation ORM vers ``Utilisateur`` n'est declaree ici : le module
    # reste independant de l'ordre d'import des modeles et evite les ambiguites
    # de cle etrangere (``user_id`` et ``attribue_par`` pointent la meme table).
    # La lecture se fait par requete explicite dans ``app.services.rbac_service``.
    role: Mapped["Role"] = relationship("Role", back_populates="user_links")

    def __repr__(self) -> str:
        return f"<UserRoleAssignment user_id={self.user_id} role_id={self.role_id}>"


__all__ = ["Permission", "Role", "RolePermission", "UserRoleAssignment"]
