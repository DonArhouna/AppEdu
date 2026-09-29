"""Paiements en ligne : intention de paiement et confirmation.

Revision ID: 0027_paiement_intents
Revises: 0026_relances_email

Un paiement en ligne est un processus en deux temps, comme un guichet
differé : d'abord une **intention** — « cette facture peut etre payee, pour
tant, via ce lien » — puis la **confirmation** — « la famille a paye, la
caisse doit suivre ». Sans intention tracee, un lien partage ne dit ni qui
l'a emis, ni pour quoi, ni jusqu'a quand ; et une confirmation sans
intention serait un paiement que personne n'a demande.

La table ``paiement_intents`` porte les intentions :

- ``token_hash`` : **l'empreinte SHA-256 du jeton du lien, jamais le jeton**.
  Une base interceptee ne doit pas contenir de quoi payer a la place de la
  famille. Le lien complet vit uniquement dans la reponse de creation —
  l'instant ou le secretariat le transmet — jamais en base.
- ``montant`` : ce que l'intention autorise, fige a la creation. Une facture
  qui evolue ensuite n'elargit pas le lien deja emis.
- ``statut`` : ``en_attente`` (le lien attend), ``confirmee`` (payee, le
  paiement existe), ``annulee`` (retiree par le secretariat), ``expiree``
  (depassee, sans surprise).
- ``expires_le`` : un lien n'est pas eternel. L'echeance est un reglage ;
  par defaut sept jours, le temps qu'un paiement mobile aboutisse.

Le lien ne revele **rien** : aucun nom, aucun matricule, aucun montant avant
que le jeton ne soit presente au endpoint public. Un jeton devine donne
moins que rien, il donne « lien inconnu ».

Additif : une table nouvelle, aucune colonne posee ailleurs.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0027_paiement_intents"
down_revision: Union[str, None] = "0026_relances_email"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "paiement_intents",
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column(
            "facture_id",
            sa.String(length=50),
            sa.ForeignKey("factures.id", ondelete="CASCADE", name="fk_paiement_intents_facture_id"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "etudiant_id",
            sa.String(length=50),
            sa.ForeignKey("etudiants.id", ondelete="CASCADE", name="fk_paiement_intents_etudiant_id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "session_id",
            sa.String(length=50),
            sa.ForeignKey("sessions_academiques.id", ondelete="CASCADE", name="fk_paiement_intents_session_id"),
            nullable=False,
        ),
        sa.Column("periode_id", sa.String(length=50), nullable=True),
        # Ce que l'intention autorise, fige a la creation.
        sa.Column("montant", sa.Numeric(14, 2), nullable=False),
        sa.Column(
            # L'empreinte du jeton du lien : la base n'heurte jamais le jeton.
            "token_hash",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "statut",
            sa.String(length=20),
            nullable=False,
            server_default="en_attente",
        ),
        sa.Column("provider", sa.String(length=50), nullable=False, server_default="simulation"),
        sa.Column("expires_le", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "confirmee_le", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("paiement_id", sa.String(length=50), nullable=True),
        sa.Column(
            "creee_par_id",
            sa.Integer(),
            sa.ForeignKey(
                "utilisateurs.id", ondelete="SET NULL", name="fk_paiement_intents_creee_par_id"
            ),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_paiement_intents_token_hash", "paiement_intents", ["token_hash"]
    )


def downgrade() -> None:
    op.drop_index("ix_paiement_intents_token_hash", table_name="paiement_intents")
    op.drop_table("paiement_intents")
