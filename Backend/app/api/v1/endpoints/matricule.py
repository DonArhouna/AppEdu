"""Endpoints de la nomenclature de matricule.

La lecture est ouverte a qui peut lire la structure ; l'ecriture exige
``institution.settings``, comme le reste du parametrage : fixer la regle de
numerotation d'une institution n'est pas une decision d'un enseignant.

Changer la regle ne modifie **aucun** matricule deja attribue. C'est le point
essentiel, et il est annonce dans le resume : sinon un institut croirait
renommer ses dossiers, et les familles Gloucesteraient de doubles.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_academic_read, require_permission
from app.models.utilisateur import Utilisateur
from app.schemas.matricule import (
    JetonMatricule,
    MatriculeJetons,
    MatriculeParametresMaj,
    MatriculeParametresOut,
)
from app.services import matricule_service
from app.services.audit_service import record_audit_event
from app.services.matricule_service import ParametreMatriculeInvalide

logger = logging.getLogger(__name__)
router = APIRouter()

require_matricule_write = require_permission("institution.settings")

#: Description des jetons, servie au client. L'ecran n'invente pas la liste :
#: un jeton undocumented dans l'ecran mais refuse par le serveur fait un ecran
#: qui ment sur ses propres capacites.
JETONS: List[Dict[str, str]] = [
    {"jeton": "{annee}", "libelle": "Année en cours", "exemple": "2026"},
    {"jeton": "{filiere}", "libelle": "Code de la filière", "exemple": "GL"},
    {"jeton": "{numero}", "libelle": "Compteur séquentiel", "exemple": "0001"},
]


def _resume(regle, *, configuree: bool, auteur=None, maj_le=None) -> MatriculeParametresOut:
    return MatriculeParametresOut(
        modele=regle.modele,
        largeur_numero=regle.largeur_numero,
        demarrage=regle.demarrage,
        modele_depart=matricule_service.MODELE_DEPART,
        exemple=regle.apercu(),
        personnalisee=regle.modele != matricule_service.MODELE_DEPART
        or regle.largeur_numero != matricule_service.LARGEUR_DEPART
        or regle.demarrage != matricule_service.DEMARRAGE_DEPART,
        configuree=configuree,
        maj_par_email=getattr(auteur, "email", None) if auteur is not None else None,
        maj_le=maj_le,
    )


@router.get(
    "/matricule",
    response_model=MatriculeParametresOut,
    summary="Lire la nomenclature de matricule en vigueur",
)
async def lire_matricule(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_read),
):
    """La regle appliquee au prochain dossier cree.

    Absente de la base, la regle de depart est retournee : c'est l'etat d'une
    instance qui n'a jamais regle sa nomenclature, pas une panne.
    """

    from sqlalchemy import select

    from app.models.parametres_matricule import ParametresMatricule

    regle = await matricule_service.charger(db)
    ligne = (await db.execute(select(ParametresMatricule).limit(1))).scalars().first()
    return _resume(
        regle,
        configuree=ligne is not None,
        auteur=ligne.maj_par if ligne is not None else None,
        maj_le=ligne.updated_at if ligne is not None else None,
    )


@router.get(
    "/matricule/jetons",
    response_model=MatriculeJetons,
    summary="Jetons acceptes dans le modele de matricule",
)
async def lister_jetons(_auth=Depends(require_academic_read)):
    return MatriculeJetons(jetons=[JetonMatricule(**jeton) for jeton in JETONS])


@router.put(
    "/matricule",
    response_model=MatriculeParametresOut,
    summary="Fixer la nomenclature de matricule",
)
async def modifier_matricule(
    payload: MatriculeParametresMaj,
    db: AsyncSession = Depends(get_db),
    auteur: Utilisateur = Depends(require_matricule_write),
):
    """Fixe la regle appliquee aux **prochains** dossiers.

    Aucun matricule deja attribue n'est modifie. Le resume le dit explicitement,
    parce que l'inverse est la lecture naturelle — et la mauvaise.
    """

    try:
        ligne, resume = await matricule_service.enregistrer(
            db,
            modele=payload.modele,
            largeur_numero=payload.largeur_numero,
            demarrage=payload.demarrage,
            auteur_id=auteur.id,
        )
    except ParametreMatriculeInvalide as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    await record_audit_event(
        db,
        actor_id=auteur.id,
        actor_email=auteur.email,
        action="institution.matricule.updated",
        resource_type="parametres_matricule",
        resource_id=ligne.id,
        details={**resume, "matricules_existants_modifies": 0},
    )
    await db.commit()
    await db.refresh(ligne)

    return _resume(
        matricule_service.Nomenclature(
            modele=ligne.modele,
            largeur_numero=ligne.largeur_numero,
            demarrage=ligne.demarrage,
        ),
        configuree=True,
        auteur=ligne.maj_par,
        maj_le=ligne.updated_at,
    )


__all__ = ["router"]
