"""add saved admissions views

Revision ID: 0010_admission_views
Revises: 0009_global_academic_context
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0010_admission_views"
down_revision: Union[str, None] = "0009_global_academic_context"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vues_admissions",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("nom", sa.String(length=100), nullable=False),
        sa.Column("filtres", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["utilisateurs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "nom", name="uq_vues_admissions_user_nom"),
    )
    op.create_index(
        op.f("ix_vues_admissions_user_id"),
        "vues_admissions",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_vues_admissions_user_id"), table_name="vues_admissions")
    op.drop_table("vues_admissions")
