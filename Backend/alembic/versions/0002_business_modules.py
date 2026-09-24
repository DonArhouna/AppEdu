"""business_modules

Revision ID: 0002_business_modules
Revises: 0001_initial_schema
Create Date: 2026-09-09 10:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0002_business_modules"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # 1. Structure Académique
    # -----------------------------------------------------------------------
    op.create_table(
        "campuses",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("nom", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("adresse", sa.String(length=255), nullable=True),
        sa.Column("ville", sa.String(length=100), nullable=True),
        sa.Column("responsable", sa.String(length=150), nullable=True),
        sa.Column("telephone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_campuses_code"), "campuses", ["code"], unique=True)

    op.create_table(
        "departements",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("campus_id", sa.String(length=50), nullable=True),
        sa.Column("nom", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("responsable", sa.String(length=150), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["campus_id"], ["campuses.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_departements_code"), "departements", ["code"], unique=True)
    op.create_index(op.f("ix_departements_campus_id"), "departements", ["campus_id"], unique=False)

    op.create_table(
        "filieres",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("departement_id", sa.String(length=50), nullable=True),
        sa.Column("nom", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("diplome", sa.String(length=50), nullable=False, server_default="Licence"),
        sa.Column("duree", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["departement_id"], ["departements.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_filieres_code"), "filieres", ["code"], unique=True)
    op.create_index(op.f("ix_filieres_departement_id"), "filieres", ["departement_id"], unique=False)

    op.create_table(
        "unites_enseignement",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("filiere_id", sa.String(length=50), nullable=True),
        sa.Column("nom", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("coefficient", sa.Float(), nullable=False, server_default="3.0"),
        sa.Column("heures", sa.Integer(), nullable=False, server_default="45"),
        sa.Column("semestre", sa.String(length=20), nullable=False, server_default="S1"),
        sa.Column("niveau", sa.String(length=50), nullable=False, server_default="Licence 1"),
        sa.Column("responsable", sa.String(length=150), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["filiere_id"], ["filieres.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_unites_enseignement_code"), "unites_enseignement", ["code"], unique=True)
    op.create_index(op.f("ix_unites_enseignement_filiere_id"), "unites_enseignement", ["filiere_id"], unique=False)

    op.create_table(
        "matieres",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("ue_id", sa.String(length=50), nullable=True),
        sa.Column("nom", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("coefficient", sa.Float(), nullable=False, server_default="1.5"),
        sa.Column("heures_cm", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("heures_td", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("heures_tp", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("enseignant_nom", sa.String(length=150), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["ue_id"], ["unites_enseignement.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_matieres_code"), "matieres", ["code"], unique=True)
    op.create_index(op.f("ix_matieres_ue_id"), "matieres", ["ue_id"], unique=False)

    # -----------------------------------------------------------------------
    # 2. Extension Étudiants (filiere_id, sexe, adresse, date_inscription)
    # -----------------------------------------------------------------------
    op.add_column("etudiants", sa.Column("filiere_id", sa.String(length=50), nullable=True))
    op.add_column("etudiants", sa.Column("sexe", sa.String(length=10), nullable=True, server_default="M"))
    op.add_column("etudiants", sa.Column("adresse", sa.String(length=255), nullable=True))
    op.add_column("etudiants", sa.Column("date_inscription", sa.Date(), nullable=True))
    with op.batch_alter_table("etudiants", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_etudiants_filiere_id",
            "filieres",
            ["filiere_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index(op.f("ix_etudiants_filiere_id"), "etudiants", ["filiere_id"], unique=False)

    # -----------------------------------------------------------------------
    # 3. Pédagogie (Cours, Examens, Notes, Absences)
    # -----------------------------------------------------------------------
    op.create_table(
        "cours",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("matiere_id", sa.String(length=50), nullable=False),
        sa.Column("enseignant_id", sa.Integer(), nullable=True),
        sa.Column("enseignant_nom", sa.String(length=150), nullable=True),
        sa.Column("salle", sa.String(length=50), nullable=False),
        sa.Column("jour_semaine", sa.String(length=20), nullable=False),
        sa.Column("heure_debut", sa.String(length=10), nullable=False),
        sa.Column("heure_fin", sa.String(length=10), nullable=False),
        sa.Column("type_cours", sa.String(length=20), nullable=False, server_default="CM"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["matiere_id"], ["matieres.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["enseignant_id"], ["utilisateurs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cours_matiere_id"), "cours", ["matiere_id"], unique=False)
    op.create_index(op.f("ix_cours_enseignant_id"), "cours", ["enseignant_id"], unique=False)

    op.create_table(
        "examens",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("nom", sa.String(length=255), nullable=False),
        sa.Column("session_id", sa.String(length=50), nullable=False),
        sa.Column("matiere_id", sa.String(length=50), nullable=False),
        sa.Column("type_examen", sa.String(length=50), nullable=False, server_default="Examen Final"),
        sa.Column("date_examen", sa.Date(), nullable=False),
        sa.Column("duree_minutes", sa.Integer(), nullable=False, server_default="120"),
        sa.Column("coefficient", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions_academiques.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["matiere_id"], ["matieres.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_examens_session_id"), "examens", ["session_id"], unique=False)
    op.create_index(op.f("ix_examens_matiere_id"), "examens", ["matiere_id"], unique=False)

    op.create_table(
        "notes",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("etudiant_id", sa.String(length=50), nullable=False),
        sa.Column("matiere_id", sa.String(length=50), nullable=False),
        sa.Column("examen_id", sa.String(length=50), nullable=True),
        sa.Column("session_id", sa.String(length=50), nullable=True),
        sa.Column("valeur", sa.Float(), nullable=False),
        sa.Column("coefficient", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("appreciation", sa.String(length=255), nullable=True),
        sa.Column("statut", sa.String(length=30), nullable=False, server_default="Validé"),
        sa.Column("saisi_par_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["etudiant_id"], ["etudiants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["matiere_id"], ["matieres.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["examen_id"], ["examens.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions_academiques.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["saisi_par_id"], ["utilisateurs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notes_etudiant_id"), "notes", ["etudiant_id"], unique=False)
    op.create_index(op.f("ix_notes_matiere_id"), "notes", ["matiere_id"], unique=False)
    op.create_index(op.f("ix_notes_examen_id"), "notes", ["examen_id"], unique=False)
    op.create_index(op.f("ix_notes_session_id"), "notes", ["session_id"], unique=False)

    op.create_table(
        "absences",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("etudiant_id", sa.String(length=50), nullable=False),
        sa.Column("cours_id", sa.String(length=50), nullable=True),
        sa.Column("matiere_id", sa.String(length=50), nullable=True),
        sa.Column("date_absence", sa.Date(), nullable=False),
        sa.Column("duree_heures", sa.Float(), nullable=False, server_default="2.0"),
        sa.Column("justifiee", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("motif", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["etudiant_id"], ["etudiants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cours_id"], ["cours.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["matiere_id"], ["matieres.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_absences_etudiant_id"), "absences", ["etudiant_id"], unique=False)
    op.create_index(op.f("ix_absences_cours_id"), "absences", ["cours_id"], unique=False)
    op.create_index(op.f("ix_absences_matiere_id"), "absences", ["matiere_id"], unique=False)

    # -----------------------------------------------------------------------
    # 4. Finances (Factures, Paiements, Reçus)
    # -----------------------------------------------------------------------
    op.create_table(
        "factures",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("numero_facture", sa.String(length=50), nullable=False),
        sa.Column("etudiant_id", sa.String(length=50), nullable=False),
        sa.Column("session_id", sa.String(length=50), nullable=False),
        sa.Column("montant_total", sa.Float(), nullable=False),
        sa.Column("montant_paye", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("date_emission", sa.Date(), nullable=False),
        sa.Column("date_echeance", sa.Date(), nullable=False),
        sa.Column("statut", sa.String(length=30), nullable=False, server_default="emise"),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["etudiant_id"], ["etudiants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions_academiques.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_factures_numero_facture"), "factures", ["numero_facture"], unique=True)
    op.create_index(op.f("ix_factures_etudiant_id"), "factures", ["etudiant_id"], unique=False)
    op.create_index(op.f("ix_factures_session_id"), "factures", ["session_id"], unique=False)

    op.create_table(
        "paiements",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("facture_id", sa.String(length=50), nullable=True),
        sa.Column("etudiant_id", sa.String(length=50), nullable=False),
        sa.Column("session_id", sa.String(length=50), nullable=False),
        sa.Column("periode_id", sa.String(length=50), nullable=True),
        sa.Column("montant", sa.Float(), nullable=False),
        sa.Column("date_paiement", sa.Date(), nullable=False),
        sa.Column("mode_paiement", sa.String(length=50), nullable=False, server_default="Espèces"),
        sa.Column("reference", sa.String(length=100), nullable=False),
        sa.Column("statut", sa.String(length=30), nullable=False, server_default="valide"),
        sa.Column("encaisse_par_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["facture_id"], ["factures.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["etudiant_id"], ["etudiants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions_academiques.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["periode_id"], ["periodes_paiement.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["encaisse_par_id"], ["utilisateurs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_paiements_etudiant_id"), "paiements", ["etudiant_id"], unique=False)
    op.create_index(op.f("ix_paiements_facture_id"), "paiements", ["facture_id"], unique=False)
    op.create_index(op.f("ix_paiements_session_id"), "paiements", ["session_id"], unique=False)
    op.create_index(op.f("ix_paiements_periode_id"), "paiements", ["periode_id"], unique=False)

    op.create_table(
        "recus",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("numero_recu", sa.String(length=50), nullable=False),
        sa.Column("paiement_id", sa.String(length=50), nullable=False),
        sa.Column("date_emission", sa.Date(), nullable=False),
        sa.Column("donnees_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["paiement_id"], ["paiements.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("paiement_id"),
    )
    op.create_index(op.f("ix_recus_numero_recu"), "recus", ["numero_recu"], unique=True)


def downgrade() -> None:
    op.drop_table("recus")
    op.drop_table("paiements")
    op.drop_table("factures")

    op.drop_table("absences")
    op.drop_table("notes")
    op.drop_table("examens")
    op.drop_table("cours")

    op.drop_constraint("fk_etudiants_filiere_id", "etudiants", type_="foreignkey")
    op.drop_index(op.f("ix_etudiants_filiere_id"), table_name="etudiants")
    op.drop_column("etudiants", "date_inscription")
    op.drop_column("etudiants", "adresse")
    op.drop_column("etudiants", "sexe")
    op.drop_column("etudiants", "filiere_id")

    op.drop_table("matieres")
    op.drop_table("unites_enseignement")
    op.drop_table("filieres")
    op.drop_table("departements")
    op.drop_table("campuses")
