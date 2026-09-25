"""add normalized academic structure

Revision ID: 0012_academic_structure
Revises: 0011_security_audit

Cette revision est volontairement additive : elle ne seed aucun referentiel et
ne backfill aucune colonne legacy.  Les colonnes de liaison sur les eleves et
candidatures sont nullable afin de representer exactement l'etat existant.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0012_academic_structure"
down_revision: Union[str, None] = "0011_security_audit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_ACTIVE_INSCRIPTION_SQLITE_PREDICATE = "actif = 1"
_ACTIVE_INSCRIPTION_POSTGRESQL_PREDICATE = "actif IS TRUE"


def upgrade() -> None:
    # 1. Cycles et niveaux.  Aucune ligne n'est injectee ici : le modele LMD
    # ne peut etre charge que via son endpoint d'action explicite.
    op.create_table(
        "cycles",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("nom", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("ordre", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_cycles_code", "cycles", ["code"], unique=True
    )

    op.create_table(
        "niveaux",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("cycle_id", sa.String(length=50), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("nom", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("ordre", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["cycle_id"], ["cycles.id"], ondelete="RESTRICT", name="fk_niveaux_cycle_id"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cycle_id", "code", name="uq_niveaux_cycle_code"),
    )
    op.create_index("ix_niveaux_cycle_id", "niveaux", ["cycle_id"], unique=False)

    # 2. Classe = filiere + niveau.  La contrainte de couple est la source de
    # verite; l'index explicite est ensuite recreated par batch sur SQLite.
    op.create_table(
        "classes",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("filiere_id", sa.String(length=50), nullable=False),
        sa.Column("niveau_id", sa.String(length=50), nullable=False),
        sa.Column("nom", sa.String(length=150), nullable=True),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["filiere_id"], ["filieres.id"], ondelete="RESTRICT", name="fk_classes_filiere_id"
        ),
        sa.ForeignKeyConstraint(
            ["niveau_id"], ["niveaux.id"], ondelete="RESTRICT", name="fk_classes_niveau_id"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("filiere_id", "niveau_id", name="uq_classes_filiere_niveau"),
    )
    op.create_index("ix_classes_filiere_niveau", "classes", ["filiere_id", "niveau_id"], unique=False)
    op.create_index("ix_classes_filiere_id", "classes", ["filiere_id"], unique=False)
    op.create_index("ix_classes_niveau_id", "classes", ["niveau_id"], unique=False)

    # 3. Inscription.  Le predicat est un index partiel portable SQLite/PostgreSQL.
    op.create_table(
        "inscriptions",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("etudiant_id", sa.String(length=50), nullable=False),
        sa.Column("classe_id", sa.String(length=50), nullable=False),
        sa.Column("session_id", sa.String(length=50), nullable=False),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("statut", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("date_inscription", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["etudiant_id"], ["etudiants.id"], ondelete="RESTRICT", name="fk_inscriptions_etudiant_id"
        ),
        sa.ForeignKeyConstraint(
            ["classe_id"], ["classes.id"], ondelete="RESTRICT", name="fk_inscriptions_classe_id"
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["sessions_academiques.id"], ondelete="RESTRICT", name="fk_inscriptions_session_id"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_inscriptions_etudiant_session_active",
        "inscriptions",
        ["etudiant_id", "session_id"],
        unique=True,
        sqlite_where=sa.text(_ACTIVE_INSCRIPTION_SQLITE_PREDICATE),
        postgresql_where=sa.text(_ACTIVE_INSCRIPTION_POSTGRESQL_PREDICATE),
    )
    op.create_index("ix_inscriptions_etudiant_id", "inscriptions", ["etudiant_id"], unique=False)
    op.create_index("ix_inscriptions_classe_id", "inscriptions", ["classe_id"], unique=False)
    op.create_index("ix_inscriptions_session_id", "inscriptions", ["session_id"], unique=False)
    op.create_index("ix_inscriptions_statut", "inscriptions", ["statut"], unique=False)

    # 4. References optionnelles sur les entites legacy.  Les colonnes restent
    # nullable et les donnees existantes ne sont pas interpretees/backfillees.
    op.add_column(
        "etudiants", sa.Column("classe_id", sa.String(length=50), nullable=True)
    )
    with op.batch_alter_table("etudiants", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_etudiants_classe_id",
            "classes",
            ["classe_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    op.create_index("ix_etudiants_classe_id", "etudiants", ["classe_id"], unique=False)

    op.add_column(
        "candidatures", sa.Column("niveau_id", sa.String(length=50), nullable=True)
    )
    op.add_column(
        "candidatures", sa.Column("classe_id", sa.String(length=50), nullable=True)
    )
    with op.batch_alter_table("candidatures", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_candidatures_niveau_id",
            "niveaux",
            ["niveau_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_candidatures_classe_id",
            "classes",
            ["classe_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    op.create_index("ix_candidatures_niveau_id", "candidatures", ["niveau_id"], unique=False)
    op.create_index("ix_candidatures_classe_id", "candidatures", ["classe_id"], unique=False)


def downgrade() -> None:
    # Une downgrade ne doit jamais detruire une trace academique.  Si des
    # lignes ont deja ete creees, on refuse explicitement la suppression plutot
    # que de laisser une suppression partielle sur SQLite.
    bind = op.get_bind()
    for table_name in ("inscriptions", "classes", "niveaux", "cycles"):
        count = bind.execute(
            sa.text(f"SELECT COUNT(*) FROM {table_name}")
        ).scalar()
        if count:
            raise RuntimeError(
                f"La downgrade 0012 refuse de supprimer des donnees dans {table_name}."
            )
    for table_name, column_name in (
        ("etudiants", "classe_id"),
        ("candidatures", "niveau_id"),
        ("candidatures", "classe_id"),
    ):
        count = bind.execute(
            sa.text(
                f"SELECT COUNT(*) FROM {table_name} WHERE {column_name} IS NOT NULL"
            )
        ).scalar()
        if count:
            raise RuntimeError(
                f"La downgrade 0012 refuse de supprimer des references ({table_name}.{column_name})."
            )

    # Retirer les references avant les tables pour que la suppression reste
    # possible sur PostgreSQL comme sur SQLite.
    op.drop_index("ix_candidatures_classe_id", table_name="candidatures")
    op.drop_index("ix_candidatures_niveau_id", table_name="candidatures")
    with op.batch_alter_table("candidatures", schema=None) as batch_op:
        batch_op.drop_constraint("fk_candidatures_classe_id", type_="foreignkey")
        batch_op.drop_constraint("fk_candidatures_niveau_id", type_="foreignkey")
    op.drop_column("candidatures", "classe_id")
    op.drop_column("candidatures", "niveau_id")

    op.drop_index("ix_etudiants_classe_id", table_name="etudiants")
    with op.batch_alter_table("etudiants", schema=None) as batch_op:
        batch_op.drop_constraint("fk_etudiants_classe_id", type_="foreignkey")
    op.drop_column("etudiants", "classe_id")

    op.drop_index("ix_inscriptions_statut", table_name="inscriptions")
    op.drop_index("ix_inscriptions_session_id", table_name="inscriptions")
    op.drop_index("ix_inscriptions_classe_id", table_name="inscriptions")
    op.drop_index("ix_inscriptions_etudiant_id", table_name="inscriptions")
    op.drop_index("uq_inscriptions_etudiant_session_active", table_name="inscriptions")
    op.drop_table("inscriptions")

    op.drop_index("ix_classes_niveau_id", table_name="classes")
    op.drop_index("ix_classes_filiere_id", table_name="classes")
    op.drop_index("ix_classes_filiere_niveau", table_name="classes")
    op.drop_table("classes")

    op.drop_index("ix_niveaux_cycle_id", table_name="niveaux")
    op.drop_table("niveaux")

    op.drop_index("uq_cycles_code", table_name="cycles")
    op.drop_table("cycles")
