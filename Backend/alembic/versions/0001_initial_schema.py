"""initial_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-08 15:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Etablissements
    op.create_table(
        "etablissements",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("nom", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("adresse", sa.String(length=255), nullable=True),
        sa.Column("telephone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("site_web", sa.String(length=255), nullable=True),
        sa.Column("devise", sa.String(length=10), nullable=False, server_default="FCFA"),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("license_key", sa.String(length=255), nullable=True),
        sa.Column("is_configured", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_etablissements_code"), "etablissements", ["code"], unique=True)

    # 2. Utilisateurs
    op.create_table(
        "utilisateurs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("nom", sa.String(length=100), nullable=False),
        sa.Column("prenom", sa.String(length=100), nullable=False),
        sa.Column("telephone", sa.String(length=50), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="ADMIN"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_utilisateurs_email"), "utilisateurs", ["email"], unique=True)

    # 3. Sessions Académiques
    op.create_table(
        "sessions_academiques",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("nom", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("annee_academique", sa.String(length=20), nullable=False, server_default="2025-2026"),
        sa.Column("date_debut", sa.Date(), nullable=False),
        sa.Column("date_fin", sa.Date(), nullable=False),
        sa.Column("statut", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sessions_academiques_code"), "sessions_academiques", ["code"], unique=True)

    # 4. Périodes de Paiement
    op.create_table(
        "periodes_paiement",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("session_id", sa.String(length=50), nullable=False),
        sa.Column("nom", sa.String(length=100), nullable=False),
        sa.Column("mois", sa.String(length=30), nullable=False),
        sa.Column("date_echeance", sa.Date(), nullable=True),
        sa.Column("montant_estime", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("pourcentage", sa.Float(), nullable=True),
        sa.Column("ordre", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions_academiques.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 5. Etudiants
    op.create_table(
        "etudiants",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("matricule", sa.String(length=50), nullable=False),
        sa.Column("nom", sa.String(length=100), nullable=False),
        sa.Column("prenom", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("telephone", sa.String(length=50), nullable=True),
        sa.Column("date_naissance", sa.Date(), nullable=True),
        sa.Column("filiere", sa.String(length=100), nullable=False),
        sa.Column("niveau", sa.String(length=50), nullable=False),
        sa.Column("statut", sa.String(length=30), nullable=False, server_default="Inscrit"),
        sa.Column("photo_url", sa.String(length=500), nullable=True),
        sa.Column("session_id", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions_academiques.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_etudiants_matricule"), "etudiants", ["matricule"], unique=True)
    op.create_index(op.f("ix_etudiants_email"), "etudiants", ["email"], unique=True)
    op.create_index(op.f("ix_etudiants_session_id"), "etudiants", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_etudiants_session_id"), table_name="etudiants")
    op.drop_index(op.f("ix_etudiants_email"), table_name="etudiants")
    op.drop_index(op.f("ix_etudiants_matricule"), table_name="etudiants")
    op.drop_table("etudiants")

    op.drop_table("periodes_paiement")

    op.drop_index(op.f("ix_sessions_academiques_code"), table_name="sessions_academiques")
    op.drop_table("sessions_academiques")

    op.drop_index(op.f("ix_utilisateurs_email"), table_name="utilisateurs")
    op.drop_table("utilisateurs")

    op.drop_index(op.f("ix_etablissements_code"), table_name="etablissements")
    op.drop_table("etablissements")
