"""Retire les valeurs métier implicites des colonnes d'établissement.

Les valeurs de démonstration et les valeurs de repli ({2025-2026}, {FCFA},
{ Licence }, {S1}, etc.) ne doivent pas être injectées par PostgreSQL lorsqu'un
champ obligatoire est omis. Les API et formulaires fournissent désormais ces
valeurs explicitement.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_remove_implicit_defaults"
down_revision: Union[str, None] = "0005_add_fee_grids"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, column, SQL type, former server default)
_DEFAULTS_TO_REMOVE = (
    ("etablissements", "devise", sa.String(length=10), "FCFA"),
    ("etablissements", "pays", sa.String(length=100), "Côte d'Ivoire"),
    ("etablissements", "licence_statut", sa.String(length=50), "active"),
    ("utilisateurs", "role", sa.String(length=50), "ADMIN"),
    ("sessions_academiques", "annee_academique", sa.String(length=20), "2025-2026"),
    ("sessions_academiques", "statut", sa.String(length=20), "active"),
    ("periodes_paiement", "montant_estime", sa.Float(), "0.0"),
    ("periodes_paiement", "ordre", sa.Integer(), "1"),
    ("etudiants", "sexe", sa.String(length=10), "M"),
    ("etudiants", "statut", sa.String(length=30), "Inscrit"),
    ("filieres", "diplome", sa.String(length=50), "Licence"),
    ("filieres", "duree", sa.Integer(), "3"),
    ("unites_enseignement", "credits", sa.Integer(), "6"),
    ("unites_enseignement", "coefficient", sa.Float(), "3.0"),
    ("unites_enseignement", "heures", sa.Integer(), "45"),
    ("unites_enseignement", "semestre", sa.String(length=20), "S1"),
    ("unites_enseignement", "niveau", sa.String(length=50), "Licence 1"),
    ("matieres", "credits", sa.Integer(), "3"),
    ("matieres", "coefficient", sa.Float(), "1.5"),
    ("matieres", "heures_cm", sa.Integer(), "20"),
    ("matieres", "heures_td", sa.Integer(), "15"),
    ("matieres", "heures_tp", sa.Integer(), "10"),
)


def upgrade() -> None:
    for table_name, column_name, column_type, _ in _DEFAULTS_TO_REMOVE:
        with op.batch_alter_table(table_name) as batch:
            batch.alter_column(
                column_name,
                existing_type=column_type,
                server_default=None,
            )


def downgrade() -> None:
    for table_name, column_name, column_type, default in _DEFAULTS_TO_REMOVE:
        with op.batch_alter_table(table_name) as batch:
            batch.alter_column(
                column_name,
                existing_type=column_type,
                server_default=default,
            )
