"""
Endpoints Pédagogie & Délibération :
- Cours & Emplois du temps
- Examens & Évaluations
- Saisie des Notes (unitaire et bulk)
- Gestion des Absences & Assiduité
- Moteur de Délibération ECTS / LMD
"""

from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db, require_enseignant, require_pedagogie
from app.models.pedagogie import Cours, Examen, Note, Absence
from app.schemas.pedagogie import (
    CoursResponse, CoursCreate,
    ExamenResponse, ExamenCreate,
    NoteResponse, NoteCreate, NoteBulkCreate,
    AbsenceResponse, AbsenceCreate,
    DeliberationSingleRequest, DeliberationPromotionRequest,
    EtudiantDeliberationResult, PromotionDeliberationResult,
)
from app.services.deliberation_engine import DeliberationEngine, DeliberationConfig

router = APIRouter()


# ---------------------------------------------------------------------------
# COURS
# ---------------------------------------------------------------------------
@router.get("/cours", response_model=List[CoursResponse], summary="Lister les cours")
async def list_cours(matiere_id: Optional[str] = None, jour: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Cours)
    if matiere_id:
        stmt = stmt.where(Cours.matiere_id == matiere_id)
    if jour:
        stmt = stmt.where(Cours.jour_semaine == jour)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/cours", response_model=CoursResponse, status_code=status.HTTP_201_CREATED, summary="Créer un cours")
async def create_cours(payload: CoursCreate, db: AsyncSession = Depends(get_db), _auth=Depends(require_pedagogie)):
    cours = Cours(id=payload.id or str(uuid.uuid4()), **payload.model_dump(exclude={"id"}))
    db.add(cours)
    await db.commit()
    await db.refresh(cours)
    return cours


# ---------------------------------------------------------------------------
# EXAMENS
# ---------------------------------------------------------------------------
@router.get("/examens", response_model=List[ExamenResponse], summary="Lister les examens")
async def list_examens(session_id: Optional[str] = None, matiere_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Examen)
    if session_id:
        stmt = stmt.where(Examen.session_id == session_id)
    if matiere_id:
        stmt = stmt.where(Examen.matiere_id == matiere_id)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/examens", response_model=ExamenResponse, status_code=status.HTTP_201_CREATED, summary="Créer un examen")
async def create_examen(payload: ExamenCreate, db: AsyncSession = Depends(get_db), _auth=Depends(require_pedagogie)):
    examen = Examen(id=payload.id or str(uuid.uuid4()), **payload.model_dump(exclude={"id"}))
    db.add(examen)
    await db.commit()
    await db.refresh(examen)
    return examen


# ---------------------------------------------------------------------------
# NOTES
# ---------------------------------------------------------------------------
@router.get("/notes", response_model=List[NoteResponse], summary="Lister les notes")
async def list_notes(
    etudiant_id: Optional[str] = None,
    matiere_id: Optional[str] = None,
    examen_id: Optional[str] = None,
    session_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Note)
    if etudiant_id:
        stmt = stmt.where(Note.etudiant_id == etudiant_id)
    if matiere_id:
        stmt = stmt.where(Note.matiere_id == matiere_id)
    if examen_id:
        stmt = stmt.where(Note.examen_id == examen_id)
    if session_id:
        stmt = stmt.where(Note.session_id == session_id)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED, summary="Saisie unitaire d'une note")
async def create_note(payload: NoteCreate, db: AsyncSession = Depends(get_db), _auth=Depends(require_enseignant)):
    statut = "Validé" if payload.valeur >= 10.0 else "Rattrapage"
    note = Note(
        id=payload.id or str(uuid.uuid4()),
        etudiant_id=payload.etudiant_id,
        matiere_id=payload.matiere_id,
        examen_id=payload.examen_id,
        session_id=payload.session_id,
        valeur=payload.valeur,
        coefficient=payload.coefficient,
        appreciation=payload.appreciation,
        statut=statut,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


@router.post("/notes/bulk", response_model=List[NoteResponse], status_code=status.HTTP_201_CREATED, summary="Saisie des notes par lot")
async def bulk_create_notes(payload: NoteBulkCreate, db: AsyncSession = Depends(get_db), _auth=Depends(require_enseignant)):
    """Permet à l'enseignant de saisir toutes les notes d'une matière/examen en une seule requête."""
    creees = []
    for item in payload.notes:
        statut = "Validé" if item.valeur >= 10.0 else "Rattrapage"
        note = Note(
            id=str(uuid.uuid4()),
            etudiant_id=item.etudiant_id,
            matiere_id=payload.matiere_id,
            examen_id=payload.examen_id,
            session_id=payload.session_id,
            valeur=item.valeur,
            coefficient=item.coefficient,
            appreciation=item.appreciation,
            statut=statut,
        )
        db.add(note)
        creees.append(note)

    await db.commit()
    for n in creees:
        await db.refresh(n)
    return creees


# ---------------------------------------------------------------------------
# ABSENCES
# ---------------------------------------------------------------------------
@router.get("/absences", response_model=List[AbsenceResponse], summary="Lister les absences")
async def list_absences(etudiant_id: Optional[str] = None, justifiee: Optional[bool] = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Absence)
    if etudiant_id:
        stmt = stmt.where(Absence.etudiant_id == etudiant_id)
    if justifiee is not None:
        stmt = stmt.where(Absence.justifiee == justifiee)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/absences", response_model=AbsenceResponse, status_code=status.HTTP_201_CREATED, summary="Déclarer une absence")
async def create_absence(payload: AbsenceCreate, db: AsyncSession = Depends(get_db), _auth=Depends(require_enseignant)):
    absence = Absence(id=payload.id or str(uuid.uuid4()), **payload.model_dump(exclude={"id"}))
    db.add(absence)
    await db.commit()
    await db.refresh(absence)
    return absence


# ---------------------------------------------------------------------------
# MOTEUR DE DÉLIBÉRATION (ECTS / LMD)
# ---------------------------------------------------------------------------
@router.post("/deliberation/calculer-etudiant", response_model=EtudiantDeliberationResult, summary="Calculer délibération d'un étudiant")
async def calculer_deliberation_etudiant(payload: DeliberationSingleRequest, _auth=Depends(require_pedagogie)):
    """Calcule les moyennes d'UEs, crédits ECTS acquis, statut et mention pour un étudiant."""
    config = payload.config or DeliberationConfig()
    result = DeliberationEngine.calculer_etudiant(payload.etudiant, config=config)
    return result


@router.post("/deliberation/calculer-promotion", response_model=PromotionDeliberationResult, summary="Calculer délibération de cohorte")
async def calculer_deliberation_promotion(payload: DeliberationPromotionRequest, _auth=Depends(require_pedagogie)):
    """Calcule le PV de jury global d'une promotion/cohorte entière avec statistiques de réussite."""
    config = payload.config or DeliberationConfig()
    result = DeliberationEngine.calculer_promotion(payload.etudiants, config=config)
    return result
