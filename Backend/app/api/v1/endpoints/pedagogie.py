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

from app.api.deps import (
    get_db,
    require_pedagogy_delete,
    require_pedagogy_grades_read,
    require_pedagogy_read,
    require_pedagogy_write,
)
from app.models.etudiant import Etudiant
from app.models.pedagogie import Cours, Examen, Note, Absence
from app.models.structure import Filiere, Matiere, UniteEnseignement
from app.models.utilisateur import Utilisateur, UserRole
from app.schemas.pedagogie import (
    CoursResponse, CoursCreate, CoursUpdate,
    ExamenResponse, ExamenCreate,
    NoteResponse, NoteCreate, NoteUpdate, NoteBulkCreate,
    AbsenceResponse, AbsenceCreate,
    DeliberationSingleRequest, DeliberationPromotionRequest,
    EtudiantDeliberationResult, PromotionDeliberationResult,
)
from app.schemas.etudiant import EtudiantSummaryResponse

from app.services.deliberation_engine import DeliberationEngine, DeliberationConfig

router = APIRouter()


async def _teacher_can_access_matiere(
    db: AsyncSession,
    user: Utilisateur,
    matiere_id: str | None,
) -> bool:
    """Vérifie qu'un enseignant ne manipule que ses matières affectées."""
    if user.role != UserRole.ENSEIGNANT.value:
        return True
    if not matiere_id:
        return False
    result = await db.execute(
        select(Cours.id)
        .where(Cours.enseignant_id == user.id, Cours.matiere_id == matiere_id)
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def _matiere_filiere(
    db: AsyncSession,
    matiere_id: str,
) -> tuple[str | None, str | None]:
    result = await db.execute(
        select(UniteEnseignement.filiere_id, Filiere.nom)
        .join(Filiere, Filiere.id == UniteEnseignement.filiere_id)
        .join(Matiere, Matiere.ue_id == UniteEnseignement.id)
        .where(Matiere.id == matiere_id)
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=404, detail="Matière introuvable.")
    return row


async def _validate_note_scope(
    db: AsyncSession,
    *,
    etudiant_id: str,
    matiere_id: str,
    session_id: str | None,
) -> None:
    """Vérifie la cohérence filière/session avant une saisie de note."""

    if not session_id:
        return
    etudiant = await db.get(Etudiant, etudiant_id)
    if etudiant is None:
        raise HTTPException(status_code=404, detail="Étudiant introuvable.")
    filiere_id, filiere_nom = await _matiere_filiere(db, matiere_id)
    if filiere_id and etudiant.filiere_id != filiere_id:
        raise HTTPException(
            status_code=422,
            detail="L'étudiant n'appartient pas à la filière de la matière sélectionnée.",
        )
    if not filiere_id and filiere_nom and etudiant.filiere != filiere_nom:
        raise HTTPException(
            status_code=422,
            detail="L'étudiant n'appartient pas à la filière de la matière sélectionnée.",
        )
    if etudiant.session_id != session_id:
        raise HTTPException(
            status_code=422,
            detail="L'étudiant n'est pas inscrit à la session sélectionnée.",
        )


# ---------------------------------------------------------------------------
# COURS
# ---------------------------------------------------------------------------
@router.get("/cours", response_model=List[CoursResponse], summary="Lister les cours")
async def list_cours(
    matiere_id: Optional[str] = None,
    jour: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateur = Depends(require_pedagogy_read),
):
    stmt = select(Cours)
    if matiere_id:
        stmt = stmt.where(Cours.matiere_id == matiere_id)
    if jour:
        stmt = stmt.where(Cours.jour_semaine == jour)
    if current_user.role == UserRole.ENSEIGNANT.value:
        stmt = stmt.where(Cours.enseignant_id == current_user.id)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/cours", response_model=CoursResponse, status_code=status.HTTP_201_CREATED, summary="Créer un cours")
async def create_cours(payload: CoursCreate, db: AsyncSession = Depends(get_db), _auth=Depends(require_pedagogy_write)):
    cours = Cours(id=payload.id or str(uuid.uuid4()), **payload.model_dump(exclude={"id"}))
    db.add(cours)
    await db.commit()
    await db.refresh(cours)
    return cours


@router.put("/cours/{cours_id}", response_model=CoursResponse, summary="Modifier un cours")
async def update_cours(
    cours_id: str,
    payload: CoursUpdate,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_pedagogy_write),
):
    cours = await db.get(Cours, cours_id)
    if not cours:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cours introuvable.")
    data = payload.model_dump(exclude_unset=True)
    start = data.get("heure_debut", cours.heure_debut)
    end = data.get("heure_fin", cours.heure_fin)
    if end <= start:
        raise HTTPException(status_code=422, detail="L'heure de fin doit être postérieure à l'heure de début.")
    for field, value in data.items():
        setattr(cours, field, value)
    await db.commit()
    await db.refresh(cours)
    return cours


@router.delete("/cours/{cours_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer un cours")
async def delete_cours(
    cours_id: str,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_pedagogy_delete),
):
    cours = await db.get(Cours, cours_id)
    if not cours:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cours introuvable.")
    await db.delete(cours)
    await db.commit()


# ---------------------------------------------------------------------------
# EXAMENS
# ---------------------------------------------------------------------------
@router.get("/examens", response_model=List[ExamenResponse], summary="Lister les examens")
async def list_examens(
    session_id: Optional[str] = None,
    matiere_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateur = Depends(require_pedagogy_read),
):
    stmt = select(Examen)
    if session_id:
        stmt = stmt.where(Examen.session_id == session_id)
    if matiere_id:
        stmt = stmt.where(Examen.matiere_id == matiere_id)
    if current_user.role == UserRole.ENSEIGNANT.value:
        assigned_matiere_ids = select(Cours.matiere_id).where(Cours.enseignant_id == current_user.id)
        stmt = stmt.where(Examen.matiere_id.in_(assigned_matiere_ids))
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/examens", response_model=ExamenResponse, status_code=status.HTTP_201_CREATED, summary="Créer un examen")
async def create_examen(payload: ExamenCreate, db: AsyncSession = Depends(get_db), _auth=Depends(require_pedagogy_write)):
    examen = Examen(id=payload.id or str(uuid.uuid4()), **payload.model_dump(exclude={"id"}))
    db.add(examen)
    await db.commit()
    await db.refresh(examen)
    return examen


@router.get(
    "/etudiants-assignes",
    response_model=List[EtudiantSummaryResponse],
    summary="Liste minimale des étudiants d'une matière et session",
)
async def list_assigned_students(
    matiere_id: str = Query(..., min_length=1),
    session_id: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateur = Depends(require_pedagogy_read),
):
    """Limite la saisie enseignant à sa matière et à la session choisie.

    Le futur modèle Classe/Inscription remplacera ce scopage de transition sans casser
    le contrat : la réponse restera une liste minimale d'étudiants autorisés.
    """

    if not await _teacher_can_access_matiere(db, current_user, matiere_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cette matière ne vous est pas affectée.",
        )

    filiere_id, filiere_nom = await _matiere_filiere(db, matiere_id)
    stmt = select(Etudiant).where(Etudiant.session_id == session_id)
    if filiere_id:
        stmt = stmt.where(Etudiant.filiere_id == filiere_id)
    elif filiere_nom:
        stmt = stmt.where(Etudiant.filiere == filiere_nom)
    else:
        return []

    stmt = stmt.order_by(Etudiant.nom.asc(), Etudiant.prenom.asc())
    result = await db.execute(stmt)
    return result.scalars().all()


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
    current_user: Utilisateur = Depends(require_pedagogy_grades_read),
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
    if current_user.role == UserRole.ENSEIGNANT.value:
        assigned_matiere_ids = select(Cours.matiere_id).where(Cours.enseignant_id == current_user.id)
        stmt = stmt.where(Note.matiere_id.in_(assigned_matiere_ids))
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED, summary="Saisie unitaire d'une note")
async def create_note(payload: NoteCreate, db: AsyncSession = Depends(get_db), current_user: Utilisateur = Depends(require_pedagogy_write)):
    if current_user.role == UserRole.ENSEIGNANT.value and not payload.session_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La session est obligatoire pour saisir une note.",
        )
    if not await _teacher_can_access_matiere(db, current_user, payload.matiere_id):
        raise HTTPException(status_code=403, detail="Cette matière ne vous est pas affectée.")
    await _validate_note_scope(
        db,
        etudiant_id=payload.etudiant_id,
        matiere_id=payload.matiere_id,
        session_id=payload.session_id,
    )
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
        saisi_par_id=current_user.id,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


@router.put("/notes/{note_id}", response_model=NoteResponse, summary="Modifier une note")
async def update_note(
    note_id: str,
    payload: NoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateur = Depends(require_pedagogy_write),
):
    note = await db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note introuvable.")
    if not await _teacher_can_access_matiere(db, current_user, note.matiere_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cette note ne vous est pas affectée.")
    effective_session_id = payload.session_id or note.session_id
    if current_user.role == UserRole.ENSEIGNANT.value and not effective_session_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La session est obligatoire pour modifier une note.",
        )
    if payload.matiere_id and not await _teacher_can_access_matiere(db, current_user, payload.matiere_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="La nouvelle matière ne vous est pas affectée.")
    await _validate_note_scope(
        db,
        etudiant_id=note.etudiant_id,
        matiere_id=payload.matiere_id or note.matiere_id,
        session_id=effective_session_id,
    )
    data = payload.model_dump(exclude_unset=True)
    if data.get("valeur") is not None:
        data["statut"] = "Validé" if data["valeur"] >= 10.0 else "Rattrapage"
    for field, value in data.items():
        setattr(note, field, value)
    await db.commit()
    await db.refresh(note)
    return note


@router.post("/notes/bulk", response_model=List[NoteResponse], status_code=status.HTTP_201_CREATED, summary="Saisie des notes par lot")
async def bulk_create_notes(payload: NoteBulkCreate, db: AsyncSession = Depends(get_db), current_user: Utilisateur = Depends(require_pedagogy_write)):
    """Permet à l'enseignant de saisir toutes les notes d'une matière/examen en une seule requête."""
    if current_user.role == UserRole.ENSEIGNANT.value and not payload.session_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La session est obligatoire pour saisir des notes.",
        )
    if not await _teacher_can_access_matiere(db, current_user, payload.matiere_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cette matière ne vous est pas affectée.")
    for item in payload.notes:
        await _validate_note_scope(
            db,
            etudiant_id=item.etudiant_id,
            matiere_id=payload.matiere_id,
            session_id=payload.session_id,
        )
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
            saisi_par_id=current_user.id,
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
async def list_absences(
    etudiant_id: Optional[str] = None,
    justifiee: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateur = Depends(require_pedagogy_read),
):
    stmt = select(Absence)
    if etudiant_id:
        stmt = stmt.where(Absence.etudiant_id == etudiant_id)
    if justifiee is not None:
        stmt = stmt.where(Absence.justifiee == justifiee)
    if current_user.role == UserRole.ENSEIGNANT.value:
        assigned_cours_ids = select(Cours.id).where(Cours.enseignant_id == current_user.id)
        assigned_matiere_ids = select(Cours.matiere_id).where(Cours.enseignant_id == current_user.id)
        stmt = stmt.where(
            Absence.cours_id.in_(assigned_cours_ids) | Absence.matiere_id.in_(assigned_matiere_ids)
        )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/absences", response_model=AbsenceResponse, status_code=status.HTTP_201_CREATED, summary="Déclarer une absence")
async def create_absence(payload: AbsenceCreate, db: AsyncSession = Depends(get_db), current_user: Utilisateur = Depends(require_pedagogy_write)):
    if current_user.role == UserRole.ENSEIGNANT.value and not payload.session_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La session est obligatoire pour déclarer une absence.",
        )
    if not await _teacher_can_access_matiere(db, current_user, payload.matiere_id):
        if payload.cours_id:
            course_access = await db.execute(
                select(Cours.id).where(
                    Cours.id == payload.cours_id,
                    Cours.enseignant_id == current_user.id,
                )
            )
            if course_access.scalar_one_or_none() is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ce cours ne vous est pas affecté.")
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="La matière ne vous est pas affectée.")
    if payload.matiere_id and payload.session_id:
        await _validate_note_scope(
            db,
            etudiant_id=payload.etudiant_id,
            matiere_id=payload.matiere_id,
            session_id=payload.session_id,
        )
    absence = Absence(id=payload.id or str(uuid.uuid4()), **payload.model_dump(exclude={"id"}))
    db.add(absence)
    await db.commit()
    await db.refresh(absence)
    return absence


# ---------------------------------------------------------------------------
# MOTEUR DE DÉLIBÉRATION (ECTS / LMD)
# ---------------------------------------------------------------------------
@router.post("/deliberation/calculer-etudiant", response_model=EtudiantDeliberationResult, summary="Calculer délibération d'un étudiant")
async def calculer_deliberation_etudiant(payload: DeliberationSingleRequest, _auth=Depends(require_pedagogy_write)):
    """Calcule les moyennes d'UEs, crédits ECTS acquis, statut et mention pour un étudiant."""
    config = payload.config or DeliberationConfig()
    result = DeliberationEngine.calculer_etudiant(payload.etudiant, config=config)
    return result


@router.post("/deliberation/calculer-promotion", response_model=PromotionDeliberationResult, summary="Calculer délibération de cohorte")
async def calculer_deliberation_promotion(payload: DeliberationPromotionRequest, _auth=Depends(require_pedagogy_write)):
    """Calcule le PV de jury global d'une promotion/cohorte entière avec statistiques de réussite."""
    config = payload.config or DeliberationConfig()
    result = DeliberationEngine.calculer_promotion(payload.etudiants, config=config)
    return result
