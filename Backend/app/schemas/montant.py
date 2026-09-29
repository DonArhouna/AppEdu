"""Type partage des montants de l'API.

Les colonnes monetaires sont des ``Decimal`` exacts (Numeric(14, 2) depuis la
migration 0023), mais le contrat JSON historique transporte des **nombres** :
le frontend lit ``montant_total`` comme un ``number``, pas comme une chaine.

Pydantic v2 serialise un ``Decimal`` en chaine par defaut — garder ce
comportement changerait silencieusement le contrat de tous les ecrans
(``Number(x).toLocaleString()`` sur une chaine rend ``NaN``).  Le
serialiseur reconvertit donc en flottant a la frontiere JSON : l'exactitude
vit dans la base et dans les calculs serveur, le JSON n'est qu'un affichage.

En entree, la validation reste un ``Decimal`` : les contraintes
``max_digits``/``decimal_places`` et les bornes ``ge``/``gt`` s'appliquent,
et un montant refuse l'est avant d'atteindre la base.
"""

from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer

Montant = Annotated[Decimal, PlainSerializer(float, return_type=float)]

__all__ = ["Montant"]
