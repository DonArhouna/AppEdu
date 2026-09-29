"""Table des salles physiques, que l'emploi du temps va enfin occuper.

Revision ID: 0025_salles
Revises: 0024_auth_hardening

Jusqu'ici, une salle n'existait nulle part : ``cours.salle`` portait un texte
libre — « Amphi A », « salle 12 », ce que chacun avait ecrit ce jour-la — et
rien n'empechait deux cours de s'y retrouver le meme lundi de 8h a 10h. Le
conflit n'etait pas detectable, parce que la salle n'etait pas une donnee.

Cette revision cree la table ``salles`` : nom, code unique, campus optionnel,
capacite, type (salle de classe, laboratoire, amphi...), equipements,
disponibilite. **Elle ne touche pas a ``cours.salle``** : les cours existants
gardent leur texte, aucune donnee n'est reinterpretee ou perdue. Le rattachement
d'un cours a une salle se fera progressivement, a la mise a jour de chaque
cours, par correspondance de nom (insensible a la casse) — jamais par une
conversion silencieuse.

Additive : le downgrade supprime la table, sans rien reecrire ailleurs.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0025_salles"
down_revision: Union[str, None] = "0024_auth_hardening"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "salles",
        sa.Column("id", sa.String(length=50), primary_key=True),
        # Le nom est ce que le cours cite : la correspondance cours ↔ salle
        # se fait sur lui, insensible a la casse. Unique : deux salles du
        # meme nom rendraient la correspondance ambigue.
        sa.Column("nom", sa.String(length=150), nullable=False, unique=True),
        # Le code est l'identifiant d'affichage court (plan, inventaire).
        sa.Column("code", sa.String(length=50), nullable=False, unique=True),
        sa.Column(
            "campus_id",
            sa.String(length=50),
            sa.ForeignKey("campuses.id", ondelete="SET NULL", name="fk_salles_campus_id"),
            nullable=True,
            index=True,
        ),
        sa.Column("batiment", sa.String(length=100), nullable=True),
        sa.Column("etage", sa.String(length=50), nullable=True),
        sa.Column("capacite", sa.Integer(), nullable=True),
        # Salle de classe, laboratoire, amphi, atelier, bureau... : une
        # etiquette libre, l'institut nomme ses lieux comme il veut.
        sa.Column("type_salle", sa.String(length=50), nullable=False, server_default="Salle de classe"),
        sa.Column("equipements", sa.Text(), nullable=True),
        # ``true`` et non ``1`` : PostgreSQL type strictement les booleens,
        # SQLite comprend les deux.
        sa.Column("disponible", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("salles")
