"""
Endpoints Structure Académique :
Gestion hiérarchique : Campus -> Départements -> Filières -> UEs -> Matières
"""

from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, require_admin, require_staff
from app.models.structure import Campus, Departement, Filiere, UniteEnseignement, Matiere
from app.schemas.structure import (
    CampusResponse, CampusCreate, CampusUpdate,
    DepartementResponse, DepartementCreate, DepartementUpdate,
    FiliereResponse, FiliereCreate, FiliereUpdate,
    UEResponse, UECreate, UEUpdate,
    MatiereResponse, MatiereCreate, MatiereUpdate,
)

router = APIRouter()


def _campus_with_hierarchy():
    """Charge la hiérarchie complète avant la sérialisation async."""
    return select(Campus).options(
        selectinload(Campus.departements).selectinload(Departement.filieres)
    )


# ---------------------------------------------------------------------------
# CAMPUS
# ---------------------------------------------------------------------------
@router.get("/campuses", response_model=List[CampusResponse], summary="Lister tous les campus")
async def list_campuses(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_staff),
):
    stmt = _campus_with_hierarchy().order_by(Campus.nom)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/campuses", response_model=CampusResponse, status_code=status.HTTP_201_CREATED, summary="Créer un campus")
async def create_campus(payload: CampusCreate, db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    stmt_check = select(Campus).where(Campus.code == payload.code)
    res_check = await db.execute(stmt_check)
    if res_check.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Un campus avec le code '{payload.code}' existe déjà.")

    campus = Campus(id=payload.id or str(uuid.uuid4()), **payload.model_dump(exclude={"id"}))
    db.add(campus)
    await db.commit()
    result = await db.execute(_campus_with_hierarchy().where(Campus.id == campus.id))
    return result.scalar_one()


@router.get("/campuses/{campus_id}", response_model=CampusResponse, summary="Détail d'un campus")
async def get_campus(
    campus_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_staff),
):
    stmt = _campus_with_hierarchy().where(Campus.id == campus_id)
    res = await db.execute(stmt)
    campus = res.scalar_one_or_none()
    if not campus:
        raise HTTPException(status_code=404, detail="Campus introuvable.")
    return campus


@router.put("/campuses/{campus_id}", response_model=CampusResponse, summary="Modifier un campus")
async def update_campus(campus_id: str, payload: CampusUpdate, db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    stmt = select(Campus).where(Campus.id == campus_id)
    res = await db.execute(stmt)
    campus = res.scalar_one_or_none()
    if not campus:
        raise HTTPException(status_code=404, detail="Campus introuvable.")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(campus, k, v)
    await db.commit()
    result = await db.execute(_campus_with_hierarchy().where(Campus.id == campus_id))
    return result.scalar_one()


@router.delete("/campuses/{campus_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer un campus")
async def delete_campus(campus_id: str, db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    stmt = select(Campus).where(Campus.id == campus_id)
    res = await db.execute(stmt)
    campus = res.scalar_one_or_none()
    if not campus:
        raise HTTPException(status_code=404, detail="Campus introuvable.")
    await db.delete(campus)
    await db.commit()


# ---------------------------------------------------------------------------
# DÉPARTEMENTS
# ---------------------------------------------------------------------------
@router.get("/departements", response_model=List[DepartementResponse], summary="Lister les départements")
async def list_departements(
    campus_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_staff),
):
    stmt = select(Departement).options(selectinload(Departement.filieres))
    if campus_id:
        stmt = stmt.where(Departement.campus_id == campus_id)
    stmt = stmt.order_by(Departement.nom)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/departements", response_model=DepartementResponse, status_code=status.HTTP_201_CREATED, summary="Créer un département")
async def create_departement(payload: DepartementCreate, db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    stmt_check = select(Departement).where(Departement.code == payload.code)
    res_check = await db.execute(stmt_check)
    if res_check.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Un département avec le code '{payload.code}' existe déjà.")

    dept = Departement(id=payload.id or str(uuid.uuid4()), **payload.model_dump(exclude={"id"}))
    db.add(dept)
    await db.commit()
    result = await db.execute(
        select(Departement)
        .options(selectinload(Departement.filieres))
        .where(Departement.id == dept.id)
    )
    return result.scalar_one()


@router.get("/departements/{dept_id}", response_model=DepartementResponse, summary="Détail d'un département")
async def get_departement(
    dept_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_staff),
):
    stmt = select(Departement).options(selectinload(Departement.filieres)).where(Departement.id == dept_id)
    res = await db.execute(stmt)
    dept = res.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Département introuvable.")
    return dept


@router.put("/departements/{dept_id}", response_model=DepartementResponse, summary="Modifier un département")
async def update_departement(dept_id: str, payload: DepartementUpdate, db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    stmt = select(Departement).where(Departement.id == dept_id)
    res = await db.execute(stmt)
    dept = res.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Département introuvable.")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(dept, k, v)
    await db.commit()
    result = await db.execute(
        select(Departement)
        .options(selectinload(Departement.filieres))
        .where(Departement.id == dept_id)
    )
    return result.scalar_one()


@router.delete("/departements/{dept_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer un département")
async def delete_departement(dept_id: str, db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    stmt = select(Departement).where(Departement.id == dept_id)
    res = await db.execute(stmt)
    dept = res.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Département introuvable.")
    await db.delete(dept)
    await db.commit()


# ---------------------------------------------------------------------------
# FILIÈRES
# ---------------------------------------------------------------------------
@router.get("/filieres", response_model=List[FiliereResponse], summary="Lister les filières")
async def list_filieres(
    departement_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_staff),
):
    stmt = select(Filiere)
    if departement_id:
        stmt = stmt.where(Filiere.departement_id == departement_id)
    stmt = stmt.order_by(Filiere.nom)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/filieres", response_model=FiliereResponse, status_code=status.HTTP_201_CREATED, summary="Créer une filière")
async def create_filiere(payload: FiliereCreate, db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    stmt_check = select(Filiere).where(Filiere.code == payload.code)
    res_check = await db.execute(stmt_check)
    if res_check.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Une filière avec le code '{payload.code}' existe déjà.")

    fil = Filiere(id=payload.id or str(uuid.uuid4()), **payload.model_dump(exclude={"id"}))
    db.add(fil)
    await db.commit()
    await db.refresh(fil)
    return fil


@router.get("/filieres/{filiere_id}", response_model=FiliereResponse, summary="Détail d'une filière")
async def get_filiere(
    filiere_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_staff),
):
    stmt = select(Filiere).where(Filiere.id == filiere_id)
    res = await db.execute(stmt)
    fil = res.scalar_one_or_none()
    if not fil:
        raise HTTPException(status_code=404, detail="Filière introuvable.")
    return fil


@router.put("/filieres/{filiere_id}", response_model=FiliereResponse, summary="Modifier une filière")
async def update_filiere(filiere_id: str, payload: FiliereUpdate, db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    stmt = select(Filiere).where(Filiere.id == filiere_id)
    res = await db.execute(stmt)
    fil = res.scalar_one_or_none()
    if not fil:
        raise HTTPException(status_code=404, detail="Filière introuvable.")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(fil, k, v)
    await db.commit()
    await db.refresh(fil)
    return fil


@router.delete("/filieres/{filiere_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer une filière")
async def delete_filiere(filiere_id: str, db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    stmt = select(Filiere).where(Filiere.id == filiere_id)
    res = await db.execute(stmt)
    fil = res.scalar_one_or_none()
    if not fil:
        raise HTTPException(status_code=404, detail="Filière introuvable.")
    await db.delete(fil)
    await db.commit()


# ---------------------------------------------------------------------------
# UNITÉS D'ENSEIGNEMENT (UE)
# ---------------------------------------------------------------------------
@router.get("/ues", response_model=List[UEResponse], summary="Lister les UEs")
async def list_ues(
    filiere_id: Optional[str] = None,
    semestre: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_staff),
):
    stmt = select(UniteEnseignement).options(selectinload(UniteEnseignement.matieres))
    if filiere_id:
        stmt = stmt.where(UniteEnseignement.filiere_id == filiere_id)
    if semestre:
        stmt = stmt.where(UniteEnseignement.semestre == semestre)
    stmt = stmt.order_by(UniteEnseignement.code)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/ues", response_model=UEResponse, status_code=status.HTTP_201_CREATED, summary="Créer une UE")
async def create_ue(payload: UECreate, db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    stmt_check = select(UniteEnseignement).where(UniteEnseignement.code == payload.code)
    res_check = await db.execute(stmt_check)
    if res_check.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Une UE avec le code '{payload.code}' existe déjà.")

    ue_id = payload.id or str(uuid.uuid4())
    ue = UniteEnseignement(
        id=ue_id,
        nom=payload.nom,
        code=payload.code,
        credits=payload.credits,
        coefficient=payload.coefficient,
        heures=payload.heures,
        semestre=payload.semestre,
        niveau=payload.niveau,
        responsable=payload.responsable,
        filiere_id=payload.filiere_id
    )
    db.add(ue)

    if payload.matieres:
        for m_in in payload.matieres:
            m = Matiere(
                id=m_in.id or str(uuid.uuid4()),
                ue_id=ue_id,
                **m_in.model_dump(exclude={"id", "ue_id"})
            )
            db.add(m)

    await db.commit()

    stmt = select(UniteEnseignement).options(selectinload(UniteEnseignement.matieres)).where(UniteEnseignement.id == ue_id)
    res = await db.execute(stmt)
    return res.scalar_one()


@router.get("/ues/{ue_id}", response_model=UEResponse, summary="Détail d'une UE")
async def get_ue(
    ue_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_staff),
):
    stmt = select(UniteEnseignement).options(selectinload(UniteEnseignement.matieres)).where(UniteEnseignement.id == ue_id)
    res = await db.execute(stmt)
    ue = res.scalar_one_or_none()
    if not ue:
        raise HTTPException(status_code=404, detail="UE introuvable.")
    return ue


@router.put("/ues/{ue_id}", response_model=UEResponse, summary="Modifier une UE")
async def update_ue(ue_id: str, payload: UEUpdate, db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    stmt = select(UniteEnseignement).where(UniteEnseignement.id == ue_id)
    res = await db.execute(stmt)
    ue = res.scalar_one_or_none()
    if not ue:
        raise HTTPException(status_code=404, detail="UE introuvable.")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(ue, k, v)
    await db.commit()

    stmt = select(UniteEnseignement).options(selectinload(UniteEnseignement.matieres)).where(UniteEnseignement.id == ue_id)
    res = await db.execute(stmt)
    return res.scalar_one()


@router.delete("/ues/{ue_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer une UE")
async def delete_ue(ue_id: str, db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    stmt = select(UniteEnseignement).where(UniteEnseignement.id == ue_id)
    res = await db.execute(stmt)
    ue = res.scalar_one_or_none()
    if not ue:
        raise HTTPException(status_code=404, detail="UE introuvable.")
    await db.delete(ue)
    await db.commit()


# ---------------------------------------------------------------------------
# MATIÈRES (ECUE)
# ---------------------------------------------------------------------------
@router.get("/matieres", response_model=List[MatiereResponse], summary="Lister les matières")
async def list_matieres(
    ue_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_staff),
):
    stmt = select(Matiere)
    if ue_id:
        stmt = stmt.where(Matiere.ue_id == ue_id)
    stmt = stmt.order_by(Matiere.nom)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/matieres", response_model=MatiereResponse, status_code=status.HTTP_201_CREATED, summary="Créer une matière")
async def create_matiere(payload: MatiereCreate, db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    stmt_check = select(Matiere).where(Matiere.code == payload.code)
    res_check = await db.execute(stmt_check)
    if res_check.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Une matière avec le code '{payload.code}' existe déjà.")

    mat = Matiere(id=payload.id or str(uuid.uuid4()), **payload.model_dump(exclude={"id"}))
    db.add(mat)
    await db.commit()
    await db.refresh(mat)
    return mat


@router.get("/matieres/{matiere_id}", response_model=MatiereResponse, summary="Détail d'une matière")
async def get_matiere(
    matiere_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_staff),
):
    stmt = select(Matiere).where(Matiere.id == matiere_id)
    res = await db.execute(stmt)
    mat = res.scalar_one_or_none()
    if not mat:
        raise HTTPException(status_code=404, detail="Matière introuvable.")
    return mat


@router.put("/matieres/{matiere_id}", response_model=MatiereResponse, summary="Modifier une matière")
async def update_matiere(matiere_id: str, payload: MatiereUpdate, db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    stmt = select(Matiere).where(Matiere.id == matiere_id)
    res = await db.execute(stmt)
    mat = res.scalar_one_or_none()
    if not mat:
        raise HTTPException(status_code=404, detail="Matière introuvable.")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(mat, k, v)
    await db.commit()
    await db.refresh(mat)
    return mat


@router.delete("/matieres/{matiere_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer une matière")
async def delete_matiere(matiere_id: str, db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    stmt = select(Matiere).where(Matiere.id == matiere_id)
    res = await db.execute(stmt)
    mat = res.scalar_one_or_none()
    if not mat:
        raise HTTPException(status_code=404, detail="Matière introuvable.")
    await db.delete(mat)
    await db.commit()
