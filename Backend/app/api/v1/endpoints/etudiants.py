"""
Endpoints Gestion des Étudiants :
- Recherche multi-critères
- Création avec génération automatique de matricule
- Inscription et affectation de session
"""

from typing import List, Optional
from datetime import date
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.api.deps import (
    get_db,
    require_students_delete,
    require_students_directory_read,
    require_students_read,
    require_students_write,
)
from app.models.academic import Classe, Inscription, Niveau
from app.models.etudiant import Etudiant
from app.models.session_academique import SessionAcademique
from app.models.structure import Filiere
from app.services.academic_service import class_projections, get_classe, sync_active_inscription
from app.schemas.etudiant import (
    EtudiantResponse,
    EtudiantSummaryResponse,
    EtudiantCreate,
    EtudiantUpdate,
    EtudiantInscriptionRequest,
)
from app.services.matricule_service import generate_matricule

router = APIRouter()


def _student_options():
    return (
        selectinload(Etudiant.classe).selectinload(Classe.filiere),
        selectinload(Etudiant.classe).selectinload(Classe.niveau).selectinload(Niveau.cycle),
        selectinload(Etudiant.inscriptions),
    )


async def _load_etudiant(db: AsyncSession, etudiant_id: str) -> Optional[Etudiant]:
    result = await db.execute(
        select(Etudiant).options(*_student_options()).where(Etudiant.id == etudiant_id)
    )
    return result.scalar_one_or_none()


def _assert_class_projection_matches(
    classe: Classe,
    *,
    filiere_id: Optional[str],
    filiere: Optional[str],
    niveau: Optional[str],
) -> None:
    """Refuse un mélange silencieux entre IDs canoniques et texte legacy."""
    if filiere_id and filiere_id != classe.filiere_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La filière fournie ne correspond pas à la classe sélectionnée.",
        )
    if filiere and filiere.strip() and filiere.strip() != classe.filiere.nom:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le nom de filière fourni ne correspond pas à la classe sélectionnée.",
        )
    canonical_niveau = classe.niveau.nom or classe.niveau.code
    if niveau and niveau.strip() and niveau.strip() not in {
        canonical_niveau,
        classe.niveau.code,
    }:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le niveau fourni ne correspond pas à la classe sélectionnée.",
        )


async def _get_session(db: AsyncSession, session_id: Optional[str]) -> Optional[SessionAcademique]:
    if not session_id:
        return None
    return await db.get(SessionAcademique, session_id)


def _build_student_query(
    *,
    search: Optional[str],
    filiere: Optional[str],
    filiere_id: Optional[str],
    session_id: Optional[str],
    statut: Optional[str],
    niveau: Optional[str],
    classe_id: Optional[str] = None,
):
    stmt = select(Etudiant).options(*_student_options())
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Etudiant.nom.ilike(pattern),
                Etudiant.prenom.ilike(pattern),
                Etudiant.matricule.ilike(pattern),
                Etudiant.email.ilike(pattern),
            )
        )
    if filiere_id:
        stmt = stmt.where(Etudiant.filiere_id == filiere_id)
    elif filiere:
        stmt = stmt.where(Etudiant.filiere == filiere)
    if session_id:
        stmt = stmt.where(Etudiant.session_id == session_id)
    if classe_id:
        stmt = stmt.where(Etudiant.classe_id == classe_id)
    if statut:
        stmt = stmt.where(Etudiant.statut == statut)
    if niveau:
        stmt = stmt.where(Etudiant.niveau == niveau)
    return stmt


@router.get("/", response_model=List[EtudiantResponse], summary="Rechercher des étudiants")
async def list_etudiants(
    search: Optional[str] = Query(None, description="Nom, prénom, email ou matricule"),
    filiere: Optional[str] = None,
    filiere_id: Optional[str] = None,
    session_id: Optional[str] = None,
    statut: Optional[str] = None,
    niveau: Optional[str] = None,
    classe_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_students_read),
):
    """Recherche multi-critères réservée au registre académique complet."""
    stmt = _build_student_query(
        search=search,
        filiere=filiere,
        filiere_id=filiere_id,
        session_id=session_id,
        statut=statut,
        niveau=niveau,
        classe_id=classe_id,
    )
    stmt = stmt.order_by(Etudiant.nom.asc(), Etudiant.prenom.asc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get(
    "/summary",
    response_model=List[EtudiantSummaryResponse],
    summary="Répertoire étudiant minimal",
)
async def list_etudiant_summaries(
    search: Optional[str] = Query(None, description="Nom, prénom, email ou matricule"),
    filiere: Optional[str] = None,
    filiere_id: Optional[str] = None,
    session_id: Optional[str] = None,
    statut: Optional[str] = None,
    niveau: Optional[str] = None,
    classe_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_students_directory_read),
):
    """Retourne uniquement les champs nécessaires aux workflows financiers.

    Aucun email, téléphone, adresse, naissance ou photo n'est exposé. Le registre
    global reste volontairement inaccessible à l'enseignant.
    """

    stmt = _build_student_query(
        search=search,
        filiere=filiere,
        filiere_id=filiere_id,
        session_id=session_id,
        statut=statut,
        niveau=niveau,
        classe_id=classe_id,
    )
    stmt = stmt.order_by(Etudiant.nom.asc(), Etudiant.prenom.asc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/", response_model=EtudiantResponse, status_code=status.HTTP_201_CREATED, summary="Créer un étudiant")
async def create_etudiant(
    payload: EtudiantCreate,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_students_write),
):
    """Crée un étudiant via le chemin legacy ou Classe + Session.

    Le chemin canonique dérive les projections texte depuis la Classe et crée
    l'inscription active.  Sans identifiants de classe, les colonnes legacy
    sont simplement conservées ; aucune donnée n'est devinée.
    """
    classe = None
    filiere_id = payload.filiere_id
    filiere_text = payload.filiere
    niveau_text = payload.niveau

    if payload.classe_id:
        if not payload.session_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Une inscription canonique nécessite une session.",
            )
        classe = await get_classe(db, payload.classe_id)
        if classe is None:
            raise HTTPException(status_code=422, detail="La classe sélectionnée n'existe pas.")
        session = await _get_session(db, payload.session_id)
        if session is None:
            raise HTTPException(status_code=422, detail="La session sélectionnée n'existe pas.")
        _assert_class_projection_matches(
            classe,
            filiere_id=payload.filiere_id,
            filiere=payload.filiere,
            niveau=payload.niveau,
        )
        projections = class_projections(classe)
        filiere_id = projections["filiere_id"]
        filiere_text = projections["filiere"]
        niveau_text = projections["niveau"]
    else:
        if not filiere_id and not (filiere_text or "").strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La filière est obligatoire pour générer un matricule.",
            )
        if filiere_id:
            stmt_f = select(Filiere).where(Filiere.id == filiere_id)
            res_f = await db.execute(stmt_f)
            f_obj = res_f.scalar_one_or_none()
            if not f_obj:
                raise HTTPException(status_code=422, detail="La filière sélectionnée n'existe pas.")
            filiere_text = filiere_text or f_obj.nom
        if not (niveau_text or "").strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Le niveau est obligatoire sur le chemin legacy.",
            )
        if payload.session_id and await _get_session(db, payload.session_id) is None:
            raise HTTPException(status_code=422, detail="La session sélectionnée n'existe pas.")

    filiere_code = ""
    if classe is not None:
        filiere_code = classe.filiere.code
    elif filiere_id:
        f_obj = await db.get(Filiere, filiere_id)
        filiere_code = f_obj.code if f_obj else ""
    else:
        filiere_code = "".join(
            [word[0] for word in (filiere_text or "").split() if word]
        ).upper()[:4]

    matricule = payload.matricule
    if not matricule or not matricule.strip():
        matricule = await generate_matricule(db, filiere_code=filiere_code)

    # Vérification d'unicité du matricule
    stmt_check = select(Etudiant).where(Etudiant.matricule == matricule)
    res_check = await db.execute(stmt_check)
    if res_check.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Un étudiant avec le matricule '{matricule}' existe déjà.")

    etudiant = Etudiant(
        id=str(uuid.uuid4()),
        matricule=matricule,
        nom=payload.nom,
        prenom=payload.prenom,
        sexe=payload.sexe,
        email=str(payload.email) if payload.email else None,
        telephone=payload.telephone,
        date_naissance=payload.date_naissance,
        adresse=payload.adresse,
        filiere=filiere_text,
        filiere_id=filiere_id,
        niveau=niveau_text,
        classe_id=classe.id if classe is not None else None,
        statut=payload.statut,
        photo_url=payload.photo_url,
        date_inscription=payload.date_inscription or date.today(),
        session_id=payload.session_id,
    )
    db.add(etudiant)
    try:
        await db.flush()
        if classe is not None and payload.session_id:
            await sync_active_inscription(
                db,
                etudiant_id=etudiant.id,
                classe_id=classe.id,
                session_id=payload.session_id,
                date_inscription=etudiant.date_inscription,
            )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Impossible de créer l'étudiant ou son inscription active.",
        ) from exc
    loaded = await _load_etudiant(db, etudiant.id)
    return loaded


@router.get("/{etudiant_id}", response_model=EtudiantResponse, summary="Détail d'un étudiant")
async def get_etudiant(
    etudiant_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_students_read),
):
    etudiant = await _load_etudiant(db, etudiant_id)
    if not etudiant:
        raise HTTPException(status_code=404, detail="Étudiant introuvable.")
    return etudiant


@router.put("/{etudiant_id}", response_model=EtudiantResponse, summary="Modifier un étudiant")
async def update_etudiant(
    etudiant_id: str,
    payload: EtudiantUpdate,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_students_write),
):
    etudiant = await _load_etudiant(db, etudiant_id)
    if not etudiant:
        raise HTTPException(status_code=404, detail="Étudiant introuvable.")

    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"]:
        data["email"] = str(data["email"])

    target_class_id = data.get("classe_id", etudiant.classe_id)
    target_session_id = data.get("session_id", etudiant.session_id)
    classe = None
    if target_class_id:
        if not target_session_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Une classe canonique nécessite une session.",
            )
        classe = await get_classe(db, target_class_id)
        if classe is None:
            raise HTTPException(status_code=422, detail="La classe sélectionnée n'existe pas.")
        class_change_requested = "classe_id" in data and data["classe_id"] != etudiant.classe_id
        _assert_class_projection_matches(
            classe,
            filiere_id=data.get("filiere_id") if class_change_requested else etudiant.filiere_id,
            filiere=data.get("filiere") if class_change_requested else etudiant.filiere,
            niveau=data.get("niveau") if class_change_requested else etudiant.niveau,
        )
        projections = class_projections(classe)
        data["filiere_id"] = projections["filiere_id"]
        data["filiere"] = projections["filiere"]
        data["niveau"] = projections["niveau"]
        data["classe_id"] = classe.id
    elif "classe_id" in data and data["classe_id"] is None and etudiant.inscriptions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Impossible de détacher une classe possessing une inscription historique.",
        )

    if target_session_id and await _get_session(db, target_session_id) is None:
        raise HTTPException(status_code=422, detail="La session sélectionnée n'existe pas.")
    if "filiere_id" in data and data["filiere_id"] and not classe:
        if await db.get(Filiere, data["filiere_id"]) is None:
            raise HTTPException(status_code=422, detail="La filière sélectionnée n'existe pas.")

    try:
        for key, value in data.items():
            setattr(etudiant, key, value)
        if classe is not None and target_session_id:
            await sync_active_inscription(
                db,
                etudiant_id=etudiant.id,
                classe_id=classe.id,
                session_id=target_session_id,
            )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Conflit lors de la modification de l'étudiant.") from exc
    return await _load_etudiant(db, etudiant_id)


@router.delete("/{etudiant_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer un étudiant")
async def delete_etudiant(
    etudiant_id: str,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_students_delete),
):
    stmt = select(Etudiant).where(Etudiant.id == etudiant_id)
    res = await db.execute(stmt)
    etudiant = res.scalar_one_or_none()
    if not etudiant:
        raise HTTPException(status_code=404, detail="Étudiant introuvable.")
    inscriptions = await db.execute(
        select(Inscription.id).where(Inscription.etudiant_id == etudiant_id).limit(1)
    )
    if inscriptions.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="L'étudiant possède une inscription historique et ne peut pas être supprimé.",
        )
    try:
        await db.delete(etudiant)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="L'étudiant est référencé par une donnée historique.",
        ) from exc


@router.post("/{etudiant_id}/inscrire", response_model=EtudiantResponse, summary="Inscrire un étudiant à une session")
async def inscrire_etudiant(
    etudiant_id: str,
    payload: EtudiantInscriptionRequest,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_students_write),
):
    """Rattache un étudiant via Classe + Session ou via le chemin legacy.

    Le chemin canonique met à jour l'inscription active sans supprimer les
    lignes inactives.  Une session seule reste acceptée pour les anciennes
    fiches, mais ne fabrique aucune inscription normalisée.
    """
    etudiant = await _load_etudiant(db, etudiant_id)
    if not etudiant:
        raise HTTPException(status_code=404, detail="Étudiant introuvable.")
    if not payload.session_id:
        raise HTTPException(status_code=422, detail="La session est obligatoire.")

    session = await _get_session(db, payload.session_id)
    if session is None:
        raise HTTPException(status_code=422, detail="La session sélectionnée n'existe pas.")

    classe = None
    if payload.classe_id:
        classe = await get_classe(db, payload.classe_id)
        if classe is None:
            raise HTTPException(status_code=422, detail="La classe sélectionnée n'existe pas.")
        _assert_class_projection_matches(
            classe,
            filiere_id=payload.filiere_id,
            filiere=payload.filiere,
            niveau=payload.niveau,
        )
        projections = class_projections(classe)
        etudiant.classe_id = classe.id
        etudiant.filiere_id = projections["filiere_id"]
        etudiant.filiere = projections["filiere"]
        etudiant.niveau = projections["niveau"]
    else:
        if payload.filiere_id:
            if await db.get(Filiere, payload.filiere_id) is None:
                raise HTTPException(status_code=422, detail="La filière sélectionnée n'existe pas.")
            etudiant.filiere_id = payload.filiere_id
        if payload.filiere:
            etudiant.filiere = payload.filiere
        if payload.niveau:
            etudiant.niveau = payload.niveau

    etudiant.session_id = payload.session_id
    etudiant.statut = "Inscrit"
    try:
        if classe is not None:
            await sync_active_inscription(
                db,
                etudiant_id=etudiant.id,
                classe_id=classe.id,
                session_id=payload.session_id,
            )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Conflit lors de l'inscription.") from exc
    return await _load_etudiant(db, etudiant_id)
