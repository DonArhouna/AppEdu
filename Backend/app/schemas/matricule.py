"""Schemas de la nomenclature de matricule."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class MatriculeParametresOut(BaseModel):
    """Regle en vigueur, avec un exemple lisible.

    L'exemple est indispensable : sans lui, un modele mal saisi n'est decouvert
    qu'a la creation du prochain dossier, c'est-a-dire sur un etudiant reel.
    """

    model_config = ConfigDict(from_attributes=True)

    modele: str
    largeur_numero: int
    demarrage: int
    #: Modele de depart historique, pour que l'ecran puisse signaler ce qui a
    #: change et proposez de revenir en arriere.
    modele_depart: str
    exemple: str
    #: true des que la regle differe du modele de depart.
    personnalisee: bool
    configuree: bool
    maj_par_email: Optional[str] = None
    maj_le: Optional[datetime] = None


class MatriculeParametresMaj(BaseModel):
    """Nouvelle regle. Remplace integralement la precedente."""

    modele: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description=(
            "Modèle du matricule. Jetons acceptés : {annee}, {filiere}, "
            "{numero}. {numero} est obligatoire : sans compteur, deux "
            "étudiants porteraient le même matricule."
        ),
        examples=["{annee}-{filiere}-{numero}"],
    )
    largeur_numero: int = Field(
        4, ge=1, le=8, description="Nombre de chiffres du compteur. 4 donne 0001."
    )
    demarrage: int = Field(
        1, ge=1, le=99999999, description="Premier numéro attribué."
    )


class JetonMatricule(BaseModel):
    """Un jeton accepte, pour que l'ecran n'invente pas la liste."""

    jeton: str
    libelle: str
    exemple: str


class MatriculeJetons(BaseModel):
    jetons: List[JetonMatricule]


__all__ = [
    "JetonMatricule",
    "MatriculeJetons",
    "MatriculeParametresMaj",
    "MatriculeParametresOut",
]
