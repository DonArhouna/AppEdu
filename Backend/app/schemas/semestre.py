"""Schemas des semestres."""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SemestreBase(BaseModel):
    """Ce qu'un semestre porte.

    Le **numero** donne l'ordre et le **libelle** ce que l'institut ecrit.
    Les deux sont necessaires : l'un sans l'autre, soit le bulletin affiche
    « 1 », soit il suppose que « S1 », « s1 » et « Semestre 1 » designent la
    meme chose.
    """

    numero: int = Field(..., ge=1, le=12, description="Ordre dans la session.")
    libelle: str = Field(..., min_length=1, max_length=50, examples=["S1"])
    date_debut: Optional[date] = None
    date_fin: Optional[date] = None
    actif: bool = True

    @field_validator("date_fin")
    @classmethod
    def _coherent(cls, valeur: Optional[date], info) -> Optional[date]:
        debut = info.data.get("date_debut")
        # Un semestre qui se termine avant de commencer n'est pas une faute de
        # saisie banale : personne ne peut le wanted sans le voir.
        if valeur and debut and valeur < debut:
            raise ValueError(
                "La fin du semestre ne peut pas précéder son début "
                f"({valeur} avant {debut})."
            )
        return valeur


class SemestreCreate(SemestreBase):
    model_config = ConfigDict(str_strip_whitespace=True)


class SemestreUpdate(BaseModel):
    """Mise a jour partielle. Seuls les champs envoyes sont touches."""

    model_config = ConfigDict(str_strip_whitespace=True)

    libelle: Optional[str] = Field(None, min_length=1, max_length=50)
    date_debut: Optional[date] = None
    date_fin: Optional[date] = None
    actif: Optional[bool] = None


class SemestreResponse(SemestreBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    #: Nombre d'UE rattachees. Un semestre sans UE ne peut pas figurer sur un
    #: bulletin : l'agent doit le voir avant de chercher pourquoi sa promotion
    #: ne sort pas.
    nb_unites: int = 0
    #: Nombre d'etudiants concernes, quand la session est connue.
    nb_etudiants: int = 0


class SemestreRepartition(BaseModel):
    """Repartition d'une session en semestres, pour l'ecran de synthese."""

    session_id: str
    session_nom: Optional[str] = None
    semestres: List[SemestreResponse] = Field(default_factory=list)
    #: UE sans semestre rattache. Elles n'entrent dans aucun bulletin : on les
    #: compte plutot que de les repartir au hasard.
    unites_sans_semestre: int = 0


__all__ = [
    "SemestreCreate",
    "SemestreRepartition",
    "SemestreResponse",
    "SemestreUpdate",
]
