"""Aligner le schéma Etablissement avec le modèle ORM.

Revision ID: 0003_align_etablissement
Revises: 0002_business_modules
Create Date: 2026-09-23

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_align_etablissement"
down_revision: Union[str, None] = "0002_business_modules"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns("etablissements")}


def _indexes(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    columns = _columns()

    # Some development databases were created with Base.metadata.create_all
    # instead of Alembic and therefore use the former Python column names.
    if "code" not in columns:
        if "sigle" in columns:
            with op.batch_alter_table("etablissements", schema=None) as batch_op:
                batch_op.alter_column(
                    "sigle",
                    new_column_name="code",
                    existing_type=sa.String(length=50),
                    existing_nullable=False,
                )
            columns.add("code")
        else:
            raise RuntimeError("Impossible de migrater etablissements: colonne code/sigle absente.")

    if "license_key" not in columns:
        if "licence_cle" in columns:
            with op.batch_alter_table("etablissements", schema=None) as batch_op:
                batch_op.alter_column(
                    "licence_cle",
                    new_column_name="license_key",
                    existing_type=sa.String(length=255),
                    existing_nullable=True,
                )
        else:
            op.add_column(
                "etablissements",
                sa.Column("license_key", sa.String(length=255), nullable=True),
            )
    elif "licence_cle" in columns:
        op.execute(
            sa.text(
                "UPDATE etablissements SET license_key = licence_cle "
                "WHERE license_key IS NULL"
            )
        )
        with op.batch_alter_table("etablissements", schema=None) as batch_op:
            batch_op.drop_column("licence_cle")

    if "pays" not in columns:
        op.add_column(
            "etablissements",
            sa.Column(
                "pays",
                sa.String(length=100),
                nullable=True,
                server_default="Côte d'Ivoire",
            ),
        )

    if "licence_statut" not in columns:
        op.add_column(
            "etablissements",
            sa.Column(
                "licence_statut",
                sa.String(length=50),
                nullable=False,
                server_default="active",
            ),
        )

    if "date_configuration" not in columns:
        op.add_column(
            "etablissements",
            sa.Column("date_configuration", sa.DateTime(timezone=True), nullable=True),
        )

    # Retire les colonnes de présentation qui ne font pas partie du modèle métier.
    for obsolete_column in ("site_web", "logo_url"):
        if obsolete_column in _columns():
            with op.batch_alter_table("etablissements", schema=None) as batch_op:
                batch_op.drop_column(obsolete_column)

    inspector = sa.inspect(op.get_bind())
    id_column = next(
        column for column in inspector.get_columns("etablissements") if column["name"] == "id"
    )
    if isinstance(id_column["type"], sa.Integer):
        if op.get_bind().dialect.name == "postgresql":
            op.alter_column(
                "etablissements",
                "id",
                existing_type=sa.Integer(),
                type_=sa.String(length=50),
                existing_nullable=False,
                postgresql_using="id::varchar(50)",
            )
        else:
            with op.batch_alter_table("etablissements", schema=None) as batch_op:
                batch_op.alter_column(
                    "id",
                    existing_type=sa.Integer(),
                    type_=sa.String(length=50),
                    existing_nullable=False,
                )

    # Aligne les types et la nullabilité avec les colonnes déjà présentes dans 0001/0002.
    with op.batch_alter_table("etablissements", schema=None) as batch_op:
        batch_op.alter_column(
            "adresse",
            existing_type=sa.String(length=255),
            type_=sa.String(length=500),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "email",
            existing_type=sa.String(length=255),
            type_=sa.String(length=255),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "telephone",
            existing_type=sa.String(length=50),
            type_=sa.String(length=50),
            existing_nullable=True,
        )

    if "ix_etablissements_code" in _indexes("etablissements"):
        op.drop_index("ix_etablissements_code", table_name="etablissements")
    op.create_index("ix_etablissements_code", "etablissements", ["code"], unique=True)

    # Ces index sont absents de la version 0002 livrée initialement. Leur ajout
    # idempotent permet aussi de rattraper une base déjà migrée en 0002.
    business_indexes = [
        ("ix_cours_enseignant_id", "cours", ["enseignant_id"]),
        ("ix_notes_examen_id", "notes", ["examen_id"]),
        ("ix_notes_session_id", "notes", ["session_id"]),
        ("ix_absences_cours_id", "absences", ["cours_id"]),
        ("ix_absences_matiere_id", "absences", ["matiere_id"]),
        ("ix_paiements_facture_id", "paiements", ["facture_id"]),
    ]
    for index_name, table_name, columns in business_indexes:
        if index_name not in _indexes(table_name):
            op.create_index(index_name, table_name, columns, unique=False)


def downgrade() -> None:
    op.add_column("etablissements", sa.Column("site_web", sa.String(length=255), nullable=True))
    op.add_column("etablissements", sa.Column("logo_url", sa.String(length=500), nullable=True))

    with op.batch_alter_table("etablissements", schema=None) as batch_op:
        batch_op.alter_column(
            "adresse",
            existing_type=sa.String(length=500),
            type_=sa.String(length=255),
            existing_nullable=True,
        )

    op.drop_column("etablissements", "date_configuration")
    op.drop_column("etablissements", "licence_statut")
    op.drop_column("etablissements", "pays")
