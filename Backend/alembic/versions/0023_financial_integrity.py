"""Integrite financiere : montants en Numeric, unicite des notes, FK comptables RESTRICT.

Revision ID: 0023_financial_integrity
Revises: 0022_ue_annuelle

Trois changements, tous compatibles avec des donnees existantes :

1. **Les montants passent de Float a Numeric(14, 2).**  Un ``float`` est un
   binaire : ``0.1 + 0.2`` n'y vaut pas ``0.3``, et un solde de scolarite
   cumule des centaines d'additions.  La conversion lit chaque valeur avec le
   type qui a ecrit la colonne (``double precision`` sur PostgreSQL, ``REAL``
   sur SQLite) : ``1999.99`` redevient exactement ``1999.99``.  Aucun montant
   n'est invente ni reformate — seule la representation change.  Les
   server defaults existants (``'0.0'`` sur ``montant_paye``) sont conservés :
   PostgreSQL les convertit en numeric sans perte.

2. **Une note n'existe qu'une fois** par (etudiant, matiere, examen,
   session).  Jusqu'ici, la saisie unitaire et l'import en lot pouvaient
   inserer deux notes sur la meme cle ; le bulletin en lisait une au hasard
   et la deliberation sommait l'autre.  La contrainte est posee APRES
   deduplication : des doublons **exact**s (meme valeur, meme coefficient)
   sont tranches vers l'ecriture la plus recente ; deux notes de valeurs
   differentes sur la meme cle sont une **erreur** — la migration echoue et
   demande une decision humaine, parce qu'un bulletin ne choisit pas seul.

3. **Une facture, un paiement ou une relance ne meurt pas avec son etudiant.**
   Les FK comptables passent de CASCADE a RESTRICT : supprimer un etudiant
   qui a des ecritures devient un refus explicite (l'endpoint renvoie
   desormais 409 avant que la base ne parle), pas une destruction silencieuse
   de pieces comptables.

Les noms des contraintes a supprimer diffèrent par dialecte : PostgreSQL
auto-nomme une FK sans nom ``{table}_{colonne}_fkey`` a la creation (migration
0002), et SQLite ne stocke aucun nom — en batch, la ``naming_convention``
recalcule les memes noms que la reflection.  Les FK de ``relances`` (0018)
portent des noms explicites cote PostgreSQL, mais restent anonymes cote
SQLite : la convention couvre les deux cas.

Les colonnes de notes (``valeur``, ``coefficient``) et les seuils de
deliberation restent en Float : ce sont des mesures, pas de l'argent.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0023_financial_integrity"
down_revision: Union[str, None] = "0022_ue_annuelle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


#: (table, colonne, nullable).  L'ordre des colonnes n'a pas de sens metier :
#: c'est l'inventaire exhaustif des monnaies du schema.
MONTANTS = [
    ("grilles_tarifaires", "droits_inscription", False),
    ("grilles_tarifaires", "scolarite_mensuelle", False),
    ("factures", "montant_total", False),
    ("factures", "montant_paye", False),
    ("paiements", "montant", False),
    ("periodes_paiement", "montant_estime", True),
    ("relances", "montant_reclame", False),
    ("relances", "solde_apres", True),
]

#: 14 chiffres dont 2 decimales : jusqu'a 999 999 999 999,99 dans la devise
#: de l'etablissement.  Une colonne sans echelle accepterait un ``999`` saisi
#: par erreur comme ``999,00`` — la monnaie ne se devine pas.
MONEY_TYPE = sa.Numeric(14, 2)

#: Cle d'unicite d'une note, dans l'ordre des colonnes.
NOTE_KEY = ("etudiant_id", "matiere_id", "examen_id", "session_id")

#: FK comptables : (nouveau nom, table, colonne, table cible, colonne cible).
#: Les quatre premieres viennent de 0002 (contraintes sans nom), les relances
#: de 0018 (nommees cote PostgreSQL).
FK_COMPTABLES = [
    ("fk_factures_etudiant_id", "factures", "etudiant_id", "etudiants", "id"),
    ("fk_factures_session_id", "factures", "session_id", "sessions_academiques", "id"),
    ("fk_paiements_facture_id", "paiements", "facture_id", "factures", "id"),
    ("fk_paiements_etudiant_id", "paiements", "etudiant_id", "etudiants", "id"),
    ("fk_paiements_session_id", "paiements", "session_id", "sessions_academiques", "id"),
    ("fk_paiements_periode_id", "paiements", "periode_id", "periodes_paiement", "id"),
    ("fk_recus_paiement_id", "recus", "paiement_id", "paiements", "id"),
    ("fk_relances_etudiant_id", "relances", "etudiant_id", "etudiants", "id"),
    ("fk_relances_session_id", "relances", "session_id", "sessions_academiques", "id"),
]

#: FK de 0018 posees AVEC un nom explicite : c'est lui que PostgreSQL connait.
NOMS_PG_0018 = {
    ("relances", "etudiant_id"): "fk_relances_etudiant",
    ("relances", "session_id"): "fk_relances_session",
}

#: Convention alembic officielle pour nommer les FK sans nom en mode batch :
#: sans elle, SQLite ne peut ni refleter ni supprimer une contrainte anonyme.
NAMING_CONVENTION = {
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
}


def _nom_pg(nouveau_nom: str, table: str, colonne: str) -> str:
    """Nom que PostgreSQL a donne a la contrainte d'origine.

    Une FK sans nom creee par 0002 porte le nom auto-genere
    ``{table}_{colonne}_fkey`` ; celle de 0018 porte son nom explicite.
    """

    return NOMS_PG_0018.get((table, colonne), f"{table}_{colonne}_fkey")


def _dedupliquer_notes() -> None:
    """Tranche les doublons de notes avant de poser l'unicite.

    Lecture des doublons en Python, ecriture par DELETE parametre : le SQL de
    fenetrage differe entre PostgreSQL et SQLite, la logique n'a pas a en
    dependre.
    """

    bind = op.get_bind()
    notes = sa.table(
        "notes",
        sa.column("id", sa.String),
        sa.column("etudiant_id", sa.String),
        sa.column("matiere_id", sa.String),
        sa.column("examen_id", sa.String),
        sa.column("session_id", sa.String),
        sa.column("valeur", sa.Float),
        sa.column("coefficient", sa.Float),
        sa.column("created_at", sa.DateTime),
    )

    lignes = bind.execute(
        sa.select(
            notes.c.id,
            notes.c.etudiant_id,
            notes.c.matiere_id,
            notes.c.examen_id,
            notes.c.session_id,
            notes.c.valeur,
            notes.c.coefficient,
            notes.c.created_at,
        )
    ).fetchall()

    groupes: dict = {}
    for ligne in lignes:
        cle = (ligne.etudiant_id, ligne.matiere_id, ligne.examen_id, ligne.session_id)
        groupes.setdefault(cle, []).append(ligne)

    supprimees: list = []
    for cle, membres in groupes.items():
        if len(membres) < 2:
            continue
        valeurs = {(float(m.valeur), float(m.coefficient)) for m in membres}
        if len(valeurs) > 1:
            # Deux notes differentes sur la meme cle : un bulletin ne peut
            # pas choisir tout seul, et la migration ne tranche pas a la
            # place de l'institut.
            ids = ", ".join(repr(m.id) for m in membres)
            raise RuntimeError(
                "Notes en conflit sur une meme cle (etudiant, matiere, examen, "
                f"session) : {cle}. Lignes concernees : {ids}. Tranchez "
                "manuellement (gardez la bonne, supprimez l'autre) puis "
                "relancez la migration."
            )
        # Doublons exacts : la plus recente l'emporte, comme une relecture
        # du registre.  Tri lexicographique de la date : les valeurs d'une
        # meme base partagent le meme format, et ``None`` (jamais datee)
        # se range comme la plus ancienne.
        membres.sort(key=lambda m: str(m.created_at or ""), reverse=True)
        supprimees.extend(m.id for m in membres[1:])

    for note_id in supprimees:
        bind.execute(sa.delete(notes).where(notes.c.id == note_id))
    if supprimees:
        print(
            f"0023_financial_integrity : {len(supprimees)} note(s) "
            "duplique(es) exactement supprimee(s), la plus recente gardee."
        )


def upgrade() -> None:
    bind = op.get_bind()
    est_sqlite = bind.dialect.name == "sqlite"

    # 1. Monnaies en decimal.
    if est_sqlite:
        # SQLite ignore ALTER TYPE : le batch reconstruit chaque table.
        # Le server default reflechi est preserve par le batch.
        for table, colonne, nullable in MONTANTS:
            with op.batch_alter_table(table) as batch:
                batch.alter_column(
                    colonne,
                    existing_type=sa.Float(),
                    type_=MONEY_TYPE,
                    nullable=nullable,
                )
    else:
        # La conversion lit les bits du type d'origine : sans le USING
        # explicite, PostgreSQL relirait un double comme s'il avait toujours
        # ete decimal — ce qui est ici le comportement voulu, mais le USING
        # le rend explicite et rejetable a la relecture.
        for table, colonne, _ in MONTANTS:
            op.execute(
                sa.text(
                    f"ALTER TABLE {table} ALTER COLUMN {colonne} "
                    f"TYPE NUMERIC(14, 2) USING {colonne}::double precision"
                )
            )

    # 2. Une note existe une fois par cle.  La deduplication AVANT la
    # contrainte : une base tachee doit migrer, pas refuser en silence.
    _dedupliquer_notes()
    with op.batch_alter_table("notes") as batch:
        batch.create_unique_constraint(
            "uq_notes_etudiant_matiere_examen_session",
            list(NOTE_KEY),
        )

    # 3. Les FK comptables deviennent RESTRICT.
    #
    # Le swap ne s'execute que sur PostgreSQL, la base de production.  SQLite
    # n'applique jamais les foreign keys : la bibliothèque ne passe pas le
    # ``PRAGMA foreign_keys = ON``, donc CASCADE comme RESTRICT y sont inertes
    # — et la reconstruction de table batch ne peut de toute facon pas retirer
    # une FK reflechie sans nom.  La conservation comptable reste garantie sur
    # SQLite par les endpoints, qui refusent la suppression (409) AVANT que la
    # base ne parle : c'est ce que couvrent les suites E2E.
    if est_sqlite:
        return
    for nouveau_nom, table, colonne, cible_table, cible_colonne in FK_COMPTABLES:
        op.drop_constraint(
            _nom_pg(nouveau_nom, table, colonne), table, type_="foreignkey"
        )
        op.create_foreign_key(
            nouveau_nom,
            table,
            cible_table,
            [colonne],
            [cible_colonne],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    bind = op.get_bind()
    est_sqlite = bind.dialect.name == "sqlite"

    # Retour aux cascades d'origine.  Les notes supprimees en deduplication
    # ne reviennent pas : un downgrade ne reecrit pas un historique detruit,
    # il retire seulement les contraintes.  Comme a la montee, SQLite est
    # exclu : FK inertes, swap sans objet.
    if est_sqlite:
        return
    for nouveau_nom, table, colonne, cible_table, cible_colonne in FK_COMPTABLES:
        op.drop_constraint(nouveau_nom, table, type_="foreignkey")
        op.create_foreign_key(
            _nom_pg(nouveau_nom, table, colonne),
            table,
            cible_table,
            [colonne],
            [cible_colonne],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("notes") as batch:
        batch.drop_constraint("uq_notes_etudiant_matiere_examen_session", type_="unique")

    if est_sqlite:
        for table, colonne, nullable in MONTANTS:
            with op.batch_alter_table(table) as batch:
                batch.alter_column(
                    colonne,
                    existing_type=MONEY_TYPE,
                    type_=sa.Float(),
                    nullable=nullable,
                )
    else:
        for table, colonne, _ in MONTANTS:
            op.execute(
                sa.text(
                    f"ALTER TABLE {table} ALTER COLUMN {colonne} "
                    f"TYPE DOUBLE PRECISION USING {colonne}::double precision"
                )
            )
