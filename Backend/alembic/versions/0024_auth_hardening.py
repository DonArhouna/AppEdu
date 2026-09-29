"""Durcissement de l'authentification : anti-brute-force et jetons de rafraichissement.

Revision ID: 0024_auth_hardening
Revises: 0023_financial_integrity

Deux mechanisms, tous les deux **additifs** : aucune donnee existante n'est
modifiee, supprimee ou reinterpretee. Une instance en production peut passer
cette revision sans interruption de service, et la retourner sans perte.

1. **Le login se defend.**  Jusqu'ici, ``POST /auth/login`` repondait a
   l'infini : un mot de passe pouvait etre devine lettre apres lettre, sans
   qu'aucune trace ne le signale. La table ``login_attempts`` conserve chaque
   tentative (adresse IP, email tente, issue), et ``utilisateurs`` porte deux
   colonnes de verrouillage : ``locked_until`` (le compte refuse les
   connexions jusqu'a cette date) et ``failed_login_count`` (le compteur
   d'echecs consécutifs, remonte a la reussite). Le seuil et la duree sont
   reglables, pas codes en dur.

2. **Une session peut etre revoquee.**  Jusqu'ici, un jeton volé restait
   valable huit heures : aucune porte existait pour le fermer. La table
   ``refresh_tokens`` conserve les jetons de rafraichissement emises — leur
   empreinte SHA-256, jamais le jeton lui-meme — et un access token ne vaut
   plus que si la session qui l'a emis est toujours vivante. Revoquer la
   session ferme l'acces **avant** l'expiration, et la rotation a chaque
   rafraichissement limite la fenetre d'exploitation d'un jeton intercepte.

Le downgrade detruit les deux tables et les colonnes : ce sont des donnees de
securite, pas des ecritures comptables. Les mots de passe, eux, ne bougent
pas — les hachages existants restent valides apres migration comme avant.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0024_auth_hardening"
down_revision: Union[str, None] = "0023_financial_integrity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- Le login se defend --------------------------------------------
    op.create_table(
        "login_attempts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # L'email **tente** peut ne correspondre a aucun compte : on le
        # conserve tel que saisi, c'est precisement lui qui interesse
        # l'investigation d'une attaque par dictionnaire.
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column(
            "resultat",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["utilisateurs.id"],
            name="fk_login_attempts_user_id",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_login_attempts_occurred_at", "login_attempts", ["occurred_at"]
    )
    op.create_index("ix_login_attempts_email", "login_attempts", ["email"])

    # Les colonnes de verrouillage vivent sur le compte : le verrou suit
    # l'utilisateur, pas la machine qui tente de se connecter en son nom.
    op.add_column(
        "utilisateurs",
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "utilisateurs",
        sa.Column(
            "failed_login_count", sa.Integer(), nullable=False,
            server_default=sa.text("0"),
        ),
    )

    # -- Une session peut etre revoquee ---------------------------------
    # L'empreinte, jamais le jeton : une base interceptee ne doit pas
    # contenir de quoi fabriquer une session valide.
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "revoked_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("revoked_reason", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["utilisateurs.id"],
            name="fk_refresh_tokens_user_id",
            ondelete="CASCADE",
        ),
        # La rotation fabrique a chaque rafraichissement une empreinte
        # nouvelle ; rejouer une empreinte deja remplacee est le signal
        # d'un vol, l'unicite ne doit donc pas s'y opposer.
        sa.Index("ix_refresh_tokens_token_hash", "token_hash"),
        sa.Index("ix_refresh_tokens_user_id", "user_id"),
    )


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    op.drop_column("utilisateurs", "failed_login_count")
    op.drop_column("utilisateurs", "locked_until")
    op.drop_index("ix_login_attempts_email", table_name="login_attempts")
    op.drop_index(
        "ix_login_attempts_occurred_at", table_name="login_attempts"
    )
    op.drop_table("login_attempts")
