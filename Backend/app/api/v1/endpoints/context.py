"""Contexte global d'année académique de l'établissement."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import (
    get_current_active_user,
    get_db,
    require_academic_context,
)
from app.models.etablissement import Etablissement
from app.models.session_academique import SessionAcademique
from app.models.utilisateur import Utilisateur
from app.schemas.context import AcademicContextResponse, AcademicContextUpdate

router = APIRouter()


async def _get_etablissement(db: AsyncSession) -> Etablissement:
    result = await db.execute(
        select(Etablissement).order_by(Etablissement.created_at.asc()).limit(1)
    )
    etablissement = result.scalar_one_or_none()
    if not etablissement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="L'établissement n'est pas encore configuré.",
        )
    return etablissement


async def _get_session(db: AsyncSession, session_id: str | None) -> SessionAcademique | None:
    if not session_id:
        return None
    result = await db.execute(
        select(SessionAcademique)
        .options(selectinload(SessionAcademique.periodes))
        .where(SessionAcademique.id == session_id)
    )
    return result.scalar_one_or_none()


async def _build_context(db: AsyncSession, etablissement: Etablissement) -> AcademicContextResponse:
    session = await _get_session(db, etablissement.session_active_id)
    year = etablissement.annee_academique_active
    configured = bool(year)

    # Une instance existante peut avoir une session active avant la migration
    # du contexte. On l'affiche comme dérivée, sans inventer d'année.
    if not year:
        result = await db.execute(
            select(SessionAcademique)
            .options(selectinload(SessionAcademique.periodes))
            .where(SessionAcademique.statut == "active")
            .order_by(SessionAcademique.date_debut.desc())
            .limit(1)
        )
        session = result.scalar_one_or_none()
        if session:
            year = session.annee_academique
    if not year:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Aucune année académique active n'est configurée.",
        )

    return AcademicContextResponse(
        annee_academique=year,
        session_id=session.id if session else None,
        session=session,
        configuree=configured,
        updated_at=etablissement.updated_at,
    )


@router.get(
    "/academique",
    response_model=AcademicContextResponse,
    summary="Lire le contexte global d'année académique",
)
async def get_academic_context(
    db: AsyncSession = Depends(get_db),
    _auth: Utilisateur = Depends(get_current_active_user),
):
    etablissement = await _get_etablissement(db)
    return await _build_context(db, etablissement)


@router.put(
    "/academique",
    response_model=AcademicContextResponse,
    summary="Configurer le contexte global d'année académique",
)
async def update_academic_context(
    payload: AcademicContextUpdate,
    db: AsyncSession = Depends(get_db),
    _auth: Utilisateur = Depends(require_academic_context),
):
    etablissement = await _get_etablissement(db)
    session = await _get_session(db, payload.session_id)
    if payload.session_id and not session:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La session sélectionnée n'existe pas.",
        )
    if session and session.annee_academique != payload.annee_academique:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="L'année de la session ne correspond pas à l'année académique choisie.",
        )

    etablissement.annee_academique_active = payload.annee_academique
    etablissement.session_active_id = payload.session_id
    await db.commit()
    await db.refresh(etablissement)
    return await _build_context(db, etablissement)
