"""Schemas de la configuration institutionnelle."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class IdentiteEtablissement(BaseModel):
    """Identite imprimable d'un etablissement.

    Les memes regles que le Setup Wizard : on ne peut pas corriger une
    configuration en saisissant une adresse de courriel invalide.
    """

    nom: str = Field(..., min_length=2, max_length=255)
    sigle: str = Field(..., min_length=2, max_length=50)
    adresse: Optional[str] = Field(None, max_length=500)
    telephone: Optional[str] = Field(None, max_length=50)
    email: EmailStr
    pays: Optional[str] = Field(None, max_length=100)
    devise: str = Field(..., min_length=3, max_length=10)

    @field_validator("sigle")
    @classmethod
    def _sigle_non_vide(cls, valeur: str) -> str:
        nettoye = valeur.strip()
        if len(nettoye) < 2:
            raise ValueError("Le sigle doit comporter au moins 2 caracteres.")
        return nettoye

    @field_validator("devise")
    @classmethod
    def _devise_majuscules(cls, valeur: str) -> str:
        return valeur.strip().upper()


class ConfigurationOut(BaseModel):
    """Configuration en vigueur, avec sa version."""

    model_config = ConfigDict(from_attributes=True)

    version: int = Field(..., description="Numero de la version en vigueur (0 = celle du Setup Wizard).")
    nom: str
    sigle: str
    adresse: Optional[str] = None
    telephone: Optional[str] = None
    email: str
    pays: Optional[str] = None
    devise: str
    annee_academique_active: Optional[str] = None
    logo_present: bool = Field(
        ..., description="Un logo est-il enregistre ? Faux si aucun ou si le fichier a disparu."
    )


class ConfigurationMajout(BaseModel):
    """Mise a jour de l'identite. Tous les champs sont optionnels.

    La normalisation est identique a celle du Setup Wizard : sans elle, on
    pourrait enregistrer la devise ``eur`` et la lire ``EUR`` partout sauf ici.
    """

    nom: Optional[str] = Field(None, min_length=2, max_length=255)
    sigle: Optional[str] = Field(None, min_length=2, max_length=50)
    adresse: Optional[str] = Field(None, max_length=500)
    telephone: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    pays: Optional[str] = Field(None, max_length=100)
    devise: Optional[str] = Field(None, min_length=3, max_length=10)

    @field_validator("sigle")
    @classmethod
    def _sigle_non_vide(cls, valeur: Optional[str]) -> Optional[str]:
        if valeur is None:
            return None
        nettoye = valeur.strip()
        if len(nettoye) < 2:
            raise ValueError("Le sigle doit comporter au moins 2 caracteres.")
        return nettoye

    @field_validator("devise")
    @classmethod
    def _devise_majuscules(cls, valeur: Optional[str]) -> Optional[str]:
        return valeur.strip().upper() if valeur is not None else None


class ConfigurationModifiee(BaseModel):
    """Reponse a une ecriture : la configuration et la version creee."""

    configuration: ConfigurationOut
    version: int
    modifications: dict = Field(
        ..., description="Champs modifies, avec leur valeur precedente."
    )


class VersionConfigurationOut(BaseModel):
    """Une entree de l'historique des versions."""

    model_config = ConfigDict(from_attributes=True)

    version: int
    nature: str
    modifications: dict
    logo_present: bool
    modifie_par_email: Optional[str] = None
    created_at: datetime
    #: Etat complet de la configuration a cette version. Permet de restaurer
    #: une version sans rejouer toute la chronologie.
    instantane: dict = Field(default_factory=dict)
