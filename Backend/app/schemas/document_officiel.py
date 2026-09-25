"""Schemas Pydantic des documents officiels."""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TypeDocumentOut(BaseModel):
    """Un type de document disponible, avec ses conditions."""

    code: str
    prefixe: str
    libelle: str
    description: str
    permission: str
    avec_tableau: bool
    #: Conditions a satisfaire pour pouvoir emettre le document.
    conditions: List[str] = Field(default_factory=list)


class DocumentOfficielOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type_document: str
    numero: str
    etudiant_id: str
    session_id: Optional[str] = None
    annee: int
    #: Chemin relatif du PDF dans le dossier de runtime (les octets restent
    #: hors base). Expose pour le support et le diagnostic disque.
    fichier: str = ""
    sha256: str
    taille_octets: int
    donnees: Dict[str, Any] = Field(default_factory=dict)
    reserves: List[str] = Field(default_factory=list)
    remplace_document_id: Optional[str] = None
    motif_duplicata: Optional[str] = None
    emis_par_id: Optional[int] = None
    emis_le: datetime
    delivre_le: Optional[date] = None
    created_at: Optional[datetime] = None


class DocumentOfficielListe(DocumentOfficielOut):
    """Version enrichie pour l'historique : identité de l'étudiant incluse."""

    etudiant_nom: Optional[str] = None
    etudiant_prenom: Optional[str] = None
    etudiant_matricule: Optional[str] = None
    libelle: Optional[str] = None


class EmissionDocumentRequest(BaseModel):
    """Demande d'emission d'un document."""

    type_document: str = Field(
        ...,
        description="certificat_scolarite, releve_notes ou quitus_financier",
    )
    session_id: Optional[str] = Field(
        None, description="Session de rattachement. Par defaut, la session active."
    )
    #: Mode apercu : reserve un numero sans produire le PDF.
    apercu: bool = Field(
        False, description="Reserver un numero sans generer le document."
    )


class DuplicataRequest(BaseModel):
    """Demande de duplicata d'un document existant."""

    motif: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Motif du duplicat : perte, vol, detruition, erreur de saisie.",
    )


class LotDocumentRequest(BaseModel):
    """Emission en serie pour une promotion ou une classe."""

    type_document: str = Field(...)
    classe_id: Optional[str] = Field(
        None, description="Classe dont emettre les documents."
    )
    session_id: Optional[str] = Field(
        None, description="Session cible. Par defaut, la session active."
    )
    #: Ne pas interrompre le lot au premier etudiant non eligible.
    ignorer_les_non_eligibles: bool = Field(
        True, description="Continuer malgré les dossiers non éligibles."
    )


class ResultatLigne(BaseModel):
    """Resultat d'une emission dans un lot."""

    etudiant_id: str
    matricule: Optional[str] = None
    nom: Optional[str] = None
    emis: bool
    numero: Optional[str] = None
    document_id: Optional[str] = None
    motif: Optional[str] = None


class LotDocumentResponse(BaseModel):
    """Bilan d'une emission en serie."""

    type_document: str
    emis: int
    echoues: int
    lignes: List[ResultatLigne] = Field(default_factory=list)


__all__ = [
    "DocumentOfficielListe",
    "DocumentOfficielOut",
    "DuplicataRequest",
    "EmissionDocumentRequest",
    "LotDocumentRequest",
    "LotDocumentResponse",
    "ResultatLigne",
    "TypeDocumentOut",
]
