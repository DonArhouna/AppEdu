"""add fee grids

Revision ID: 0005_add_fee_grids
Revises: 0004_normalize_etablissement_constraints
Create Date: 2026-09-23 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_add_fee_grids"
down_revision: Union[str, None] = "0004_normalize_etablissement"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "grilles_tarifaires",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("filiere_id", sa.String(length=50), nullable=True),
        sa.Column("filiere", sa.String(length=255), nullable=False),
        sa.Column("niveau", sa.String(length=100), nullable=False),
        sa.Column("droits_inscription", sa.Float(), nullable=False),
        sa.Column("scolarite_mensuelle", sa.Float(), nullable=False),
        sa.Column("nombre_mois", sa.Integer(), nullable=False),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["filiere_id"], ["filieres.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("filiere", "niveau", name="uq_grilles_tarifaires_filiere_niveau"),
    )
    op.create_index(
        op.f("ix_grilles_tarifaires_filiere_id"),
        "grilles_tarifaires",
        ["filiere_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_grilles_tarifaires_filiere_id"), table_name="grilles_tarifaires")
    op.drop_table("grilles_tarifaires")
