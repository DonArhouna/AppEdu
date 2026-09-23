"""
Academic Sessions & Payment Periods Endpoints :
- GET / : Liste des sessions académiques avec leurs périodes de paiement associées
- GET /active : Retourne la session académique active
- GET /{session_id} : Détails d'une session
- POST / : Création d'une nouvelle session académique
- PUT /{session_id} : Mise à jour d'une session académique
- DELETE /{session_id} : Suppression d'une session
"""

from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, require_admin
from app.models.session_academique import SessionAcademique, PeriodePaiement
from app.schemas.session import (
    SessionAcademiqueCreate,
    SessionAcademiqueUpdate,
    SessionAcademiqueResponse,
    PeriodePaiementResponse,
)

router = APIRouter()


@router.get("/", response_model=List[SessionAcademiqueResponse], summary="Lister toutes les sessions académiques")
async def list_sessions(
    db: AsyncSession = Depends(get_db)
):
    """Retourne la liste de toutes les sessions académiques avec leurs périodes ordonnées."""
    stmt = (
        select(SessionAcademique)
        .options(selectinload(SessionAcademique.periodes))
        .order_by(SessionAcademique.date_debut.desc())
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    return sessions


@router.get("/active", response_model=SessionAcademiqueResponse, summary="Obtenir la session active")
async def get_active_session(
    db: AsyncSession = Depends(get_db)
):
    """Retourne la session académique actuellement active avec son calendrier de paiement."""
    stmt = (
        select(SessionAcademique)
        .options(selectinload(SessionAcademique.periodes))
        .where(SessionAcademique.statut == "active")
        .limit(1)
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        # Fallback vers la plus récente si aucune marquée explicitement "active"
        stmt_fallback = (
            select(SessionAcademique)
            .options(selectinload(SessionAcademique.periodes))
            .order_by(SessionAcademique.date_debut.desc())
            .limit(1)
        )
        res_fb = await db.execute(stmt_fallback)
        session = res_fb.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune session académique active n'a été trouvée."
        )
    return session


@router.get("/{session_id}", response_model=SessionAcademiqueResponse, summary="Détail d'une session")
async def get_session_by_id(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retourne une session académique spécifique par son identifiant."""
    stmt = (
        select(SessionAcademique)
        .options(selectinload(SessionAcademique.periodes))
        .where(SessionAcademique.id == session_id)
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session académique introuvable (ID: {session_id})"
        )
    return session


@router.get("/{session_id}/periodes", response_model=List[PeriodePaiementResponse], summary="Périodes de paiement d'une session")
async def get_session_periods(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retourne les périodes de paiement rattachées à la session."""
    stmt = (
        select(PeriodePaiement)
        .where(PeriodePaiement.session_id == session_id)
        .order_by(PeriodePaiement.ordre.asc())
    )
    result = await db.execute(stmt)
    periodes = result.scalars().all()
    return periodes


@router.post("/", response_model=SessionAcademiqueResponse, status_code=status.HTTP_201_CREATED, summary="Créer une session académique")
async def create_session(
    payload: SessionAcademiqueCreate,
    db: AsyncSession = Depends(get_db),
    _admin = Depends(require_admin)
):
    """Crée une nouvelle session académique avec ses périodes de paiement (Réservé ADMIN)."""
    # Vérifier l'unicité du code
    stmt_check = select(SessionAcademique).where(SessionAcademique.code == payload.code)
    res_check = await db.execute(stmt_check)
    if res_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Une session académique avec le code '{payload.code}' existe déjà."
        )

    session_id = payload.id or f"session-{payload.code.lower().replace(' ', '-')}"
    new_session = SessionAcademique(
        id=session_id,
        nom=payload.nom,
        code=payload.code,
        annee_academique=payload.annee_academique,
        date_debut=payload.date_debut,
        date_fin=payload.date_fin,
        statut=payload.statut,
        description=payload.description
    )
    db.add(new_session)

    if payload.periodes:
        for idx, p_in in enumerate(payload.periodes, start=1):
            periode = PeriodePaiement(
                id=p_in.id or str(uuid.uuid4()),
                session_id=session_id,
                nom=p_in.nom,
                mois=p_in.mois,
                date_echeance=p_in.date_echeance,
                montant_estime=p_in.montant_estime,
                pourcentage=p_in.pourcentage,
                ordre=p_in.ordre or idx
            )
            db.add(periode)

    await db.commit()

    # Recharger avec les relations
    stmt = (
        select(SessionAcademique)
        .options(selectinload(SessionAcademique.periodes))
        .where(SessionAcademique.id == session_id)
    )
    res = await db.execute(stmt)
    return res.scalar_one()
