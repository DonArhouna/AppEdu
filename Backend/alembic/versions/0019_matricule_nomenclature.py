"""Nomenclature de matricule parametrable par l'etablissement

Revision ID: 0019_matricule_nomenclature
Revises: 0018_relances_facturation

Le matricule etait produit par une regle codee en dur dans
``matricule_service`` : ``{annee}-{code_filiere}-{0001}``. Un institut ne
pouvait ni changer le separateur, ni la largeur du compteur, ni l'ordre des
parties. Le parametre existe desormais.

Le choix d'un **modele** plutot que d'une liste de booleens (``avec_annee``,
``avec_filiere``, ``separateur``…) est delibere : un modele se lit, se
documente et couvre les cas qu'on n'a pas prevus. ``{annee}-{filiere}-{numero}``
reproduit exactement le comportement actuel — la migration ne change rien pour
une instance deja en service.

La ligne est creee pour tout etablissement deja configure. Sur une instance
neuve, la migration n'a pas d'etablissement a viser : la ligne sera creee a la
premiere lecture, avec les valeurs par defaut, qui sont deja le comportement
historique. Aucun seed de donnee n'est donc necessaire ici.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0019_matricule_nomenclature"
down_revision: Union[str, None] = "0018_relances_facturation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

#: Reproduit la regle codee en dur d'avant cette migration.
MODELE_DEPART = "{annee}-{filiere}-{numero}"
LARGEUR_DEPART = 4
DEMARRAGE_DEPART = 1


def upgrade() -> None:
    op.create_table(
        "parametres_matricule",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("etablissement_id", sa.String(length=50), nullable=False),
        # Modele du matricule. Seul {numero} est obligatoire : sans lui, il n'y
        # a pas de compteur, seulement un prefixe — deux etudiants porteraient
        # alors le meme matricule.
        sa.Column("modele", sa.String(length=120), nullable=False),
        # Nombre de chiffres du compteur : 4 donne 0001.
        sa.Column("largeur_numero", sa.Integer(), nullable=False, server_default="4"),
        # Premier numero attribue. Permet a un institut de reprendre a 1000.
        sa.Column("demarrage", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("maj_par_id", sa.Integer(), nullable=True),
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
            ["etablissement_id"],
            ["etablissements.id"],
            ondelete="CASCADE",
            name="fk_parametres_matricule_etablissement",
        ),
        sa.ForeignKeyConstraint(
            ["maj_par_id"],
            ["utilisateurs.id"],
            ondelete="SET NULL",
            name="fk_parametres_matricule_maj_par",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "etablissement_id", name="uq_parametres_matricule_etablissement"
        ),
    )

    # L'identifiant de l'etablissement n'est pas connu a la redaction de la
    # migration : on interroge la base au moment de l'application, comme pour
    # le reglement de deliberation.
    table = sa.table(
        "parametres_matricule",
        sa.column("id", sa.String(length=36)),
        sa.column("etablissement_id", sa.String(length=50)),
        sa.column("modele", sa.String(length=120)),
        sa.column("largeur_numero", sa.Integer()),
        sa.column("demarrage", sa.Integer()),
    )
    liaison = op.get_bind()
    etablissements = [
        row[0]
        for row in liaison.execute(
            sa.text("SELECT id FROM etablissements WHERE is_configured = TRUE")
        )
    ]
    if etablissements:
        op.bulk_insert(
            table,
            [
                {
                    "id": f"matricule-{etablissement_id[:24]}",
                    "etablissement_id": etablissement_id,
                    "modele": MODELE_DEPART,
                    "largeur_numero": LARGEUR_DEPART,
                    "demarrage": DEMARRAGE_DEPART,
                }
                for etablissement_id in etablissements
            ],
        )


def downgrade() -> None:
    op.drop_table("parametres_matricule")
