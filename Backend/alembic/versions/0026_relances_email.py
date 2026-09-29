"""Envoi des lettres de relance par email : trace du resultat.

Revision ID: 0026_relances_email
Revises: 0025_salles

Jusqu'ici, une relance se **constatait** : le secretariat notait l'avoir
faite, par quel moyen. Le lot 4 ajoute un envoi reel — la lettre PDF parte
par email — mais l'acte reste humain et explicite : c'est le secretariat qui
decide d'envoyer, l'application ne previenne personne toute seule.

Deux colonnes conservent ce que l'envoi a donne : ``email_envoye_le`` (date
de la derniere tentative) et ``email_statut`` (``envoye``, ``simule`` ou
``echec``, avec le detail technique dans le journal d'audit). Un envoi
simule (SMTP non configure) se **dit** : l'application ne pretend jamais
avoir contacte un etudiant qu'elle n'a pas contacte.

Additif : deux colonnes nullables, aucun reclassement, downgrade inverse.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0026_relances_email"
down_revision: Union[str, None] = "0025_salles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "relances",
        sa.Column("email_envoye_le", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "relances",
        sa.Column("email_statut", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("relances", "email_statut")
    op.drop_column("relances", "email_envoye_le")
