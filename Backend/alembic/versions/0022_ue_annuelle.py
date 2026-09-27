"""Enseignements annuels, et notes par semestre

Revision ID: 0022_ue_annuelle
Revises: 0021_bareme_mentions

Deux ajouts lies par la meme realite pedagogique : une matiere peut etre
**annuelle** — suivie sur toute l'annee, presente sur les deux semestres, et
**evaluee sur chacun**.

1. ``unites_enseignement.regime``, a deux valeurs :

   - ``semestrielle`` (defaut) — tout ce qui existe deja. L'UE ne compte que
     dans le semestre auquel elle est rattachee.
   - ``annuelle`` — l'UE se retrouve sur **tous** les semestres de la session.
     Le champ ``semestre_id`` n'a alors plus de sens pour elle, et n'est pas
     exige. Ses notes portent chacune leur semestre.

2. ``notes.semestre_id`` — sans lui, il est impossible de separer la note de
   S1 de celle de S2 pour une meme matiere annuelle : les deux iraient sur le
   meme bulletin, et le moteur les fusionnerait en une moyenne qui n'appartient
   a aucun semestre.

   La colonne est **nullable** et ne se deduit pas. La deduire de la date
   d'examen serait fiable chez un institut qui saisit ses dates de semestre, et
   silencieusement fausse chez celui qui ne le fait pas — or la creation d'une
   session ne renseigne aucune date. Deviner rendrait le bulletin dependant
   d'une donnee absente.

Ce que la migration ne decide pas, volontairement : la repartition des credits
d'une UE annuelle. Un institut peut la porter en entier sur chaque semestre
(3 + 3) ou la partager (1,5 + 1,5) ; les deux se lisent sur ses releves, et le
moteur additionne ce que l'institut a saisi. Le recapitulatif annuel, moyenne
ponderee des deux bulletins, reste juste dans les deux cas. Trancher ici
imposerait une pratique a un institut qui peut tres bien en avoir une autre.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0022_ue_annuelle"
down_revision: Union[str, None] = "0021_bareme_mentions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

REGIMES = ("semestrielle", "annuelle")
LONGUEUR = 20
CONTRAINTE = "ck_unites_enseignement_regime"


def upgrade() -> None:
    # 1. Le regime de l'UE.
    with op.batch_alter_table("unites_enseignement") as lot:
        lot.add_column(
            sa.Column(
                "regime",
                sa.String(length=LONGUEUR),
                nullable=False,
                server_default=REGIMES[0],
            )
        )
    # SQLite ne comprend pas ``ALTER TABLE ... ADD CONSTRAINT`` ; le
    # ``batch_alter_table`` se replie en recopiant la table, et reste une
    # reecriture d'operations simples sur PostgreSQL.
    with op.batch_alter_table("unites_enseignement") as lot:
        lot.create_check_constraint(
            CONTRAINTE,
            f"regime IN ({', '.join(repr(r) for r in REGIMES)})",
        )

    # 2. Le semestre d'une note.
    #
    # ``SET NULL`` et non ``CASCADE`` : supprimer un semestre ne doit pas
    # supprimer des notes. La note resterait orpheline, signalee, plutot que
    # detruite — c'est le meme choix que pour les UE.
    #
    # La cle est nommee : sur SQLite, ``batch_alter_table`` recree la table et
    # refuse une contrainte anonyme (« Constraint must have a name »).
    with op.batch_alter_table("notes") as lot:
        lot.add_column(
            sa.Column(
                "semestre_id",
                sa.String(length=50),
                sa.ForeignKey(
                    "semestres.id",
                    name="fk_notes_semestre_id",
                    ondelete="SET NULL",
                ),
                nullable=True,
            )
        )
    with op.batch_alter_table("notes") as lot:
        lot.create_index("ix_notes_semestre_id", ["semestre_id"], unique=False)

    # 3. ``unites_enseignement.semestre`` devient **nullable**.
    #
    # C'est l'etiquette d'affichage du semestre, et un enseignement annuel n'en
    # designe aucun : il en designe plusieurs. L'obliger a en saisir un
    # reviendrait a demander une fausse reponse pour obtenir un affichage — et
    # l'etiquette accompagnerait un rattachement que la lecture ignore.
    with op.batch_alter_table("unites_enseignement") as lot:
        lot.alter_column(
            "semestre", existing_type=sa.String(length=20), nullable=True
        )


def downgrade() -> None:
    liaison = op.get_bind()
    sans_etiquette = int(
        liaison.execute(
            sa.text("SELECT count(*) FROM unites_enseignement WHERE semestre IS NULL")
        ).scalar()
        or 0
    )
    if sans_etiquette:
        # L'ancien schema exigeait une etiquette de semestre et ne connaissait
        # pas l'enseignement annuel. Laisser planter sur une
        # ``NotNullViolation`` ne dirait pas *quoi* corriger ; le dire ici
        # evite un aller-retour.
        raise RuntimeError(
            f"Retrogradation impossible : {sans_etiquette} UE(s) n'ont pas "
            "d'étiquette de semestre (enseignements annuels). Passez-les en "
            "régime « semestrielle » et rattachez-les à un semestre avant de "
            "rétrograder."
        )

    with op.batch_alter_table("unites_enseignement") as lot:
        lot.alter_column(
            "semestre", existing_type=sa.String(length=20), nullable=False
        )
    with op.batch_alter_table("notes") as lot:
        lot.drop_index("ix_notes_semestre_id")
    with op.batch_alter_table("notes") as lot:
        lot.drop_column("semestre_id")
    with op.batch_alter_table("unites_enseignement") as lot:
        lot.drop_constraint(CONTRAINTE, type_="check")
    with op.batch_alter_table("unites_enseignement") as lot:
        lot.drop_column("regime")
