"""
Schémas Pydantic V2 des salles (lot 3).

Une salle est enfin une donnee : jusque-la, ``cours.salle`` portait un texte
libre et rien ne disait ce que l'institut possede comme lieux. La creation
comme la modification refusent un doublon de nom (casse ignoree) : deux
salles du meme nom rendraient la correspondance cours ↔ salle ambigue, et
c'est sur cette correspondance que repose la detection de conflits.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SalleBase(BaseModel):
    nom: str = Field(..., example="Amphi A")
    code: str = Field(..., example="AMPHI-A")
    campus_id: Optional[str] = None
    batiment: Optional[str] = Field(None, example="Bâtiment principal")
    etage: Optional[str] = Field(None, example="RDC")
    capacite: Optional[int] = Field(None, ge=0, example=150)
    type_salle: str = Field("Salle de classe", example="Amphithéâtre")
    equipements: Optional[str] = Field(None, example="Vidéoprojecteur, tableau blanc")
    disponible: bool = True


class SalleCreate(SalleBase):
    id: Optional[str] = None


class SalleUpdate(BaseModel):
    nom: Optional[str] = None
    code: Optional[str] = None
    campus_id: Optional[str] = None
    batiment: Optional[str] = None
    etage: Optional[str] = None
    capacite: Optional[int] = Field(None, ge=0)
    type_salle: Optional[str] = None
    equipements: Optional[str] = None
    disponible: Optional[bool] = None


class SalleResponse(SalleBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
