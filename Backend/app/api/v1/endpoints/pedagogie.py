"""
Endpoints Pédagogie & Délibération :
- Cours & Emplois du temps
- Examens & Évaluations
- Saisie des Notes (unitaire et bulk)
- Gestion des Absences & Assiduité
- Moteur de Délibération ECTS / LMD
"""

from typing import List, Optional
import json
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
from app.services import edt_service
from app.models.etudiant import Etudiant
from app.models.pedagogie import Cours, Examen, Note, Absence
from app.models.structure import Filiere, Matiere, UniteEnseignement
from app.models.utilisateur import Utilisateur, UserRole
from app.schemas.pedagogie import (
    CoursResponse, CoursCreate, CoursUpdate,
    ExamenResponse, ExamenCreate,
    NoteResponse, NoteCreate, NoteUpdate, NoteBulkCreate,
    AbsenceResponse, AbsenceCreate,
    )
from app.schemas.etudiant import EtudiantSummaryResponse


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

def _reponse_conflits(conflits) -> str:
    """409 lisible : l'essentiel en une phrase, le detail en annexe.

    La liste JSON complete est jointe a la fin du message : le frontend
    l'affiche telle quelle, et un client programme peut la parser.
    """
    resume = ", ".join(
        f"{c.matiere or c.cours_id} ({c.jour} {c.heure_debut}-{c.heure_fin})"
        for c in conflits[:3]
    )
    plus = "…" if len(conflits) > 3 else ""
    return (
        f"Conflit d'emploi du temps : {len(conflits)} séance(s) occupent déjà "
        f"cet emploi ({resume}{plus}). Détail : "
        f"conflits={json.dumps([c.model_dump() for c in conflits], ensure_ascii=False)}"
    )


async def _verifier_seance_edt(
    db: AsyncSession,
    *,
    jour_semaine: str,
    heure_debut: str,
    heure_fin: str,
    salle: str,
    enseignant_id: Optional[int],
    cours_exclu_id: Optional[str] = None,
    salle_modifiee: bool = True,
) -> None:
    """Les règles que toute séance publiée doit respecter.

    Trois refus distincts, chacun nommé : un jour ou des horaires que l'on
    ne sait pas lire (422), une salle declarée indisponible (422), une
    séance déjà posée sur le même créneau dans la même salle ou devant le
    même enseignant (409 — le créneau existe, il est pris).
    """
    if edt_service.jour_normalise(jour_semaine) is None:
        raise HTTPException(
            status_code=422,
            detail="Jour inconnu « %s ». Valeurs acceptées : %s."
            % (jour_semaine, ", ".join(edt_service.JOURS_OUVRABLES)),
        )
    if not edt_service.horaires_valides(heure_debut, heure_fin):
        raise HTTPException(
            status_code=422,
            detail=(
                "Horaires invalides : l'heure de fin doit suivre l'heure de "
                "début, au format HH:MM."
            ),
        )
    salle_enregistree = await edt_service.salle_par_nom(db, salle)
    if salle_modifiee and salle_enregistree is not None and not salle_enregistree.disponible:
        raise HTTPException(
            status_code=422,
            detail=(
                f"La salle « {salle_enregistree.nom} » est marquée indisponible "
                "et n'accepte pas de nouvelle séance."
            ),
        )
    conflits = await edt_service.trouver_conflits(
        db,
        jour_semaine=jour_semaine,
        heure_debut=heure_debut,
        heure_fin=heure_fin,
        salle=salle,
        enseignant_id=enseignant_id,
        cours_exclu_id=cours_exclu_id,
    )
    if conflits:
        raise HTTPException(status_code=409, detail=_reponse_conflits(conflits))


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
    await _verifier_seance_edt(
        db,
        jour_semaine=payload.jour_semaine,
        heure_debut=payload.heure_debut,
        heure_fin=payload.heure_fin,
        salle=payload.salle,
        enseignant_id=payload.enseignant_id,
    )
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
    # Les règles se verifient sur l'etat **resultant** de la modification,
    # pas sur la seule charge utile : changer la salle d'un cours sans
    # reverifier ses horaires laisserait un conflit passer. La salle, elle,
    # n'est « modifiée » que si la charge utile la change : un cours déjà
    # posé dans une salle devenue indisponible reste modifiable sur le
    # reste (enseignant, horaires), sinon plus aucune correction ne serait
    # possible sans déplacer d'abord le cours.
    await _verifier_seance_edt(
        db,
        jour_semaine=data.get("jour_semaine", cours.jour_semaine),
        heure_debut=start,
        heure_fin=end,
        salle=data.get("salle", cours.salle),
        enseignant_id=data.get("enseignant_id", cours.enseignant_id),
        cours_exclu_id=cours.id,
        salle_modifiee="salle" in data and data["salle"] != cours.salle,
    )
    for field, value in data.items():
        setattr(cours, field, value)
    await db.commit()
    await db.refresh(cours)
    return cours


@router.get(
    "/cours/conflits",
    response_model=List[edt_service.ConflitEdt],
    summary="Audit : lister les conflits d'emploi du temps existants",
)
async def list_conflits_cours(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_pedagogy_read),
):
    """Les paires de cours déjà en conflit dans l'emploi du temps publié.

    Le guard bloque désormais toute nouvelle séance contradictoire ; les
    conflits créés **avant** le guard, eux, restent en base. Cet audit les
    liste — par cours le plus récent, celui qui a pris le créneau — pour que
    l'administration sache quoi replanifier.
    """
    return await edt_service.lister_conflits_existants(db)


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

