"""add institutional configuration (versioned settings, logo, institution.settings)

Revision ID: 0016_configuration_institutionnelle
Revises: 0015_documents_officiels

Une instance doit etre configurable par son etablissement : identite
imprimable (nom, sigle, adresse, contacts, devise) et logo. Ces elements
apparaissent sur les documents officiels ; sans eux, un certificat n'est pas
exploitable.

Trois ajouts strictement additifs :

1. ``configuration_versions`` : journal des versions de la configuration. Une
   modification est un acte administratif comme un autre : on conserve qui a
   change quoi et quand, avec un instantane des valeurs avant ecriture. Cela
   permet de repondre a « le certificat de mars portait quel logo ? » et de
   revenir a une version anterieure.
2. La permission ``institution.settings`` : elle est delibrement distincte,
   pour qu'une direction puisse preparer un logo ou corriger une coordonnee
   sans ouvrir ``users.manage`` ni ``roles.manage``.  Elle ne remplace aucune
   permission existante et n'ouvre aucune route preexistante.
3. Aucun seed. La configuration initiale reste celle du Setup Wizard, a
   version 0. Les octets du logo restent hors PostgreSQL, dans
   ``storage/etablissement``.

Aucun document officiel n'est emis ni modifie par cette migration : la
version 1 d'une configuration n'est pas une raison de reemettre des
certificats deja delivres, qui gardent l'instantane de leur emission.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0016_config_institutionnelle"
down_revision: Union[str, None] = "0015_documents_officiels"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def _permission_institution_settings() -> sa.text:
    """INSERT idempotent de la permission, partage avec le module institution."""

    return sa.text(
        """
        INSERT INTO rbac_permissions (code, domaine, action, libelle, description, systeme, actif)
        SELECT :code, :domaine, :action, :libelle, :description, TRUE, TRUE
        WHERE NOT EXISTS (SELECT 1 FROM rbac_permissions WHERE code = :code)
        """
    )


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Journal des versions de la configuration institutionnelle
    # ------------------------------------------------------------------
    op.create_table(
        "configuration_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("etablissement_id", sa.String(length=50), nullable=False),
        # Numerotation sequentielle, unique par etablissement : deux versions
        # ne peuvent pas porter le meme numero, meme en emission concurrente.
        sa.Column("version", sa.Integer(), nullable=False),
        # 'etablissement' (identite) ou 'branding' (logo).
        sa.Column("nature", sa.String(length=30), nullable=False),
        # Champs modifies par cette version, avec leur valeur precedente.
        # C'est ce qui rend l'historique lisible sans reconstituer l'historique
        # complet a partir de toutes les versions.
        sa.Column("modifications", JSON_TYPE, nullable=False, server_default=sa.text("'{}'")),
        # Instantanе complet apres ecriture : permet de restaurer une version
        # sans rejouer la chronologie.
        sa.Column("instantane", JSON_TYPE, nullable=False, server_default=sa.text("'{}'")),
        # Le logo est-il present a cette version ? Permet de savoir si une
        # version anterieure avait un branding, meme si le fichier a disparu.
        sa.Column("logo_present", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("modifie_par_id", sa.Integer(), nullable=True),
        sa.Column("modifie_par_email", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["etablissement_id"], ["etablissements.id"], ondelete="CASCADE",
            name="fk_configuration_versions_etablissement",
        ),
        sa.ForeignKeyConstraint(
            ["modifie_par_id"], ["utilisateurs.id"], ondelete="SET NULL",
            name="fk_configuration_versions_modifie_par",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_configuration_versions_numero",
        "configuration_versions",
        ["etablissement_id", "version"],
        unique=True,
    )
    op.create_index(
        "ix_configuration_versions_etablissement",
        "configuration_versions",
        ["etablissement_id", "version"],
    )

    # ------------------------------------------------------------------
    # 2. Permission de configuration institutionnelle
    # ------------------------------------------------------------------
    op.execute(
        _permission_institution_settings()
        .bindparams(
            code="institution.settings",
            domaine="institution",
            action="settings",
            libelle="Configurer l'etablissement",
            description=(
                "Modifier l'identite institutionnelle et le logo utilises sur "
                "les documents officiels"
            ),
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM rbac_permissions WHERE code = :code").bindparams(
            code="institution.settings"
        )
    )
    op.drop_index("ix_configuration_versions_etablissement", table_name="configuration_versions")
    op.drop_index("uq_configuration_versions_numero", table_name="configuration_versions")
    op.drop_table("configuration_versions")
