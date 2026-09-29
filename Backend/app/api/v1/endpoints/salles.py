"""
Endpoints Salles (lot 3) : inventaire des lieux et occupation par les cours.

Une salle se cree avec un nom unique (casse ignoree) : la detection de
conflits repose sur la correspondance entre ``cours.salle`` et ce nom, deux
salles homonymes la rendraient ambigue. La suppression d'une salle encore
citee par un cours est refusee en 409 motive : la detacher d'un coup ferait
disparaitre le lieu de courses planifiees, sans que personne ne l'ait decide.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_academic_read, require_academic_structure_write
from app.models.pedagogie import Cours
from app.models.salle import Salle
from app.schemas.salle import SalleCreate, SalleResponse, SalleUpdate

router = APIRouter()


async def _doublon_nom(db: AsyncSession, nom: str, exclu_id: Optional[str] = None) -> bool:
    stmt = select(Salle.id).where(func.lower(Salle.nom) == nom.strip().lower())
    if exclu_id:
        stmt = stmt.where(Salle.id != exclu_id)
    return (await db.execute(stmt)).scalars().first() is not None


async def _doublon_code(db: AsyncSession, code: str, exclu_id: Optional[str] = None) -> bool:
    stmt = select(Salle.id).where(func.lower(Salle.code) == code.strip().lower())
    if exclu_id:
        stmt = stmt.where(Salle.id != exclu_id)
    return (await db.execute(stmt)).scalars().first() is not None


@router.get("/salles", response_model=List[SalleResponse], summary="Lister les salles")
async def list_salles(
    campus_id: Optional[str] = None,
    disponible: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_read),
):
    stmt = select(Salle).order_by(Salle.nom)
    if campus_id:
        stmt = stmt.where(Salle.campus_id == campus_id)
    if disponible is not None:
        stmt = stmt.where(Salle.disponible == disponible)
    return (await db.execute(stmt)).scalars().all()


@router.post("/salles", response_model=SalleResponse, status_code=status.HTTP_201_CREATED, summary="Créer une salle")
async def create_salle(
    payload: SalleCreate,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_structure_write),
):
    if await _doublon_nom(db, payload.nom):
        raise HTTPException(
            status_code=409,
            detail=f"Une salle nommée « {payload.nom} » existe déjà.",
        )
    if await _doublon_code(db, payload.code):
        raise HTTPException(
            status_code=409,
            detail=f"Une salle avec le code '{payload.code}' existe déjà.",
        )
    salle = Salle(id=payload.id or str(uuid.uuid4()), **payload.model_dump(exclude={"id"}))
    db.add(salle)
    await db.commit()
    await db.refresh(salle)
    return salle


@router.get("/salles/{salle_id}", response_model=SalleResponse, summary="Détail d'une salle")
async def get_salle(
    salle_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_read),
):
    salle = await db.get(Salle, salle_id)
    if not salle:
        raise HTTPException(status_code=404, detail="Salle introuvable.")
    return salle


@router.put("/salles/{salle_id}", response_model=SalleResponse, summary="Modifier une salle")
async def update_salle(
    salle_id: str,
    payload: SalleUpdate,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_structure_write),
):
    salle = await db.get(Salle, salle_id)
    if not salle:
        raise HTTPException(status_code=404, detail="Salle introuvable.")
    data = payload.model_dump(exclude_unset=True)
    if "nom" in data and await _doublon_nom(db, data["nom"], exclu_id=salle.id):
        raise HTTPException(
            status_code=409,
            detail=f"Une salle nommée « {data['nom']} » existe déjà.",
        )
    if "code" in data and await _doublon_code(db, data["code"], exclu_id=salle.id):
        raise HTTPException(
            status_code=409,
            detail=f"Une salle avec le code '{data['code']}' existe déjà.",
        )
    for field, value in data.items():
        setattr(salle, field, value)
    await db.commit()
    await db.refresh(salle)
    return salle


@router.delete("/salles/{salle_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer une salle")
async def delete_salle(
    salle_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_structure_write),
):
    salle = await db.get(Salle, salle_id)
    if not salle:
        raise HTTPException(status_code=404, detail="Salle introuvable.")
    occupee = (
        await db.execute(
            select(Cours.id)
            .where(func.lower(Cours.salle) == salle.nom.strip().lower())
            .limit(1)
        )
    ).scalars().first()
    if occupee:
        raise HTTPException(
            status_code=409,
            detail=(
                f"La salle « {salle.nom} » est citée par des cours planifiés et ne "
                "peut pas être supprimée. Déplacez ces cours, ou marquez la salle "
                "comme indisponible."
            ),
        )
    await db.delete(salle)
    await db.commit()
