"""Registre des écoles : la base de contrôle du multi-tenant.

Revision ID: 0028_tenant_registry
Revises: 0027_paiement_intents

Le multi-tenant (lot 6) distingue deux plans :

- la **base de contrôle** — ``DATABASE_URL``, celle que cette revision
  modifie — porte le registre des écoles : qui existe, où est sa base,
  quel est son statut d'abonnement ;
- chaque école dispose de **sa base** ``emp_tenant_{id}`` sur le même
  serveur, migrée indépendamment. L'isolation est physique : une fuite
  dans le code ne peut pas lire une autre école, une sauvegarde (ou une
  restitution RGPD) se fait base par base.

Cette table ne crée aucune base : le provisionneur lit ce registre et
fabrique les bases. Une instance ``standalone`` (le cas de toutes les
installations clientes actuelles) ignore simplement cette table.

Additif : une table nouvelle sur la base de contrôle uniquement.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0028_tenant_registry"
down_revision: Union[str, None] = "0027_paiement_intents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(length=50), primary_key=True),
        # L'identifiant court : il nomme la base (``emp_tenant_isi``) et
        # l'en-tête de résolution (``X-Tenant-ID: isi``).
        sa.Column("slug", sa.String(length=50), nullable=False, unique=True, index=True),
        sa.Column("nom", sa.String(length=255), nullable=False),
        # ``active`` (service normal), ``suspendue`` (impayé, lecture seule
        # côté provisionneur), ``resiliee`` (données conservées, accès fermé).
        sa.Column("statut", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("plan", sa.String(length=50), nullable=False, server_default="standard"),
        sa.Column("abonnement_jusquau", sa.Date(), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("tenants")
