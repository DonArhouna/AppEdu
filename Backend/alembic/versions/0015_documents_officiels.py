"""add official documents (issuance register, branding, documents.issue)

Revision ID: 0015_documents_officiels
Revises: 0014_etudiant_import

Trois ajouts strictement additifs :

1. ``documents_officiels`` : registre d'emission. Un document officiel est un
   acte administratif ; l'etablissement doit pouvoir prouver ce qu'il a
   delivre, a qui, quand, par qui et sur la base de quelles donnees. Le PDF
   lui-meme reste sur le disque ; PostgreSQL ne conserve que le chemin
   relatif, l'empreinte SHA-256 et l'instantane des donnees.
2. ``etablissements.logo_url`` : premier element de la configuration
   institutionnelle. Sans branding, un certificat officiel n'est pas
   exploitable.
3. La permission ``documents.issue`` : elle permet de deleguer l'emission
   (secreariat) sans ouvrir l'ecriture sur les dossiers etudiants.

Aucun seed de document, aucune donnee metier ajoutee.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0015_documents_officiels"
down_revision: Union[str, None] = "0014_etudiant_import"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def _permission_documents_issue() -> sa.text:
    """INSERT idempotent de la permission, partage avec le seed 0013."""

    from app.core.document_types import PERMISSION_DOCUMENTS

    return sa.text(
        """
        INSERT INTO rbac_permissions (code, domaine, action, libelle, description, systeme, actif)
        SELECT :code, :domaine, :action, :libelle, :description, TRUE, TRUE
        WHERE NOT EXISTS (SELECT 1 FROM rbac_permissions WHERE code = :code)
        """
    )


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Branding de l'etablissement
    # ------------------------------------------------------------------
    op.add_column(
        "etablissements",
        sa.Column("logo_url", sa.String(length=500), nullable=True),
    )

    # ------------------------------------------------------------------
    # 2. Registre d'emission des documents officiels
    # ------------------------------------------------------------------
    op.create_table(
        "documents_officiels",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("type_document", sa.String(length=50), nullable=False),
        sa.Column("numero", sa.String(length=50), nullable=False),
        sa.Column("etudiant_id", sa.String(length=50), nullable=False),
        sa.Column("session_id", sa.String(length=50), nullable=True),
        sa.Column("annee", sa.Integer(), nullable=False),
        sa.Column("fichier", sa.String(length=500), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("taille_octets", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("donnees", JSON_TYPE, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("reserves", JSON_TYPE, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("remplace_document_id", sa.String(length=36), nullable=True),
        sa.Column("motif_duplicata", sa.Text(), nullable=True),
        sa.Column("emis_par_id", sa.Integer(), nullable=True),
        sa.Column("emis_le", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivre_le", sa.Date(), nullable=True),
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
            ["etudiant_id"], ["etudiants.id"], ondelete="CASCADE",
            name="fk_documents_officiels_etudiant",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["sessions_academiques.id"], ondelete="SET NULL",
            name="fk_documents_officiels_session",
        ),
        sa.ForeignKeyConstraint(
            ["remplace_document_id"], ["documents_officiels.id"], ondelete="SET NULL",
            name="fk_documents_officiels_remplace",
        ),
        sa.ForeignKeyConstraint(
            ["emis_par_id"], ["utilisateurs.id"], ondelete="SET NULL",
            name="fk_documents_officiels_emis_par",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_documents_officiels_numero",
        "documents_officiels",
        ["type_document", "numero"],
        unique=True,
    )
    op.create_index(
        "ix_documents_officiels_etudiant",
        "documents_officiels", ["etudiant_id"], unique=False,
    )
    op.create_index(
        "ix_documents_officiels_type",
        "documents_officiels", ["type_document"], unique=False,
    )

    # ------------------------------------------------------------------
    # 3. Permission documents.issue (idempotente)
    # ------------------------------------------------------------------
    op.execute(
        _permission_documents_issue().bindparams(
            code="documents.issue",
            domaine="documents",
            action="issue",
            libelle="Emettre les documents officiels",
            description=(
                "Generation des certificats de scolarite, releves de notes "
                "et quitus financiers."
            ),
        )
    )


def downgrade() -> None:
    # Le registre est une tracabilite administrative : sa suppression est
    # destructive. On retire la permission puis la table, comme le reste du
    # projet, mais l'operation reste signalee dans la documentation.
    op.execute(sa.text("DELETE FROM rbac_permissions WHERE code = 'documents.issue'"))
    op.drop_index("ix_documents_officiels_type", table_name="documents_officiels")
    op.drop_index("ix_documents_officiels_etudiant", table_name="documents_officiels")
    op.drop_index("uq_documents_officiels_numero", table_name="documents_officiels")
    op.drop_table("documents_officiels")
    op.drop_column("etablissements", "logo_url")
