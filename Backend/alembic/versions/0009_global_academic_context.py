"""add the persisted global academic context

Revision ID: 0009_global_academic_context
Revises: 0008_admissions_workflow
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0009_global_academic_context"
down_revision: Union[str, None] = "0008_admissions_workflow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "etablissements",
        sa.Column("annee_academique_active", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "etablissements",
        sa.Column("session_active_id", sa.String(length=50), nullable=True),
    )
    op.create_index(
        op.f("ix_etablissements_session_active_id"),
        "etablissements",
        ["session_active_id"],
        unique=False,
    )
    with op.batch_alter_table("etablissements", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_etablissements_session_active_id",
            "sessions_academiques",
            ["session_active_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # Reprise additive : si une instance possède déjà une session active,
    # le contexte est initialisé à partir de données réelles, jamais d'une
    # année fictive. Les instances sans session restent configurables.
    bind = op.get_bind()
    active_session = bind.execute(
        sa.text(
            """
            SELECT id, annee_academique
            FROM sessions_academiques
            WHERE statut = :active
            ORDER BY date_debut DESC, created_at DESC
            LIMIT 1
            """
        ),
        {"active": "active"},
    ).mappings().first()
    if active_session:
        bind.execute(
            sa.text(
                """
                UPDATE etablissements
                SET annee_academique_active = :annee,
                    session_active_id = :session_id
                WHERE annee_academique_active IS NULL
                """
            ),
            {
                "annee": active_session["annee_academique"],
                "session_id": active_session["id"],
            },
        )


def downgrade() -> None:
    with op.batch_alter_table("etablissements", schema=None) as batch_op:
        batch_op.drop_constraint("fk_etablissements_session_active_id", type_="foreignkey")
    op.drop_index(
        op.f("ix_etablissements_session_active_id"),
        table_name="etablissements",
    )
    op.drop_column("etablissements", "session_active_id")
    op.drop_column("etablissements", "annee_academique_active")
