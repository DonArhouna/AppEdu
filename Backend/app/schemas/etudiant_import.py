"""Schemas Pydantic de l'import massif d'etudiants."""

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

ModeImport = Literal["creation", "mise_a_jour"]


class ColonneImport(BaseModel):
    """Une colonne reconnue du fichier source."""

    source: str = Field(..., description="En-tête d'origine, tel que lu.")
    cible: str = Field(..., description="Champ métier correspondant.")


class AnalyseLigne(BaseModel):
    """Diagnostic d'une ligne du fichier."""

    ligne: int
    statut: Literal["valide", "erreur", "ignore"]
    action: Literal["creer", "mettre_a_jour", "aucune"] = "aucune"
    matricule: Optional[str] = None
    nom: Optional[str] = None
    prenom: Optional[str] = None
    filiere: Optional[str] = None
    niveau: Optional[str] = None
    email: Optional[str] = None
    erreurs: List[str] = Field(default_factory=list)
    avertissements: List[str] = Field(default_factory=list)


class AnalyseEtudiantsResponse(BaseModel):
    """Rapport d'analyse, avant toute ecriture metier."""

    batch_id: str
    nom_fichier: str
    format_source: str
    statut: str
    mode: ModeImport
    nb_lignes: int
    nb_creer: int
    nb_mettre_a_jour: int
    nb_erreurs: int
    nb_avertissements: int
    nb_ignorees: int
    colonnes_reconnues: List[ColonneImport]
    colonnes_ignorees: List[str]
    champs_obligatoires_manquants: List[str]
    lignes: List[AnalyseLigne]
    message: Optional[str] = None


class LigneImportResultat(BaseModel):
    """Resultat de l'ecriture d'une ligne."""

    ligne: int
    statut: str
    action: str
    matricule: Optional[str] = None
    etudiant_id: Optional[str] = None
    erreurs: List[str] = Field(default_factory=list)


class ValidationImportResponse(BaseModel):
    """Bilan de l'ecriture."""

    batch_id: str
    statut: str
    nb_importes: int
    nb_mises_a_jour: int
    nb_erreurs: int
    nb_ignorees: int
    lignes: List[LigneImportResultat]
    message: Optional[str] = None


class EtudiantImportRowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ligne: int
    statut: str
    action: str
    matricule: Optional[str] = None
    etudiant_id: Optional[str] = None
    erreurs: List[str] = Field(default_factory=list)
    avertissements: List[str] = Field(default_factory=list)
    donnees: Dict[str, object] = Field(default_factory=dict)


class EtudiantImportBatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nom_fichier: str
    format_source: str
    statut: str
    mode: str
    nb_lignes: int
    nb_creer: int
    nb_mettre_a_jour: int
    nb_erreurs: int
    nb_avertissements: int
    nb_importes: int
    nb_ignorees: int
    colonnes: Dict[str, object] = Field(default_factory=dict)
    message: Optional[str] = None
    cree_par_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EtudiantImportBatchDetail(EtudiantImportBatchOut):
    """Un lot avec ses lignes."""

    rows: List[EtudiantImportRowOut] = Field(default_factory=list)


class ColonneModele(BaseModel):
    """Documentation d'une colonne attendue par le fichier d'import."""

    colonne: str
    champ: str
    obligatoire: bool
    description: str
    exemples: List[str] = Field(default_factory=list)


class ModeleImportResponse(BaseModel):
    """Contrat du fichier attendu, sans aucune donnee fictive."""

    nom_fichier_suggere: str
    formats_acceptes: List[str]
    encodage: str
    separateurs_csv: List[str]
    colonnes: List[ColonneModele]
    notes: List[str]


__all__ = [
    "AnalyseEtudiantsResponse",
    "AnalyseLigne",
    "ColonneImport",
    "ColonneModele",
    "EtudiantImportBatchDetail",
    "EtudiantImportBatchOut",
    "EtudiantImportRowOut",
    "LigneImportResultat",
    "ModeImport",
    "ModeleImportResponse",
    "ValidationImportResponse",
]
