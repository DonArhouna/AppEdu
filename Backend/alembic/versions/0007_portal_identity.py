"""add explicit student account link for self-service portals

Revision ID: 0007_portal_identity
Revises: 0006_remove_implicit_defaults
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007_portal_identity"
down_revision: Union[str, None] = "0006_remove_implicit_defaults"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "utilisateurs",
        sa.Column("etudiant_id", sa.String(length=50), nullable=True),
    )
    op.create_index(
        op.f("ix_utilisateurs_etudiant_id"),
        "utilisateurs",
        ["etudiant_id"],
        unique=False,
    )
    with op.batch_alter_table("utilisateurs", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_utilisateurs_etudiant_id",
            "etudiants",
            ["etudiant_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # Reprise additive des instances legacy : aucun compte fictif n'est créé.
    # Le lien n'est renseigné que si un dossier réel porte exactement le même
    # email et si le compte a déjà le rôle étudiant.
    op.execute(
        """
        UPDATE utilisateurs
        SET etudiant_id = (
            SELECT etudiants.id
            FROM etudiants
            WHERE lower(etudiants.email) = lower(utilisateurs.email)
        )
        WHERE role = 'ETUDIANT'
          AND etudiant_id IS NULL
        """
    )


def downgrade() -> None:
    with op.batch_alter_table("utilisateurs", schema=None) as batch_op:
        batch_op.drop_constraint("fk_utilisateurs_etudiant_id", type_="foreignkey")
    op.drop_index(op.f("ix_utilisateurs_etudiant_id"), table_name="utilisateurs")
    op.drop_column("utilisateurs", "etudiant_id")
