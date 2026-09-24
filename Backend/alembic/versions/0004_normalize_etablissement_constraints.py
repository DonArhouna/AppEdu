"""Normaliser les contraintes du modèle Etablissement.

Revision ID: 0004_normalize_etablissement
Revises: 0003_align_etablissement
Create Date: 2026-09-23

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_normalize_etablissement"
down_revision: Union[str, None] = "0003_align_etablissement"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ne jamais inventer une coordonnée institutionnelle. Si une ancienne base
    # contient une valeur nulle, la contrainte doit échouer et exiger une
    # correction explicite avant de poursuivre.
    with op.batch_alter_table("etablissements", schema=None) as batch_op:
        batch_op.alter_column(
            "email",
            existing_type=sa.String(length=255),
            type_=sa.String(length=255),
            existing_nullable=True,
            nullable=False,
        )
        batch_op.alter_column(
            "telephone",
            existing_type=sa.String(length=50),
            type_=sa.String(length=50),
            existing_nullable=True,
            nullable=False,
        )
        batch_op.alter_column(
            "devise",
            existing_type=sa.String(length=20),
            type_=sa.String(length=10),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("etablissements", schema=None) as batch_op:
        batch_op.alter_column(
            "email",
            existing_type=sa.String(length=255),
            type_=sa.String(length=255),
            existing_nullable=False,
            nullable=True,
        )
        batch_op.alter_column(
            "telephone",
            existing_type=sa.String(length=50),
            type_=sa.String(length=50),
            existing_nullable=False,
            nullable=True,
        )
        batch_op.alter_column(
            "devise",
            existing_type=sa.String(length=10),
            type_=sa.String(length=20),
            existing_nullable=False,
        )
