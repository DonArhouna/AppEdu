"""add bulk student import (batches and rows)

Revision ID: 0014_etudiant_import
Revises: 0013_rbac_dynamic

Cette revision est **strictement additive** : deux tables, aucune colonne
existante modifiee, aucun backfill, aucun seed.

Le module d'import est en deux temps : ``analyse`` (aucune ecriture metier)
puis ``valider``.  Ces tables ne stockent que le diagnostic et le resultat ;
elles ne contiennent aucune donnee d'etudiant hors de ce que l'admin a
explicitement depose dans son fichier.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0014_etudiant_import"
down_revision: Union[str, None] = "0013_rbac_dynamic"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

#: JSON portable : JSONB sur PostgreSQL, JSON sur SQLite (tests E2E).
JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "etudiants_import_batches",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("nom_fichier", sa.String(length=255), nullable=False),
        sa.Column("format_source", sa.String(length=10), nullable=False),
        sa.Column("statut", sa.String(length=20), nullable=False),
        sa.Column("nb_lignes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nb_creer", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nb_mettre_a_jour", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nb_erreurs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nb_avertissements", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nb_importes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nb_ignorees", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("colonnes", JSON_TYPE, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("mode", sa.String(length=20), nullable=False, server_default="creation"),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("cree_par_id", sa.Integer(), nullable=True),
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
            ["cree_par_id"],
            ["utilisateurs.id"],
            ondelete="SET NULL",
            name="fk_etudiants_import_batches_cree_par",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_etudiants_import_batches_statut",
        "etudiants_import_batches",
        ["statut"],
        unique=False,
    )

    op.create_table(
        "etudiants_import_rows",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("batch_id", sa.String(length=36), nullable=False),
        sa.Column("ligne", sa.Integer(), nullable=False),
        sa.Column("statut", sa.String(length=20), nullable=False),
        sa.Column(
            "action", sa.String(length=20), nullable=False, server_default="aucune"
        ),
        sa.Column("donnees", JSON_TYPE, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("brut", JSON_TYPE, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("erreurs", JSON_TYPE, nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "avertissements", JSON_TYPE, nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column("matricule", sa.String(length=50), nullable=True),
        sa.Column("etudiant_id", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["etudiants_import_batches.id"],
            ondelete="CASCADE",
            name="fk_etudiants_import_rows_batch",
        ),
        sa.ForeignKeyConstraint(
            ["etudiant_id"],
            ["etudiants.id"],
            ondelete="SET NULL",
            name="fk_etudiants_import_rows_etudiant",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_etudiants_import_rows_batch",
        "etudiants_import_rows",
        ["batch_id"],
        unique=False,
    )
    op.create_index(
        "uq_etudiants_import_rows_batch_ligne",
        "etudiants_import_rows",
        ["batch_id", "ligne"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_etudiants_import_rows_batch_ligne", table_name="etudiants_import_rows")
    op.drop_index("ix_etudiants_import_rows_batch", table_name="etudiants_import_rows")
    op.drop_table("etudiants_import_rows")
    op.drop_index("ix_etudiants_import_batches_statut", table_name="etudiants_import_batches")
    op.drop_table("etudiants_import_batches")
