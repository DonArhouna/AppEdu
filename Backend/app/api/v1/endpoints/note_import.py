"""Endpoints de l'import de notes.

Le meme decouplage que l'import d'etudiants, et pour la meme raison :

1. ``POST /pedagogie/import/analyse`` lit le fichier et renvoie le
   rapport ligne a ligne, **sans ecrire la moindre note** ;
2. ``POST /pedagogie/import/valider`` ecrit ce que le rapport annonceait.

L'agent lit donc le rapport **avant** d'ecrire, et l'ecran ne peut pas
promettre autre chose que ce qu'il enregistre.

Une difference assumee : l'import d'etudiants conserve un lot en base, parce
qu'un fichier d'etudiants peut porter des milliers de lignes qu'on veut
rejouer. Ici, le lot tient dans la requete — un rapport de notes est petit et
sans donnee sensible — donc aucun stockage intermediaire n'est ajoute. C'est un
choix de simplicite, pas un oubli ; il serait a revoir si les promotions
deviennent tres larges.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permission
from app.models.utilisateur import Utilisateur
from app.schemas.note_import import (
    AnalyseNotesLigne,
    AnalyseNotesReponse,
    ImportNotesBilan,
)
from app.services import note_import_service as service
from app.services.audit_service import record_audit_event
from app.services.etudiant_import_service import ImportFormatInvalide
from app.services.note_import_service import ImportNotesInvalide

logger = logging.getLogger(__name__)
router = APIRouter()

#: Saisie de notes : teaching act, donc le meme droit que la saisie unitaire.
require_notes_write = require_permission("pedagogy.write")
require_notes_read = require_permission("pedagogy.read")

FORMATS = "utilisez un fichier .csv (UTF-8) ou .xlsx"


def _erreur(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
    )


def _rapport_vers_reponse(rapport) -> AnalyseNotesReponse:
    lignes: List[AnalyseNotesLigne] = []
    for ligne in rapport.lignes:
        lignes.append(AnalyseNotesLigne(
            numero=ligne.numero,
            matricule=ligne.matricule or None,
            nom_complet=ligne.nom_complet,
            etudiant_id=ligne.etudiant.id if ligne.etudiant is not None else None,
            notes={
                cle: valeur
                for cle, valeur in ligne.notes.items()
                if not cle.startswith("__")
            },
            a_creer=ligne.a_creer,
            a_modifier=ligne.a_modifier,
            erreurs=list(ligne.erreurs),
            ignoree=ligne.ignoree,
        ))
    return AnalyseNotesReponse(
        evaluations=rapport.evaluations,
        lignes=lignes,
        classe=rapport.classe,
        matiere=rapport.matiere,
        session=rapport.session,
        resume=rapport.resume(),
        importable=rapport.total_notes > 0,
    )


@router.get(
    "/import/modele",
    summary="Modèle de fichier pour l'import de notes",
)
async def modele_fichier(_auth=Depends(require_notes_read)):
    """La description du format attendu, sans aucune donnee d'etudiant.

    Un modele est un gabarit **vide** : il montre les colonnes sans les
    remplir. Un modele contenant de faux eleves serait recopie tel quel, et ses
    notes se retrouveraient dans la promotion.
    """

    return {
        "colonnes_identite": {
            "matricule": "préféré — identifie l'étudiant sans ambiguïté",
            "nom": "ou, avec « prénom », si la classe n'a pas d'homonyme",
            "prenom": "",
        },
        "colonnes_evaluation": "toute autre colonne",
        "exemple_entetes": [
            "Matricule", "Nom", "Prénom", "Devoir 1", "Devoir 2", "Examen:2",
        ],
        "regles": [
            "Un en-tête peut porter son coefficient après deux-points : "
            "« Examen:2 ». Sinon le poids est celui de la matière, pris sur "
            "sa fiche.",
            "s'applique à toutes.",
            "Une note se lit sur 20. La virgule décimale est acceptée : 12,5.",
            "Une cellule vide signifie « non évalué » : aucune note n'est "
            "créée. Un 0 saisi reste un 0.",
            "Un en-tête contenant « examen », « final », « partiel » ou "
            "« rattrapage » devient une épreuve ; tout le reste est un "
            "contrôle continu.",
        ],
        "fichiers_acceptes": FORMATS,
    }


@router.post(
    "/import/analyse",
    response_model=AnalyseNotesReponse,
    summary="Analyser un fichier de notes (dry-run)",
)
async def analyser_fichier(
    fichier: UploadFile = File(..., description=FORMATS),
    classe_id: str = Form(..., description="Promotion concernée."),
    matiere_id: str = Form(..., description="Matière concernée."),
    session_id: str = Form(..., description="Session concernée."),
    db: AsyncSession = Depends(get_db),
    _auth: Utilisateur = Depends(require_notes_write),
):
    """Lit le fichier et renvoie le rapport. **Aucune note n'est écrite.**

    Le classe, la matiere et la session sont choisis **ici** plutot que deduits
    du fichier : un tableur de notes ne les porte pas, et les deviner reviendrait
    a affecter des notes a la mauvaise matiere.

    Le coefficient par defaut vient de la **matiere**, il n'est pas demande.
    """

    raw = await fichier.read()
    try:
        rapport = await service.analyser(
            db,
            filename=fichier.filename or "notes.csv",
            raw=raw,
            classe_id=classe_id,
            matiere_id=matiere_id,
            session_id=session_id,
        )
    except (ImportFormatInvalide, ImportNotesInvalide) as exc:
        raise _erreur(exc) from exc

    return _rapport_vers_reponse(rapport)


@router.post(
    "/import/valider",
    response_model=ImportNotesBilan,
    status_code=status.HTTP_201_CREATED,
    summary="Enregistrer les notes annoncees par un rapport",
)
async def valider_import(
    rapport: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    auteur: Utilisateur = Depends(require_notes_write),
):
    """Ecrit les notes decrites par le rapport d'analyse.

    Le serveur ne relit pas le fichier : il ecrit ce que le rapport a annonce.
    C'est ce qui garantit que l'ecran ne montre jamais autre chose que ce qu'il
    enregistre.
    """

    lignes = rapport.get("lignes") or []
    evaluations = rapport.get("evaluations") or []
    if not evaluations:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rapport vide : relancez l'analyse avant de valider.",
        )
    if not lignes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Aucune ligne à importer. Relancez l'analyse.",
        )

    matiere_id = (rapport.get("matiere") or {}).get("id") or ""
    session_id = (rapport.get("session") or {}).get("id") or ""
    if not matiere_id or not session_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le rapport ne précise pas la matière ou la session. "
            "Relancez l'analyse.",
        )

    # Le rapport est reconstruit avec les memes types que l'analyse, afin que
    # la validation ne puisse pas diverger de ce qui a ete montre.
    reconstruite = service.RapportImportNotes(
        evaluations=evaluations,
        classe=rapport.get("classe"),
        matiere=rapport.get("matiere"),
        session=rapport.get("session"),
    )
    for entree in lignes:
        reconstruite.lignes.append(service.LigneNote(
            numero=int(entree.get("numero") or 0),
            matricule=str(entree.get("matricule") or ""),
            nom_complet=str(entree.get("nom_complet") or ""),
            # Les cles de notes sont renvoyees telles quelles : c'est le service
            # qui les normalise a la lecture. Les reaffecter ici reintroduirait
            # une seconde convention — et c'est exactement ce qui faisait
            # disparaitre les colonnes dont le nom contenait une espace.
            notes={
                str(cle): valeur
                for cle, valeur in (entree.get("notes") or {}).items()
            },
            a_creer=int(entree.get("a_creer") or 0),
            a_modifier=int(entree.get("a_modifier") or 0),
            erreurs=[str(message) for message in (entree.get("erreurs") or [])],
            ignoree=bool(entree.get("ignoree")),
        ))

    # L'etudiant est resolu par le matricule annonce : c'est ce que le
    # serveur a deja verifie lors de l'analyse.
    from sqlalchemy import select

    from app.models.etudiant import Etudiant

    classe_id = (rapport.get("classe") or {}).get("id") or ""
    etudiants = await service._etudiants_de_la_classe(db, classe_id)
    par_matricule = {
        str(etudiant.matricule or "").lower(): etudiant for etudiant in etudiants
    }
    for ligne in reconstruite.lignes:
        if ligne.matricule and not ligne.ignoree and not ligne.erreurs:
            ligne.etudiant = par_matricule.get(ligne.matricule.lower())

    try:
        bilan = await service.valider(
            db,
            rapport=reconstruite,
            matiere_id=matiere_id,
            session_id=session_id,
        )
    except ImportNotesInvalide as exc:
        await db.rollback()
        raise _erreur(exc) from exc

    await record_audit_event(
        db,
        actor_id=auteur.id,
        actor_email=auteur.email,
        action="pedagogie.notes.imported",
        resource_type="import_notes",
        resource_id=f"{matiere_id}:{session_id}",
        details={
            "classe_id": classe_id,
            "matiere_id": matiere_id,
            "session_id": session_id,
            **bilan,
        },
    )
    await db.commit()

    return ImportNotesBilan(**bilan)


__all__ = ["router"]
