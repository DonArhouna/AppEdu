"""Barème de mentions conforme aux usages observés

Revision ID: 0021_bareme_mentions
Revises: 0020_semestres

Le barème de départ portait quatre mentions, de « Passable » à 0. Deux
divergences avec les relevés de l'institut :

1. **« Insuffisant » manquait.** Sous l'ancien barème, une note de 3/20
   s'affichait « Passable ». C'est une affirmation fausse sur un document
   officiel : l'étudiant lit qu'il a passé alors qu'il est en rattrapage.
2. **« Passable » démarrait à 0** au lieu de 10. Une borne à 0 rendait la
   mention inutile — tout passage serait « passable », et l'échelle n'aurait
   plus trois degrés mais un.

Barème appliqué, déduit des relevés :

    Très Bien  >= 16      Bien      >= 14
    Assez Bien >= 12      Passable  >= 10      Insuffisant < 10

Deux précautions :

- la migration ne touche que les règles **non confirmées**, celles qui sont
  encore des valeurs de départ. Un règlement confirmé garde le barème que son
  jury a fixé : changer d'avis sur ses propres seuils n'appartient pas à une
  migration ;
- l'écriture passe par le type JSON du dialecte (JSONB sur PostgreSQL), pas
  par un ``CAST`` en SQL brut — un ``CAST(... AS JSON)`` ecrit dans une
  colonne ``jsonb`` depend de l'alias de type, qui n'est pas le meme partout.
"""

import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0021_bareme_mentions"
down_revision: Union[str, None] = "0020_semestres"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

#: Barème issu des relevés, du plus haut au plus bas : c'est l'ordre dans
#: lequel le module de délibération les applique, le premier seuil atteint
#: donnant la mention.
BAREME_CORRECT = [
    {"libelle": "Très Bien", "seuil_min": 16.0},
    {"libelle": "Bien", "seuil_min": 14.0},
    {"libelle": "Assez Bien", "seuil_min": 12.0},
    {"libelle": "Passable", "seuil_min": 10.0},
    {"libelle": "Insuffisant", "seuil_min": 0.0},
]

#: Ancien barème, conservé pour que le downgrade remette exactement l'état
#: précédent.
BAREME_ANCIEN = [
    {"libelle": "Très Bien", "seuil_min": 16.0},
    {"libelle": "Bien", "seuil_min": 14.0},
    {"libelle": "Assez Bien", "seuil_min": 12.0},
    {"libelle": "Passable", "seuil_min": 0.0},
]

TYPE_JSON = JSON().with_variant(JSONB, "postgresql")


def _ecrire(bareme: list) -> None:
    """Ecrit le barème sur les seules regles non confirmees."""

    liaison = op.get_bind()
    identifiants = [
        row[0]
        for row in liaison.execute(
            sa.text(
                "SELECT id FROM regles_deliberation "
                "WHERE confirme_par_email IS NULL"
            )
        )
    ]
    if not identifiants:
        return

    # Le parametre est type par le dialecte : PostgreSQL reçoit du JSONB,
    # SQLite du JSON. Un ``CAST`` en SQL brut ecrit dans une colonne ``jsonb``
    # dependrait de l'alias de type, qui n'est pas le meme partout.
    expression = sa.bindparam(
        "bareme",
        type_=TYPE_JSON,
        value=bareme,
    )
    for identifiant in identifiants:
        liaison.execute(
            sa.text(
                "UPDATE regles_deliberation SET bareme_mentions = :bareme "
                "WHERE id = :id"
            ).bindparams(expression),
            {"id": identifiant},
        )


def upgrade() -> None:
    _ecrire(BAREME_CORRECT)


def downgrade() -> None:
    _ecrire(BAREME_ANCIEN)
