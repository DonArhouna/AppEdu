"""add invoice follow-up (dunning) tracking

Revision ID: 0018_relances_facturation
Revises: 0017_deliberation_pv

La balance agee calcule les creances en retard, mais rien ne permet de
**suivre** ce qui a ete relance : aucune trace de qui a contacte quel
etudiant, quand, pour quel montant. Un secretariat qui relance trois fois
sans le savoir, ou qui relance apres un encaissement, n'a aucun moyen de le
savoir.

Cet increment ajoute un journal des relances :

- ``relances`` : une relance par etudiant, avec le **montant reclame au
  moment de la relance** et la liste des factures concernees, figee en JSON.
  On fige parce qu'une facture peut etre soldee depuis : sans instantane,
  l'historique afficherait aujourd'hui un montant que personne n'a reclame.

Ce qui n'est **pas** ajoute, et pourquoi :

- aucun envoi d'email ou de SMS. L'application n'a aucune identite de
  messagerie, et en inventer une produirait un systeme qui Pretend
  contacter l'etudiant sans le faire. La relance est un acte du
  secretariat, constate ici, pas un envoi automatique ;
- aucun bareme de relance automatique. Le moment d'une relance releve de la
  politique de l'etablissement, pas du code. Seuls le **niveau** (1re,
  2e, 3e relance) et l'anciennete sont calcules, a partir des faits
  enregistres.

Aucun seed : la premiere relance est un acte reel, jamais une donnee
prefabriquee.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0018_relances_facturation"
down_revision: Union[str, None] = "0017_deliberation_pv"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "relances",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("etudiant_id", sa.String(length=50), nullable=False),
        # La session rend la relance tracable dans le temps ; une dette
        # ancienne reste consultable apres le passage a la session suivante.
        sa.Column("session_id", sa.String(length=50), nullable=True),
        # 1re, 2e, 3e... sur la dette de cet etudiant. Calcule a partir des
        # relances deja enregistrees, jamais saisi.
        sa.Column("niveau", sa.Integer(), nullable=False),
        sa.Column("date_relance", sa.Date(), nullable=False),
        # Moyen constate : courrier, appel, guichet... Le libelle vient d'une
        # liste fermee, pas d'une saisie libre qui divergerait.
        sa.Column("moyen", sa.String(length=30), nullable=False),
        # Montant reclame ce jour-la, et detail des factures concernees.
        # Figes : une facture soldee depuis ne doit pas reecrire l'historique.
        sa.Column("montant_reclame", sa.Float(), nullable=False),
        sa.Column(
            "factures_concernees",
            JSON_TYPE,
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        # Jours de retard de la plus ancienne echeance au moment de la
        # relance : c'est l'anciennete qui justifie la relance.
        sa.Column("retard_jours", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message", sa.Text(), nullable=True),
        # Solde constate apres la relance. NULL tant qu'aucun encaissement
        # n'a suivi : une relance efficace n'est pas un solde sur du papier.
        sa.Column("solde_apres", sa.Float(), nullable=True),
        sa.Column("relance_par_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["etudiant_id"], ["etudiants.id"], ondelete="CASCADE",
            name="fk_relances_etudiant",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["sessions_academiques.id"], ondelete="SET NULL",
            name="fk_relances_session",
        ),
        sa.ForeignKeyConstraint(
            ["relance_par_id"], ["utilisateurs.id"], ondelete="SET NULL",
            name="fk_relances_relance_par",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Suivi d'un etudiant : l'historique et le prochain niveau se lisent par
    # etudiant, du plus ancien au plus recent.
    op.create_index(
        "ix_relances_etudiant",
        "relances",
        ["etudiant_id", "date_relance"],
    )
    # Vue « a relancer » : les creances les plus anciennes d'abord.
    op.create_index("ix_relances_date", "relances", ["date_relance"])


def downgrade() -> None:
    op.drop_index("ix_relances_date", table_name="relances")
    op.drop_index("ix_relances_etudiant", table_name="relances")
    op.drop_table("relances")
