"""harden security and add audit events

Revision ID: 0011_security_audit
Revises: 0010_admission_views
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0011_security_audit"
down_revision: Union[str, None] = "0010_admission_views"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    duplicates = connection.execute(
        sa.text(
            """
            SELECT etudiant_id, COUNT(*) AS total
            FROM utilisateurs
            WHERE etudiant_id IS NOT NULL
            GROUP BY etudiant_id
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()
    if duplicates:
        raise RuntimeError(
            "Des comptes utilisateurs partagent un même etudiant_id. "
            "La migration 0011 refuse d'appliquer une contrainte d'unicité."
        )

    op.drop_index("ix_utilisateurs_etudiant_id", table_name="utilisateurs")
    op.create_index(
        "uq_utilisateurs_etudiant_id",
        "utilisateurs",
        ["etudiant_id"],
        unique=True,
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("actor_email", sa.String(length=255), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=100), nullable=True),
        sa.Column("outcome", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["utilisateurs.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_events_occurred_at", "audit_events", ["occurred_at"], unique=False
    )
    op.create_index("ix_audit_events_actor_id", "audit_events", ["actor_id"], unique=False)
    op.create_index("ix_audit_events_action", "audit_events", ["action"], unique=False)
    op.create_index(
        "ix_audit_events_resource_type", "audit_events", ["resource_type"], unique=False
    )
    op.create_index(
        "ix_audit_events_resource_id", "audit_events", ["resource_id"], unique=False
    )

    with op.batch_alter_table("absences") as batch_op:
        batch_op.add_column(sa.Column("session_id", sa.String(length=50), nullable=True))
        batch_op.create_foreign_key(
            "fk_absences_session_id",
            "sessions_academiques",
            ["session_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index(
        "ix_absences_session_id", "absences", ["session_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_absences_session_id", table_name="absences")
    with op.batch_alter_table("absences") as batch_op:
        batch_op.drop_constraint("fk_absences_session_id", type_="foreignkey")
        batch_op.drop_column("session_id")

    op.drop_index("ix_audit_events_resource_id", table_name="audit_events")
    op.drop_index("ix_audit_events_resource_type", table_name="audit_events")
    op.drop_index("ix_audit_events_action", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_id", table_name="audit_events")
    op.drop_index("ix_audit_events_occurred_at", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_index("uq_utilisateurs_etudiant_id", table_name="utilisateurs")
    op.create_index(
        "ix_utilisateurs_etudiant_id", "utilisateurs", ["etudiant_id"], unique=False
    )
