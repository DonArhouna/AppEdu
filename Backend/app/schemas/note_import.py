"""Schemas de l'import de notes.

Le rapport est renvoye **en entier** a l'ecran, y compris les erreurs : c'est
ce qui permet a l'agent de voir « ces 3 lignes ont echoue » avant de valider.
Tronquer une liste d'erreurs pour alleger la reponse serait le pire des deux
maux : il corrigerait le fichier, ou il ne verrait pas le probleme.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EvaluationColonne(BaseModel):
    """Une colonne du tableur, interpretee comme evaluation."""

    nom: str
    #: Position dans le fichier, en 1-based, telle que l'agent la voit.
    colonne: int
    coefficient: float
    #: ``CC`` ou ``Examen Final`` : ce que le serveur en fera.
    type: str
    #: false si l'evaluation existe deja pour cette matiere et cette session.
    nouvelle: bool


class AnalyseNotesLigne(BaseModel):
    """Une ligne du fichier, et ce qu'on peut en faire."""

    numero: int
    matricule: Optional[str] = None
    nom_complet: str = ""
    etudiant_id: Optional[str] = None
    #: Notes lues, indexees par evaluation. Une valeur absente signifie
    #: « non evalue » — ce qui n'est pas un zero.
    notes: Dict[str, Optional[float]] = Field(default_factory=dict)
    a_creer: int = 0
    a_modifier: int = 0
    erreurs: List[str] = Field(default_factory=list)
    #: Ligne vide du tableur, ou entierement sans note : ni erreur ni ecriture.
    ignoree: bool = False


class AnalyseNotesReponse(BaseModel):
    """Rapport complet d'une analyse, sans aucune ecriture."""

    evaluations: List[EvaluationColonne] = Field(default_factory=list)
    lignes: List[AnalyseNotesLigne] = Field(default_factory=list)
    classe: Optional[Dict[str, Any]] = None
    matiere: Optional[Dict[str, Any]] = None
    session: Optional[Dict[str, Any]] = None
    resume: Dict[str, Any] = Field(default_factory=dict)
    #: false lorsqu'aucune note ne peut etre enregistree : le bouton de
    #: validation doit alors etre indisponible, et non produire un import vide.
    importable: bool = False
    #: Le contexte de l'import, tel que l'analyse l'a recu. Il est **renvoye**
    #: et non recalcule a la validation : le rapport est le contrat, et la
    #: validation ne peut donc faire que ce que l'analyse a montre.
    #:
    #: La reponse declare ce champ plutot que de l'ajouter apres coup : un
    #: client qui l'ignore doit pouvoir le voir. Une validation sans semestre
    #: ecrirait des notes sans semestre en paraissant avoir suivi l'analyse.
    #:
    #: ``semestre_id`` est indispensable a un enseignement annuel, note sur
    #: chaque semestre. ``rattrapage`` dit que les notes **remplacent** la
    #: premiere tentative sur ce semestre, au lieu de s'y ajouter.
    #:
    #: Le champ ne s'appelle pas ``import`` : c'est un mot-cle Python. Un alias
    #: aurait garde le nom dans le JSON tout en etant un piege a lire.
    contexte: Dict[str, Any] = Field(default_factory=dict)


class ImportNotesBilan(BaseModel):
    """Ce qui a reellement ete ecrit."""

    evaluations: int
    lignes: int
    #: Total annonce par l'analyse, et confirme — ou non — a l'ecriture.
    total_notes: int
    notes_creees: int
    notes_modifiees: int
    lignes_en_erreur: int
    total_erreurs: int
    creees: int
    modifiees: int
    lignes_ignorees: int


__all__ = [
    "AnalyseNotesLigne",
    "AnalyseNotesReponse",
    "EvaluationColonne",
    "ImportNotesBilan",
]
