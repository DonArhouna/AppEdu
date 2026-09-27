"""Semestres comme entites de premiere classe

Revision ID: 0020_semestres
Revises: 0019_matricule_nomenclature

``UniteEnseignement.semestre`` etait une **chaine libre** (``S1``..``S6``).
Trois consequences, toutes visibles a l'usage :

- rien ne garantissait qu'une UE designee ``S1`` et une autre ``S1`` soient
  le meme semestre — elles pouvaient etre saisies ``S1``, ``s1`` ou ``Semestre 1`` ;
- il n'y avait **aucune date** : impossible de situer une epreuve dans le
  temps, ni de cloturer une periode de notes ;
- un bulletin par semestre n'etait pas concevable, faute de perimetre.

``semestres`` devient une entite : un semestre appartient a une session, porte
un numero, un libelle et **ses dates**. L'UE s'y rattache par ``semestre_id``.

La colonne ``semestre`` (chaine) est **conservee** et devient le libelle
d'affichage ; elle n'est plus la source de structure. La migration reprend
l'etiquette existante dans le libelle du semestre cree, si bien que les deux
concordent des la premiere seconde.

Une reserve, assumee et signalee : une UE n'estrattachee **ni a une session ni
a une filiere** dans le schema actuel — il n'existe aucun lien session ↔
filiere. Le rattachement automatique des UE d'une instance qui aurait
plusieurs sessions est donc **impossible a faire correctement**, et le faire
mal serait pire que de ne pas le faire. La migration cree les semestres de
chaque session, et ne recable les UE que si l'instance n'a **qu'une seule**
session. Au-dela, les UE restent non rattachees, et l'ecran les signale.

``semestre_id`` reste **nullable** : un tiers des instituts n'ont qu'un seul
semestre, et les obliger a en creer deux pour saisir une UE les ferait saisir
n'importe quoi. Une UE sans semestre n'est pas invisible — elle est exclue du
bulletin, avec la raison, comme une matiere hors UE l'est du calcul de moyenne.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0020_semestres"
down_revision: Union[str, None] = "0019_matricule_nomenclature"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "semestres",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("session_id", sa.String(length=50), nullable=False),
        # L'ordre des semestres n'est pas un detail d'affichage : c'est lui qui
        # dit lequel precede l'autre.
        sa.Column("numero", sa.Integer(), nullable=False),
        # Ce que l'institut ecrit : « S1 », « Semestre 1 », « 1er semestre ».
        sa.Column("libelle", sa.String(length=50), nullable=False),
        sa.Column("date_debut", sa.Date(), nullable=True),
        sa.Column("date_fin", sa.Date(), nullable=True),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.true()),
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
            ["session_id"],
            ["sessions_academiques.id"],
            ondelete="CASCADE",
            name="fk_semestres_session",
        ),
        sa.PrimaryKeyConstraint("id"),
        # Un numero par session : deux « semestre 1 » dans la meme annee
        # rendraient la moyenne par semestre ambigue.
        sa.UniqueConstraint(
            "session_id", "numero", name="uq_semestres_session_numero"
        ),
    )
    op.create_index("ix_semestres_session", "semestres", ["session_id", "numero"])

    # SQLite ne sait pas ajouter une cle etrangere par ALTER : il faut le mode
    # batch, qui recopie la table. Il fonctionne tel quel sur PostgreSQL.
    with op.batch_alter_table("unites_enseignement") as batch:
        batch.add_column(
            sa.Column("semestre_id", sa.String(length=50), nullable=True)
        )
        batch.create_foreign_key(
            "fk_unites_enseignement_semestre",
            "semestres",
            ["semestre_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index(
        "ix_unites_enseignement_semestre",
        "unites_enseignement",
        ["semestre_id"],
    )

    liaison = op.get_bind()
    sessions = [
        row[0] for row in liaison.execute(sa.text("SELECT id FROM sessions_academiques"))
    ]
    if not sessions:
        # Instance neuve : rien a recabler. Les semestres seront crees avec la
        # session, depuis l'ecran.
        return

    # Deux semestres par session : le modele le plus courant en LMD. L'institut
    # renomme, ajoute ou retire un semestre depuis l'ecran ; on ne fige pas son
    # organisation pedagogique dans une migration.
    #
    # Les dates restent NULL : la session ne les porte pas de facon
    # exploitable, et inventer le debut d'un semestre serait pretendre connaitre
    # un calendrier que personne n'a saisi.
    for session_id in sessions:
        for numero in (1, 2):
            liaison.execute(
                sa.text(
                    "INSERT INTO semestres (id, session_id, numero, libelle, "
                    "date_debut, date_fin, actif, created_at, updated_at) "
                    "VALUES (:id, :session_id, :numero, :libelle, "
                    "NULL, NULL, true, now(), now())"
                ),
                {
                    "id": f"semestre-{session_id[:20]}-S{numero}",
                    "session_id": session_id,
                    "numero": numero,
                    "libelle": f"S{numero}",
                },
            )

    if len(sessions) > 1:
        # Plusieurs sessions : aucun lien ne permet de dire a laquelle une UE
        # appartient. On ne rattache rien plutot que de rattacher au hasard —
        # un semestre faux fausserait la moyenne et le bulletin.
        return

    # Une seule session : le rattachement est certain. La comparaison est
    # normalisee pour que « S1 », « s1 » et « S1 » aboutissent au meme semestre.
    liaison.execute(
        sa.text(
            "UPDATE unites_enseignement AS ue "
            "SET semestre_id = s.id "
            "FROM semestres AS s "
            "WHERE s.session_id = :session_id "
            "  AND upper(trim(ue.semestre)) = upper(trim(s.libelle))"
        ),
        {"session_id": sessions[0]},
    )


def downgrade() -> None:
    op.drop_index("ix_semestres_session", table_name="semestres")
    op.drop_index("ix_unites_enseignement_semestre", table_name="unites_enseignement")
    with op.batch_alter_table("unites_enseignement") as batch:
        batch.drop_constraint("fk_unites_enseignement_semestre", type_="foreignkey")
        batch.drop_column("semestre_id")
    op.drop_table("semestres")
