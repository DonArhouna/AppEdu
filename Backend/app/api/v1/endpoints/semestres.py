"""Endpoints des semestres d'une session.

Un semestre est une **donnee de l'institut**, pas une etiquette : il a un
numero, un libelle et des dates. Le lire et le modifier releve de
``academic.write``, comme toute la structure ; le voir est ouvert a qui lit la
structure.

Une session est creee avec deux semestres vides (``S1``, ``S2``). C'est le
modele LMD le plus courant, et **creer une session n'oblige pas a les
utiliser** : un institut annuel n'en utilise qu'un, et un institut en trois
periodes en ajoute. En revanche, ne pas les prevoir obligerait chaque
institut a les creer apres coup — donc a les saisir n'importe comment.
"""

from __future__ import annotations

import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_academic_read, require_academic_write
from app.models.academic import Inscription
from app.models.session_academique import SessionAcademique
from app.models.structure import Semestre, UniteEnseignement
from app.schemas.semestre import (
    SemestreCreate,
    SemestreRepartition,
    SemestreResponse,
    SemestreUpdate,
)
from app.services.audit_service import record_audit_event

logger = logging.getLogger(__name__)
router = APIRouter()


async def _compter_unites(db: AsyncSession, semestre_id: str) -> int:
    return int(
        (
            await db.execute(
                select(func.count(UniteEnseignement.id)).where(
                    UniteEnseignement.semestre_id == semestre_id
                )
            )
        ).scalar()
        or 0
    )


async def _compter_etudiants(db: AsyncSession, session_id: str) -> int:
    return int(
        (
            await db.execute(
                select(func.count(func.distinct(Inscription.etudiant_id))).where(
                    Inscription.session_id == session_id
                )
            )
        ).scalar()
        or 0
    )


def _vers_reponse(
    semestre: Semestre, *, nb_unites: int, nb_etudiants: int
) -> SemestreResponse:
    return SemestreResponse(
        id=semestre.id,
        session_id=semestre.session_id,
        numero=semestre.numero,
        libelle=semestre.libelle,
        date_debut=semestre.date_debut,
        date_fin=semestre.date_fin,
        actif=semestre.actif,
        nb_unites=nb_unites,
        nb_etudiants=nb_etudiants,
    )


@router.get(
    "/semestres/repartition",
    response_model=SemestreRepartition,
    summary="Repartition d'une session en semestres",
)
async def lire_repartition(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_read),
):
    """Les semestres d'une session, et ce qui n'y est pas rattache.

    Le compte des UE sans semestre est ce qui permet a l'agent de voir qu'une
    matiere sortira du bulletin : il est annonce plutot que de disparaitre du
    calcul en silence.
    """

    session = await db.get(SessionAcademique, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette session académique n'existe pas.",
        )

    semestres = list(
        (
            await db.execute(
                select(Semestre)
                .where(Semestre.session_id == session_id)
                .order_by(Semestre.numero)
            )
        ).scalars().all()
    )
    nb_etudiants = await _compter_etudiants(db, session_id)
    sans_semestre = int(
        (
            await db.execute(
                select(func.count(UniteEnseignement.id)).where(
                    UniteEnseignement.semestre_id.is_(None)
                )
            )
        ).scalar()
        or 0
    )

    return SemestreRepartition(
        session_id=session_id,
        session_nom=session.nom,
        semestres=[
            _vers_reponse(
                semestre,
                nb_unites=await _compter_unites(db, semestre.id),
                nb_etudiants=nb_etudiants,
            )
            for semestre in semestres
        ],
        unites_sans_semestre=sans_semestre,
    )


@router.get(
    "/semestres/{semestre_id}",
    response_model=SemestreResponse,
    summary="Lire un semestre",
)
async def lire_semestre(
    semestre_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_read),
):
    semestre = await db.get(Semestre, semestre_id)
    if semestre is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ce semestre n'existe pas.",
        )
    return _vers_reponse(
        semestre,
        nb_unites=await _compter_unites(db, semestre.id),
        nb_etudiants=await _compter_etudiants(db, semestre.session_id),
    )


@router.post(
    "/semestres",
    response_model=SemestreResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter un semestre a une session",
)
async def creer_semestre(
    payload: SemestreCreate,
    session_id: str,
    db: AsyncSession = Depends(get_db),
    auteur=Depends(require_academic_write),
):
    """Ajoute un semestre. Le numero est unique dans la session.

    Deux « semestre 1 » dans la meme annee rendraient la moyenne par semestre
    ambigue : on ne saurait pas laquelle des deux lire. L'unicite est donc
    refusee, pas silencieusement renumerotee.
    """

    session = await db.get(SessionAcademique, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette session académique n'existe pas.",
        )

    existant = (
        await db.execute(
            select(Semestre).where(
                Semestre.session_id == session_id, Semestre.numero == payload.numero
            )
        )
    ).scalars().first()
    if existant is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Le semestre n°{payload.numero} existe déjà pour cette session "
                   f"(« {existant.libelle} »). Choisissez un autre numéro, ou "
                   "modifiez celui-ci.",
        )

    semestre = Semestre(
        id=str(uuid.uuid4()),
        session_id=session_id,
        numero=payload.numero,
        libelle=payload.libelle,
        date_debut=payload.date_debut,
        date_fin=payload.date_fin,
        actif=payload.actif,
    )
    db.add(semestre)
    await db.flush()

    await record_audit_event(
        db,
        actor_id=auteur.id,
        actor_email=auteur.email,
        action="academic.semestre.created",
        resource_type="semestre",
        resource_id=semestre.id,
        details={"session_id": session_id, "numero": payload.numero,
                 "libelle": payload.libelle},
    )
    await db.commit()
    await db.refresh(semestre)

    return _vers_reponse(semestre, nb_unites=0, nb_etudiants=0)


@router.put(
    "/semestres/{semestre_id}",
    response_model=SemestreResponse,
    summary="Modifier un semestre",
)
async def modifier_semestre(
    semestre_id: str,
    payload: SemestreUpdate,
    db: AsyncSession = Depends(get_db),
    auteur=Depends(require_academic_write),
):
    """Modifie un semestre. Le **numero** n'est pas modifiable.

    Changer le numero apres coup deplacerait un semestre dans l'ordre des
    periodes sans que les bulletins deja emis changent — et ces bulletins-la
    dateraient d'une numerotation qui n'existe plus.
    """

    semestre = await db.get(Semestre, semestre_id)
    if semestre is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ce semestre n'existe pas.",
        )

    donnees = payload.model_dump(exclude_unset=True)
    avant = {
        "libelle": semestre.libelle,
        "date_debut": semestre.date_debut,
        "date_fin": semestre.date_fin,
        "actif": semestre.actif,
    }
    for champ, valeur in donnees.items():
        setattr(semestre, champ, valeur)

    # La coherence debut/fin est verifiee sur l'ensemble, pas seulement sur la
    # seule valeur envoyee : corriger la fin en laissant un debut incoherent
    # doit etre refuse aussi.
    if semestre.date_debut and semestre.date_fin and semestre.date_fin < semestre.date_debut:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La fin du semestre ne peut pas précéder son début.",
        )

    await db.flush()
    await record_audit_event(
        db,
        actor_id=auteur.id,
        actor_email=auteur.email,
        action="academic.semestre.updated",
        resource_type="semestre",
        resource_id=semestre.id,
        details={"avant": {k: str(v) for k, v in avant.items()},
                 "apres": {k: str(v) for k, v in donnees.items()}},
    )
    await db.commit()
    await db.refresh(semestre)

    return _vers_reponse(
        semestre,
        nb_unites=await _compter_unites(db, semestre.id),
        nb_etudiants=await _compter_etudiants(db, semestre.session_id),
    )


@router.delete(
    "/semestres/{semestre_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un semestre",
)
async def supprimer_semestre(
    semestre_id: str,
    db: AsyncSession = Depends(get_db),
    auteur=Depends(require_academic_write),
):
    """Supprime un semestre, et **rattache ses UE** a aucun semestre.

    Les UE ne sont pas supprimees : elles perdent leur rattachement et
    remontent dans le compte des « sans semestre », donc hors des bulletins
    suivants. Supprimer des UE parce qu'on a reorganise les periodes
    detruirait des matieres, et avec elles des notes.
    """

    semestre = await db.get(Semestre, semestre_id)
    if semestre is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ce semestre n'existe pas.",
        )

    orphelines = int(
        (
            await db.execute(
                select(func.count(UniteEnseignement.id)).where(
                    UniteEnseignement.semestre_id == semestre_id
                )
            )
        ).scalar()
        or 0
    )

    await db.delete(semestre)
    await db.flush()
    await record_audit_event(
        db,
        actor_id=auteur.id,
        actor_email=auteur.email,
        action="academic.semestre.deleted",
        resource_type="semestre",
        resource_id=semestre_id,
        details={"unites_detachees": orphelines},
    )
    await db.commit()

    logger.info(
        "Semestre %s supprime ; %d UE sans rattachement.", semestre_id, orphelines
    )


__all__ = ["router"]
