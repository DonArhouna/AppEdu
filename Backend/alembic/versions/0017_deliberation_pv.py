"""add persisted deliberation (jury decisions, rules, attestation of success)

Revision ID: 0017_deliberation_pv
Revises: 0016_config_institutionnelle

La deliberation est aujourd'hui **calculee a la volee** et **jamais
enregistree**. Aucun proces-verbal, aucune date, aucun jury : c'est
volontiers, et c'est pourquoi ``document_types.py`` refuse d'emettre une
attestation de reussite. On ne peut pas attester ce qui n'est pas prouve.

Cet increment persiste la decision. Trois ajouts strictement additifs :

1. ``regles_deliberation`` : les regles de deliberation de l'etablissement.
   Les seuils existants (10/20, eliminatoire 7/20, compensation, 18 ECTS,
   mentions) etaient **codes en dur** et dupliques dans le frontend. Un
   reglement academique n'est pas une constante technique : il devient
   reglable, et l'institut declare l'avoir confirme. L'etat
   ``confirme_par`` distingue un reglement valide d'une valeur de depart
   jamais revue.

2. ``deliberations`` : une seance de jury pour une promotion (classe +
   session), avec sa date, son lieu, son president et ses membres. Les
   regles en vigueur sont **figees** dans la seance : changer le reglement
   plus tard ne doit pas reecrire l'historique d'un jury deja tenu.

3. ``deliberation_decisions`` : la decision **reellement prise** pour chaque
   etudiant, avec la proposition du moteur conservee a cote. Le moteur
   propose, le jury tranche : la ligne porte les deux, et un ecart exige un
   motif. Une decision calculee n'est donc jamais presentee comme une
   decision de jury.

Une deliberation close devient immuable : c'est ce qui autorise ensuite
l'attestation de reussite, dont la generation exige un statut ``Admis``
constate par le jury.

Aucun seed de deliberation, aucune decision inventee. Les regles sont creees
sans valeur arbitraire jugee : les seuils existants sont repris comme point
de depart, avec ``confirme_par = NULL`` pour signaler qu'ils restent a
valider par l'institut.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0017_deliberation_pv"
down_revision: Union[str, None] = "0016_config_institutionnelle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

#: Bareme des mentions, repris des seuils deja en vigueur dans le moteur.
#: Ce sont des **points de depart**, pas un reglement valide : la ligne
#: creee porte ``confirme_par = NULL`` tant que l'institut ne l'a pas
#: explicitement confirmee.
BAREME_MENTIONS_DEPART = [
    {"libelle": "Tres Bien", "seuil_min": 16.0},
    {"libelle": "Bien", "seuil_min": 14.0},
    {"libelle": "Assez Bien", "seuil_min": 12.0},
    {"libelle": "Passable", "seuil_min": 0.0},
]


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Regles de deliberation de l'etablissement
    # ------------------------------------------------------------------
    op.create_table(
        "regles_deliberation",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("etablissement_id", sa.String(length=50), nullable=False),
        # Bareme de validation.
        sa.Column("seuil_validation_moyenne", sa.Float(), nullable=False),
        # Sous ce seuil, une note est eliminatoire et bloque la compensation.
        sa.Column("seuil_eliminatoire", sa.Float(), nullable=False),
        # Sous ce seuil de moyenne, l'etudiant est ajourne : le rattrapage
        # n'est pas ouvert. Le 8,5 du moteur existant etait en dur.
        sa.Column("seuil_rattrapage_minimale", sa.Float(), nullable=False),
        # ECTS minimaux pour un passage conditionnel.
        sa.Column("seuil_passage_conditionnel_ects", sa.Integer(), nullable=False),
        # La compensation entre UE est-elle admise ?
        sa.Column("compensation_autorisee", sa.Boolean(), nullable=False),
        # Bareme des mentions : [{libelle, seuil_min}].
        sa.Column("bareme_mentions", JSON_TYPE, nullable=False),
        # Reglement confirme par l'institut ? NULL = valeurs de depart,
        # jamais revues. Le conditionner evite de delibérer sur des regles
        # que personne n'a validees.
        sa.Column("confirme_par_id", sa.Integer(), nullable=True),
        sa.Column("confirme_par_email", sa.String(length=255), nullable=True),
        sa.Column("confirme_le", sa.DateTime(timezone=True), nullable=True),
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
            ["etablissement_id"], ["etablissements.id"], ondelete="CASCADE",
            name="fk_regles_deliberation_etablissement",
        ),
        sa.ForeignKeyConstraint(
            ["confirme_par_id"], ["utilisateurs.id"], ondelete="SET NULL",
            name="fk_regles_deliberation_confirme_par",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Une seule regle vivante par etablissement : c'est le reglement en vigueur.
    op.create_index(
        "uq_regles_deliberation_etablissement",
        "regles_deliberation",
        ["etablissement_id"],
        unique=True,
    )

    # ------------------------------------------------------------------
    # 2. Seances de jury
    # ------------------------------------------------------------------
    op.create_table(
        "deliberations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("etablissement_id", sa.String(length=50), nullable=False),
        # Une promotion = une classe + une session.
        sa.Column("classe_id", sa.String(length=50), nullable=False),
        sa.Column("session_id", sa.String(length=50), nullable=False),
        sa.Column("date_deliberation", sa.Date(), nullable=False),
        sa.Column("lieu", sa.String(length=255), nullable=True),
        sa.Column("president", sa.String(length=150), nullable=False),
        # [{nom, qualite}] — la composition est saisie, jamais devinee.
        sa.Column("membres", JSON_TYPE, nullable=False, server_default=sa.text("'[]'")),
        # 'brouillon' (seance en cours, decisions modifiables)
        # ou 'close' (verdict arrete, decisions immuables).
        sa.Column("statut", sa.String(length=20), nullable=False),
        # Regles en vigueur au moment de la seance, figees.
        sa.Column("regles", JSON_TYPE, nullable=False),
        sa.Column("close_le", sa.DateTime(timezone=True), nullable=True),
        sa.Column("close_par_id", sa.Integer(), nullable=True),
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
            ["etablissement_id"], ["etablissements.id"], ondelete="CASCADE",
            name="fk_deliberations_etablissement",
        ),
        sa.ForeignKeyConstraint(
            ["classe_id"], ["classes.id"], ondelete="CASCADE",
            name="fk_deliberations_classe",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["sessions_academiques.id"], ondelete="CASCADE",
            name="fk_deliberations_session",
        ),
        sa.ForeignKeyConstraint(
            ["close_par_id"], ["utilisateurs.id"], ondelete="SET NULL",
            name="fk_deliberations_close_par",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Un jury ne se tient deux fois pour la meme promotion et la meme session.
    op.create_index(
        "uq_deliberations_promotion",
        "deliberations",
        ["classe_id", "session_id"],
        unique=True,
    )

    # ------------------------------------------------------------------
    # 3. Decisions du jury
    # ------------------------------------------------------------------
    op.create_table(
        "deliberation_decisions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("deliberation_id", sa.String(length=36), nullable=False),
        sa.Column("etudiant_id", sa.String(length=50), nullable=False),
        # Ce que le moteur propose...
        sa.Column("proposition_statut", sa.String(length=30), nullable=False),
        sa.Column("proposition_mention", sa.String(length=50), nullable=True),
        # ...et ce que le jury a decide.
        sa.Column("statut", sa.String(length=30), nullable=False),
        sa.Column("mention", sa.String(length=50), nullable=True),
        # Ecart entre proposition et decision, et son motif. Un ecart sans
        # motif laisse la decision inexpliquee : il est donc obligatoire.
        sa.Column("motif_ecart", sa.Text(), nullable=True),
        # Elements de calcul conserves : moyenne generale, ECTS, moyennes
        # par UE. Le PV et l'attestation s'appuient dessus, pas sur un
        # recalcul ulterieur qui pourrait differer.
        sa.Column("moyenne_generale", sa.Float(), nullable=False),
        sa.Column("ects_acquis", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ects_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("moyennes_ue", JSON_TYPE, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("notes_eliminatoires", JSON_TYPE, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("decide_le", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decide_par_id", sa.Integer(), nullable=True),
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
            ["deliberation_id"], ["deliberations.id"], ondelete="CASCADE",
            name="fk_deliberation_decisions_deliberation",
        ),
        sa.ForeignKeyConstraint(
            ["etudiant_id"], ["etudiants.id"], ondelete="CASCADE",
            name="fk_deliberation_decisions_etudiant",
        ),
        sa.ForeignKeyConstraint(
            ["decide_par_id"], ["utilisateurs.id"], ondelete="SET NULL",
            name="fk_deliberation_decisions_decide_par",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Un etudiant ne peut avoir qu'une decision par seance.
    op.create_index(
        "uq_deliberation_decisions_etudiant",
        "deliberation_decisions",
        ["deliberation_id", "etudiant_id"],
        unique=True,
    )
    # Recherche de l'admission d'un etudiant pour une session donnee.
    op.create_index(
        "ix_deliberation_decisions_etudiant",
        "deliberation_decisions",
        ["etudiant_id"],
    )

    # ------------------------------------------------------------------
    # 4. Regles de depart, explicitement non confirmees
    # ------------------------------------------------------------------
    # Insertion typee plutot qu'un INSERT SQL : ``bareme_mentions`` est une
    # colonne JSON, et un parametre lie dans un ``text()`` y arriverait comme
    # du texte. Le type est ici declare explicitement.
    table = sa.table(
        "regles_deliberation",
        sa.column("id", sa.String),
        sa.column("etablissement_id", sa.String),
        sa.column("seuil_validation_moyenne", sa.Float),
        sa.column("seuil_eliminatoire", sa.Float),
        sa.column("seuil_rattrapage_minimale", sa.Float),
        sa.column("seuil_passage_conditionnel_ects", sa.Integer),
        sa.column("compensation_autorisee", sa.Boolean),
        sa.column("bareme_mentions", JSON_TYPE),
        sa.column("confirme_par_id", sa.Integer),
        sa.column("confirme_par_email", sa.String),
        sa.column("confirme_le", sa.DateTime(timezone=True)),
    )
    liaison = op.get_bind()
    # L'identifiant de l'etablissement n'est pas connu a la redaction de la
    # migration : on interroge la base au moment de l'application, pour que le
    # seed s'applique a l'instance reellement installee.
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
                    "id": f"regles-{etablissement_id[:24]}",
                    "etablissement_id": etablissement_id,
                    # Points de depart repris du moteur existant, **non
                    # confirmes** : confirme_par reste NULL tant que
                    # l'institut n'a pas valide son reglement.
                    "seuil_validation_moyenne": 10.0,
                    "seuil_eliminatoire": 7.0,
                    "seuil_rattrapage_minimale": 8.5,
                    "seuil_passage_conditionnel_ects": 18,
                    "compensation_autorisee": True,
                    "bareme_mentions": BAREME_MENTIONS_DEPART,
                    "confirme_par_id": None,
                    "confirme_par_email": None,
                    "confirme_le": None,
                }
                for etablissement_id in etablissements
            ],
        )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM regles_deliberation "
            "WHERE confirme_par_email IS NULL AND id LIKE 'regles-%'"
        )
    )
    op.drop_index("ix_deliberation_decisions_etudiant", table_name="deliberation_decisions")
    op.drop_index("uq_deliberation_decisions_etudiant", table_name="deliberation_decisions")
    op.drop_table("deliberation_decisions")
    op.drop_index("uq_deliberations_promotion", table_name="deliberations")
    op.drop_table("deliberations")
    op.drop_index("uq_regles_deliberation_etablissement", table_name="regles_deliberation")
    op.drop_table("regles_deliberation")
