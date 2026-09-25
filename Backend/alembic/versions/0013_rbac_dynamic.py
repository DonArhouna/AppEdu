"""add dynamic RBAC (permissions, roles, assignments)

Revision ID: 0013_rbac_dynamic
Revises: 0012_academic_structure

Cette revision est **strictement additive** : aucune colonne de ``utilisateurs``
n'est supprimee, ``utilisateurs.role`` reste la projection legacy lue par les
guards statiques existants, et ``utilisateurs.is_superuser`` n'est jamais
considere comme une autorite.

Ce que la migration cree (et rien d'autre) :

1. Quatre tables vides :

   - ``rbac_permissions``      : catalogue des permissions techniques
   - ``rbac_roles``            : roles dynamiques, sans heritage
   - ``rbac_role_permissions`` : grants allow-only permission -> role
   - ``rbac_user_roles``       : affectations role -> compte utilisateur

2. Le seed du catalogue, **idempotent** (une permission ou un role deja
   present n'est jamais reecrit) :

   - 14 permissions techniques issues de ``app.core.permissions``
     (``dashboard.read``, ``students.read``, ``students.write``,
     ``admissions.read``, ``admissions.write``, ``academic.read``,
     ``academic.write``, ``pedagogy.read``, ``pedagogy.write``,
     ``finance.read``, ``finance.write``, ``users.manage``,
     ``roles.manage``, ``audit.read``) ;
   - 6 roles systemes alignes sur la projection legacy : ``ROLE_ADMIN``,
     ``ROLE_DIRECTEUR_ETUDES``, ``ROLE_SECRETARIAT``, ``ROLE_COMPTABILITE``,
     ``ROLE_ENSEIGNANT``, ``ROLE_ETUDIANT``.

Ce que la migration ne fait **pas**, volontairement :

- elle n'accorde **aucune** permission a un role.  Une matrice role/permission
  serait une invention metier : les droits sont arbitres par un administrateur
  via ``PUT /api/v1/rbac/roles/{code}/permissions`` ;
- elle ne cree **aucun** compte utilisateur et ne rattache personne a un role ;
- elle ne modifie **aucune** ligne de ``utilisateurs``.

Le downgrade est refuse des qu'un role hors catalogue a ete cree : detruire
ces donnees serait une perte silencieuse.  Si seuls les six roles systemes et
le catalogue sont presents, le downgrade retire les quatre tables.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.core.permissions import PERMISSION_CATALOG, SYSTEM_ROLES


revision: str = "0013_rbac_dynamic"
down_revision: Union[str, None] = "0012_academic_structure"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Catalogue des permissions
    # ------------------------------------------------------------------
    op.create_table(
        "rbac_permissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("domaine", sa.String(length=50), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("libelle", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "systeme",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "actif",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_rbac_permissions_code", "rbac_permissions", ["code"], unique=True
    )
    op.create_index(
        "ix_rbac_permissions_domaine", "rbac_permissions", ["domaine"], unique=False
    )
    op.create_index(
        "ix_rbac_permissions_actif", "rbac_permissions", ["actif"], unique=False
    )

    # ------------------------------------------------------------------
    # 2. Roles dynamiques.  Aucun role n'herite d'un autre role : la seule
    #    source d'autorite est la table de grants ci-dessous.
    # ------------------------------------------------------------------
    op.create_table(
        "rbac_roles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("libelle", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "ordre", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "systeme",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "actif",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_rbac_roles_code", "rbac_roles", ["code"], unique=True)
    op.create_index("ix_rbac_roles_systeme", "rbac_roles", ["systeme"], unique=False)
    op.create_index("ix_rbac_roles_actif", "rbac_roles", ["actif"], unique=False)

    # ------------------------------------------------------------------
    # 3. Grants permission -> role (allow-only)
    # ------------------------------------------------------------------
    op.create_table(
        "rbac_role_permissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.Column("attribue_par", sa.Integer(), nullable=True),
        sa.Column("motif", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["rbac_roles.id"],
            ondelete="CASCADE",
            name="fk_rbac_role_permissions_role_id",
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["rbac_permissions.id"],
            ondelete="CASCADE",
            name="fk_rbac_role_permissions_permission_id",
        ),
        sa.ForeignKeyConstraint(
            ["attribue_par"],
            ["utilisateurs.id"],
            ondelete="SET NULL",
            name="fk_rbac_role_permissions_attribue_par",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "role_id", "permission_id", name="uq_rbac_role_permissions"
        ),
    )
    op.create_index(
        "ix_rbac_role_permissions_role_id",
        "rbac_role_permissions",
        ["role_id"],
        unique=False,
    )
    op.create_index(
        "ix_rbac_role_permissions_permission_id",
        "rbac_role_permissions",
        ["permission_id"],
        unique=False,
    )
    op.create_index(
        "ix_rbac_role_permissions_attribue_par",
        "rbac_role_permissions",
        ["attribue_par"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # 4. Affectations role -> compte utilisateur.  Cette table ne modifie
    #    jamais ``utilisateurs.role`` : la projection legacy reste ecrite
    #    uniquement par une action applicative explicite.
    # ------------------------------------------------------------------
    op.create_table(
        "rbac_user_roles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column(
            "actif", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("attribue_par", sa.Integer(), nullable=True),
        sa.Column("motif", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["utilisateurs.id"],
            ondelete="CASCADE",
            name="fk_rbac_user_roles_user_id",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["rbac_roles.id"],
            ondelete="CASCADE",
            name="fk_rbac_user_roles_role_id",
        ),
        sa.ForeignKeyConstraint(
            ["attribue_par"],
            ["utilisateurs.id"],
            ondelete="SET NULL",
            name="fk_rbac_user_roles_attribue_par",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "role_id", name="uq_rbac_user_roles"),
    )
    op.create_index(
        "ix_rbac_user_roles_user_id", "rbac_user_roles", ["user_id"], unique=False
    )
    op.create_index(
        "ix_rbac_user_roles_role_id", "rbac_user_roles", ["role_id"], unique=False
    )
    op.create_index(
        "ix_rbac_user_roles_attribue_par",
        "rbac_user_roles",
        ["attribue_par"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # 5. Seed idempotent du catalogue et des six roles systemes.
    #    Aucune permission n'est accordee et aucun compte n'est cree.
    # ------------------------------------------------------------------
    connection = op.get_bind()

    for definition in PERMISSION_CATALOG:
        deja_present = connection.execute(
            sa.text("SELECT 1 FROM rbac_permissions WHERE code = :code"),
            {"code": definition.code},
        ).scalar()
        if deja_present:
            continue
        connection.execute(
            sa.text(
                """
                INSERT INTO rbac_permissions
                    (code, domaine, action, libelle, description, systeme, actif)
                VALUES
                    (:code, :domaine, :action, :libelle, :description, TRUE, :actif)
                """
            ),
            {
                "code": definition.code,
                "domaine": definition.domaine,
                "action": definition.action,
                "libelle": definition.libelle,
                "description": definition.description,
                "actif": True,
            },
        )

    for definition in SYSTEM_ROLES:
        deja_present = connection.execute(
            sa.text("SELECT 1 FROM rbac_roles WHERE code = :code"),
            {"code": definition.code},
        ).scalar()
        if deja_present:
            continue
        connection.execute(
            sa.text(
                """
                INSERT INTO rbac_roles
                    (code, libelle, description, ordre, systeme, actif)
                VALUES
                    (:code, :libelle, :description, :ordre, TRUE, :actif)
                """
            ),
            {
                "code": definition.code,
                "libelle": definition.libelle,
                "description": definition.description,
                "ordre": definition.ordre,
                "actif": True,
            },
        )


def downgrade() -> None:
    # Une suppression de role hors catalogue detruirait une decision
    # d'autorite prise par un administrateur.  La downgrade est donc refusee
    # plutot que silencieusement destructive.
    connection = op.get_bind()
    roles_hors_catalogue = connection.execute(
        sa.text("SELECT COUNT(*) FROM rbac_roles WHERE systeme = 0")
    ).scalar()
    if roles_hors_catalogue:
        raise RuntimeError(
            "La downgrade 0013 est refusee : "
            f"{roles_hors_catalogue} role(s) dynamique(s) hors catalogue existent. "
            "Supprimez-les explicitement via DELETE /api/v1/rbac/roles/{code} "
            "avant de retrograder le schema."
        )

    for table_name, indexes in (
        (
            "rbac_user_roles",
            (
                "ix_rbac_user_roles_attribue_par",
                "ix_rbac_user_roles_role_id",
                "ix_rbac_user_roles_user_id",
            ),
        ),
        (
            "rbac_role_permissions",
            (
                "ix_rbac_role_permissions_attribue_par",
                "ix_rbac_role_permissions_permission_id",
                "ix_rbac_role_permissions_role_id",
            ),
        ),
        (
            "rbac_roles",
            (
                "ix_rbac_roles_actif",
                "ix_rbac_roles_systeme",
                "uq_rbac_roles_code",
            ),
        ),
        (
            "rbac_permissions",
            (
                "ix_rbac_permissions_actif",
                "ix_rbac_permissions_domaine",
                "uq_rbac_permissions_code",
            ),
        ),
    ):
        for index_name in indexes:
            op.drop_index(index_name, table_name=table_name)
        op.drop_table(table_name)
