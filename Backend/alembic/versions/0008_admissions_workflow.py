"""add persistent admissions workflow

Revision ID: 0008_admissions_workflow
Revises: 0007_portal_identity
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008_admissions_workflow"
down_revision: Union[str, None] = "0007_portal_identity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "candidatures",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("reference", sa.String(length=50), nullable=False),
        sa.Column("nom", sa.String(length=100), nullable=False),
        sa.Column("prenom", sa.String(length=100), nullable=False),
        sa.Column("sexe", sa.String(length=10), nullable=True),
        sa.Column("date_naissance", sa.Date(), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("telephone", sa.String(length=50), nullable=True),
        sa.Column("adresse", sa.String(length=500), nullable=True),
        sa.Column("filiere_id", sa.String(length=50), nullable=False),
        sa.Column("niveau", sa.String(length=50), nullable=False),
        sa.Column("session_id", sa.String(length=50), nullable=True),
        sa.Column("statut", sa.String(length=30), nullable=False),
        sa.Column("date_demande", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("etudiant_id", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["filiere_id"], ["filieres.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions_academiques.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["utilisateurs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["etudiant_id"], ["etudiants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_candidatures_reference"), "candidatures", ["reference"], unique=True)
    op.create_index(op.f("ix_candidatures_email"), "candidatures", ["email"], unique=False)
    op.create_index(op.f("ix_candidatures_filiere_id"), "candidatures", ["filiere_id"], unique=False)
    op.create_index(op.f("ix_candidatures_session_id"), "candidatures", ["session_id"], unique=False)
    op.create_index(op.f("ix_candidatures_statut"), "candidatures", ["statut"], unique=False)
    op.create_index(op.f("ix_candidatures_created_by_id"), "candidatures", ["created_by_id"], unique=False)
    op.create_index(op.f("ix_candidatures_etudiant_id"), "candidatures", ["etudiant_id"], unique=True)

    op.create_table(
        "pieces_candidature",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("candidature_id", sa.String(length=50), nullable=False),
        sa.Column("type", sa.String(length=100), nullable=False),
        sa.Column("nom_fichier", sa.String(length=255), nullable=True),
        sa.Column("chemin_stockage", sa.String(length=500), nullable=True),
        sa.Column("statut", sa.String(length=30), nullable=False),
        sa.Column("date_depot", sa.DateTime(timezone=True), nullable=True),
        sa.Column("commentaire", sa.Text(), nullable=True),
        sa.Column("valide_par_id", sa.Integer(), nullable=True),
        sa.Column("date_validation", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["candidature_id"], ["candidatures.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["valide_par_id"], ["utilisateurs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pieces_candidature_candidature_id"), "pieces_candidature", ["candidature_id"], unique=False)
    op.create_index(op.f("ix_pieces_candidature_statut"), "pieces_candidature", ["statut"], unique=False)

    op.create_table(
        "decisions_admission",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("candidature_id", sa.String(length=50), nullable=False),
        sa.Column("decision", sa.String(length=30), nullable=False),
        sa.Column("motif", sa.Text(), nullable=True),
        sa.Column("decisionnaire_id", sa.Integer(), nullable=False),
        sa.Column("date_decision", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["candidature_id"], ["candidatures.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decisionnaire_id"], ["utilisateurs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_decisions_admission_candidature_id"), "decisions_admission", ["candidature_id"], unique=False)
    op.create_index(op.f("ix_decisions_admission_decisionnaire_id"), "decisions_admission", ["decisionnaire_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_decisions_admission_decisionnaire_id"), table_name="decisions_admission")
    op.drop_index(op.f("ix_decisions_admission_candidature_id"), table_name="decisions_admission")
    op.drop_table("decisions_admission")

    op.drop_index(op.f("ix_pieces_candidature_statut"), table_name="pieces_candidature")
    op.drop_index(op.f("ix_pieces_candidature_candidature_id"), table_name="pieces_candidature")
    op.drop_table("pieces_candidature")

    op.drop_index(op.f("ix_candidatures_etudiant_id"), table_name="candidatures")
    op.drop_index(op.f("ix_candidatures_created_by_id"), table_name="candidatures")
    op.drop_index(op.f("ix_candidatures_statut"), table_name="candidatures")
    op.drop_index(op.f("ix_candidatures_session_id"), table_name="candidatures")
    op.drop_index(op.f("ix_candidatures_filiere_id"), table_name="candidatures")
    op.drop_index(op.f("ix_candidatures_email"), table_name="candidatures")
    op.drop_index(op.f("ix_candidatures_reference"), table_name="candidatures")
    op.drop_table("candidatures")
