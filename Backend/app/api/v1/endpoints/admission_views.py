"""Vues de filtres enregistrées, privées par utilisateur."""

from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admissions_read, require_admissions_write
from app.models.admission_views import VueAdmissions
from app.models.utilisateur import Utilisateur
from app.schemas.admissions import (
    VueAdmissionsCreate,
    VueAdmissionsResponse,
    VueAdmissionsUpdate,
)

router = APIRouter()


async def _get_owned_view(
    db: AsyncSession,
    view_id: str,
    user_id: int,
) -> VueAdmissions:
    result = await db.execute(
        select(VueAdmissions).where(
            VueAdmissions.id == view_id,
            VueAdmissions.user_id == user_id,
        )
    )
    view = result.scalar_one_or_none()
    if not view:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vue introuvable.")
    return view


@router.get(
    "/vues",
    response_model=List[VueAdmissionsResponse],
    summary="Lister mes vues d'admissions",
)
async def list_admission_views(
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateur = Depends(require_admissions_read),
):
    result = await db.execute(
        select(VueAdmissions)
        .where(VueAdmissions.user_id == current_user.id)
        .order_by(VueAdmissions.nom.asc())
    )
    return list(result.scalars().all())


@router.post(
    "/vues",
    response_model=VueAdmissionsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enregistrer une vue d'admissions",
)
async def create_admission_view(
    payload: VueAdmissionsCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateur = Depends(require_admissions_write),
):
    existing = await db.execute(
        select(VueAdmissions.id).where(
            VueAdmissions.user_id == current_user.id,
            VueAdmissions.nom == payload.nom,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Une vue portant ce nom existe déjà.",
        )
    view = VueAdmissions(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        nom=payload.nom,
        filtres=payload.filtres.model_dump(mode="json", exclude_none=True),
    )
    db.add(view)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Une vue portant ce nom existe déjà.",
        ) from exc
    await db.refresh(view)
    return view


@router.put(
    "/vues/{view_id}",
    response_model=VueAdmissionsResponse,
    summary="Modifier une vue d'admissions",
)
async def update_admission_view(
    view_id: str,
    payload: VueAdmissionsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateur = Depends(require_admissions_write),
):
    view = await _get_owned_view(db, view_id, current_user.id)
    data = payload.model_dump(mode="json", exclude_unset=True)
    if "nom" in data and data["nom"] is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le nom d'une vue ne peut pas être null.",
        )
    if "filtres" in data and data["filtres"] is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Les filtres d'une vue ne peuvent pas être null.",
        )
    if "nom" in data and data["nom"] != view.nom:
        duplicate = await db.execute(
            select(VueAdmissions.id).where(
                VueAdmissions.user_id == current_user.id,
                VueAdmissions.nom == data["nom"],
                VueAdmissions.id != view_id,
            )
        )
        if duplicate.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Une vue portant ce nom existe déjà.",
            )
    for field, value in data.items():
        setattr(view, field, value)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Une vue portant ce nom existe déjà.",
        ) from exc
    await db.refresh(view)
    return view


@router.delete(
    "/vues/{view_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une vue d'admissions",
)
async def delete_admission_view(
    view_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateur = Depends(require_admissions_write),
):
    view = await _get_owned_view(db, view_id, current_user.id)
    await db.delete(view)
    await db.commit()
