"""Workflow d'admissions persistant et protégé par RBAC.

Le module couvre la candidature, le checklist documentaire, les décisions et la
conversion en dossier étudiant. Les fichiers sont écrits dans un stockage local
sécurisé et la base ne conserve que leur chemin relatif.
"""

from datetime import date, datetime, timezone
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, require_admissions
from app.models.admissions import Candidature, DecisionAdmission, PieceCandidature
from app.models.etudiant import Etudiant
from app.models.session_academique import SessionAcademique
from app.models.structure import Filiere
from app.models.utilisateur import Utilisateur
from app.schemas.admissions import (
    CandidatureConversionResponse,
    CandidatureCreate,
    CandidaturePage,
    CandidatureResponse,
    BulkCandidatureAction,
    BulkCandidatureActionResponse,
    CandidatureStatusUpdate,
    CandidatureUpdate,
    DecisionAdmissionCreate,
    PieceCandidatureCreate,
    PieceCandidatureResponse,
    PieceCandidatureUpdate,
    StatutCandidature,
    StatutPiece,
    TypeDecision,
)
from app.services.file_storage import (
    StorageError,
    delete_stored_file,
    media_type_for,
    resolve_stored_path,
    store_admission_upload,
)
from app.services.matricule_service import generate_matricule

router = APIRouter()

_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    StatutCandidature.NOUVELLE.value: {
        StatutCandidature.EN_VERIFICATION.value,
        StatutCandidature.ANNULEE.value,
    },
    StatutCandidature.EN_VERIFICATION.value: {
        StatutCandidature.COMPLETE.value,
        StatutCandidature.ANNULEE.value,
    },
    StatutCandidature.COMPLETE.value: {
        StatutCandidature.EN_VERIFICATION.value,
        StatutCandidature.ANNULEE.value,
    },
    StatutCandidature.LISTE_ATTENTE.value: {
        StatutCandidature.EN_VERIFICATION.value,
        StatutCandidature.ANNULEE.value,
    },
    StatutCandidature.ACCEPTEE.value: {StatutCandidature.CONVERTI.value, StatutCandidature.ANNULEE.value},
    StatutCandidature.REFUSEE.value: set(),
    StatutCandidature.CONVERTI.value: set(),
    StatutCandidature.ANNULEE.value: set(),
}


async def _load_candidature(db: AsyncSession, candidature_id: str) -> Candidature:
    stmt = (
        select(Candidature)
        .options(
            selectinload(Candidature.pieces),
            selectinload(Candidature.decisions),
            selectinload(Candidature.filiere),
            selectinload(Candidature.session).selectinload(SessionAcademique.periodes),
        )
        .where(Candidature.id == candidature_id)
    )
    result = await db.execute(stmt)
    candidature = result.scalar_one_or_none()
    if not candidature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidature introuvable.")
    return candidature


async def _validate_references(
    db: AsyncSession,
    filiere_id: str,
    session_id: str | None,
) -> tuple[Filiere, SessionAcademique | None]:
    filiere = await db.get(Filiere, filiere_id)
    if not filiere:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La filière sélectionnée n'existe pas.",
        )
    session = None
    if session_id:
        session = await db.get(SessionAcademique, session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La session académique sélectionnée n'existe pas.",
            )
    return filiere, session


def _assert_not_closed(candidature: Candidature) -> None:
    if candidature.statut in {
        StatutCandidature.CONVERTI.value,
        StatutCandidature.ANNULEE.value,
        StatutCandidature.REFUSEE.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette candidature est close et ne peut plus être modifiée.",
        )


def _apply_status_transition(
    candidature: Candidature,
    target: StatutCandidature,
    commentaire: str | None = None,
) -> None:
    """Applique une transition de workflow et centralise ses garde-fous."""
    target_value = target.value
    if target in {
        StatutCandidature.ACCEPTEE,
        StatutCandidature.REFUSEE,
        StatutCandidature.LISTE_ATTENTE,
    }:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Une décision d'admission doit être enregistrée via l'historique des décisions.",
        )
    if target == StatutCandidature.CONVERTI:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La conversion doit être effectuée via l'endpoint de conversion transactionnelle.",
        )
    if target_value not in _ALLOWED_TRANSITIONS.get(candidature.statut, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Transition non autorisée : {candidature.statut} → {target_value}.",
        )
    if target == StatutCandidature.COMPLETE and any(
        piece.statut in {StatutPiece.REQUISE.value, StatutPiece.REJETEE.value}
        for piece in candidature.pieces
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Toutes les pièces présentes doivent être reçues ou validées avant de marquer le dossier complet.",
        )
    candidature.statut = target_value
    if commentaire:
        prefix = f"[{datetime.now(timezone.utc).isoformat()}] {commentaire}"
        candidature.notes = f"{candidature.notes}\n{prefix}" if candidature.notes else prefix


@router.get(
    "/candidatures",
    response_model=CandidaturePage,
    summary="Lister les candidatures avec pagination serveur",
)
async def list_candidatures(
    search: str | None = Query(None, description="Nom, prénom, email ou référence"),
    statut: StatutCandidature | None = None,
    filiere_id: str | None = None,
    session_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _auth: Utilisateur = Depends(require_admissions),
):
    filters = []
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Candidature.nom.ilike(pattern),
                Candidature.prenom.ilike(pattern),
                Candidature.email.ilike(pattern),
                Candidature.reference.ilike(pattern),
            )
        )
    if statut:
        filters.append(Candidature.statut == statut.value)
    if filiere_id:
        filters.append(Candidature.filiere_id == filiere_id)
    if session_id:
        filters.append(Candidature.session_id == session_id)

    count_stmt = select(func.count()).select_from(Candidature)
    for condition in filters:
        count_stmt = count_stmt.where(condition)
    total = int((await db.execute(count_stmt)).scalar() or 0)
    pages = (total + page_size - 1) // page_size

    stmt = (
        select(Candidature)
        .options(
            selectinload(Candidature.pieces),
            selectinload(Candidature.decisions),
            selectinload(Candidature.filiere),
            selectinload(Candidature.session).selectinload(SessionAcademique.periodes),
        )
        .order_by(
            Candidature.date_demande.desc(),
            Candidature.created_at.desc(),
            Candidature.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    for condition in filters:
        stmt = stmt.where(condition)
    result = await db.execute(stmt)
    items = list(result.scalars().unique().all())

    counts_stmt = select(Candidature.statut, func.count()).select_from(Candidature)
    for condition in filters:
        counts_stmt = counts_stmt.where(condition)
    counts_result = await db.execute(counts_stmt.group_by(Candidature.statut))
    counts = {str(status_value): int(count) for status_value, count in counts_result.all()}

    return CandidaturePage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        counts=counts,
    )


@router.post(
    "/candidatures",
    response_model=CandidatureResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une candidature",
)
async def create_candidature(
    payload: CandidatureCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateur = Depends(require_admissions),
):
    filiere, _ = await _validate_references(db, payload.filiere_id, payload.session_id)
    candidature = Candidature(
        id=str(uuid.uuid4()),
        reference=f"CAND-{date.today().year}-{uuid.uuid4().hex[:10].upper()}",
        nom=payload.nom.strip(),
        prenom=payload.prenom.strip(),
        sexe=payload.sexe,
        date_naissance=payload.date_naissance,
        email=str(payload.email).lower().strip(),
        telephone=payload.telephone,
        adresse=payload.adresse,
        filiere_id=filiere.id,
        niveau=payload.niveau.strip(),
        session_id=payload.session_id,
        statut=StatutCandidature.NOUVELLE.value,
        date_demande=payload.date_demande or date.today(),
        notes=payload.notes,
        source=payload.source,
        created_by_id=current_user.id,
    )
    db.add(candidature)
    await db.commit()
    return await _load_candidature(db, candidature.id)


@router.get(
    "/candidatures/{candidature_id}",
    response_model=CandidatureResponse,
    summary="Consulter une candidature",
)
async def get_candidature(
    candidature_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: Utilisateur = Depends(require_admissions),
):
    return await _load_candidature(db, candidature_id)


@router.put(
    "/candidatures/{candidature_id}",
    response_model=CandidatureResponse,
    summary="Modifier les informations d'une candidature",
)
async def update_candidature(
    candidature_id: str,
    payload: CandidatureUpdate,
    db: AsyncSession = Depends(get_db),
    _auth: Utilisateur = Depends(require_admissions),
):
    candidature = await _load_candidature(db, candidature_id)
    _assert_not_closed(candidature)
    data = payload.model_dump(exclude_unset=True)
    required_fields = ("nom", "prenom", "email", "filiere_id", "niveau")
    if any(field in data and data[field] is None for field in required_fields):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Les champs nom, prénom, email, filière et niveau ne peuvent pas être vidés.",
        )
    if data.get("email"):
        data["email"] = str(data["email"]).lower().strip()
    if "filiere_id" in data:
        await _validate_references(db, data["filiere_id"], data.get("session_id", candidature.session_id))
    elif "session_id" in data and data["session_id"] is not None:
        await _validate_references(db, candidature.filiere_id, data["session_id"])
    for field, value in data.items():
        setattr(candidature, field, value)
    await db.commit()
    return await _load_candidature(db, candidature_id)


@router.patch(
    "/candidatures/{candidature_id}/statut",
    response_model=CandidatureResponse,
    summary="Faire progresser le statut d'une candidature",
)
async def update_candidature_status(
    candidature_id: str,
    payload: CandidatureStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _auth: Utilisateur = Depends(require_admissions),
):
    candidature = await _load_candidature(db, candidature_id)
    _apply_status_transition(candidature, payload.statut, payload.commentaire)
    await db.commit()
    return await _load_candidature(db, candidature_id)


@router.post(
    "/candidatures/actions",
    response_model=BulkCandidatureActionResponse,
    summary="Appliquer une action groupée à des candidatures",
)
async def bulk_update_candidatures(
    payload: BulkCandidatureAction,
    db: AsyncSession = Depends(get_db),
    _auth: Utilisateur = Depends(require_admissions),
):
    targets = {
        "mettre_en_verification": StatutCandidature.EN_VERIFICATION,
        "marquer_complete": StatutCandidature.COMPLETE,
        "annuler": StatutCandidature.ANNULEE,
    }
    target = targets[payload.action.value]
    updated_ids: list[str] = []
    errors = []

    for candidature_id in dict.fromkeys(payload.ids):
        try:
            candidature = await _load_candidature(db, candidature_id)
            _assert_not_closed(candidature)
            _apply_status_transition(candidature, target, payload.commentaire)
            updated_ids.append(candidature.id)
        except HTTPException as exc:
            errors.append({"candidature_id": candidature_id, "message": str(exc.detail)})

    await db.commit()
    return BulkCandidatureActionResponse(updated_ids=updated_ids, errors=errors)


@router.post(
    "/candidatures/{candidature_id}/pieces",
    response_model=PieceCandidatureResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter une pièce à une candidature",
)
async def add_candidature_document(
    candidature_id: str,
    payload: PieceCandidatureCreate,
    db: AsyncSession = Depends(get_db),
    _auth: Utilisateur = Depends(require_admissions),
):
    candidature = await _load_candidature(db, candidature_id)
    _assert_not_closed(candidature)
    piece = PieceCandidature(
        id=str(uuid.uuid4()),
        candidature_id=candidature.id,
        type=payload.type.strip(),
        nom_fichier=payload.nom_fichier,
        statut=StatutPiece.REQUISE.value,
        commentaire=payload.commentaire,
    )
    db.add(piece)
    await db.commit()
    await db.refresh(piece)
    return piece


@router.post(
    "/pieces/{piece_id}/fichier",
    response_model=PieceCandidatureResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Déposer le fichier d'une pièce d'admission",
)
async def upload_candidature_document(
    piece_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _auth: Utilisateur = Depends(require_admissions),
):
    """Écrit les octets dans le stockage local et ne persiste que son chemin relatif."""
    piece = await db.get(PieceCandidature, piece_id)
    if not piece:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pièce introuvable.")

    candidature = await _load_candidature(db, piece.candidature_id)
    _assert_not_closed(candidature)
    old_path = piece.chemin_stockage

    try:
        relative_path, original_name, _mime_type, _file_size = await store_admission_upload(
            file,
            candidature_id=candidature.id,
            piece_id=piece.id,
        )
    except StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    now = datetime.now(timezone.utc)
    piece.chemin_stockage = relative_path
    piece.nom_fichier = original_name
    piece.statut = StatutPiece.RECUE.value
    piece.date_depot = now
    piece.valide_par_id = None
    piece.date_validation = None
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        delete_stored_file(relative_path)
        raise

    if old_path and old_path != relative_path:
        delete_stored_file(old_path)
    await db.refresh(piece)
    return piece


@router.get(
    "/pieces/{piece_id}/fichier",
    response_class=FileResponse,
    summary="Télécharger le fichier d'une pièce d'admission",
)
async def download_candidature_document(
    piece_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: Utilisateur = Depends(require_admissions),
):
    piece = await db.get(PieceCandidature, piece_id)
    if not piece:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pièce introuvable.")
    if not piece.chemin_stockage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun fichier n'est associé à cette pièce.",
        )
    try:
        file_path = resolve_stored_path(piece.chemin_stockage)
    except StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Le chemin de stockage de cette pièce est invalide.",
        ) from exc
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Le fichier associé à cette pièce est introuvable.",
        )

    return FileResponse(
        file_path,
        media_type=media_type_for(piece.nom_fichier),
        filename=piece.nom_fichier or f"{piece.id}.bin",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.put(
    "/pieces/{piece_id}",
    response_model=PieceCandidatureResponse,
    summary="Mettre à jour le statut d'une pièce",
)
async def update_candidature_document(
    piece_id: str,
    payload: PieceCandidatureUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateur = Depends(require_admissions),
):
    piece = await db.get(PieceCandidature, piece_id)
    if not piece:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pièce introuvable.")
    candidature = await _load_candidature(db, piece.candidature_id)
    _assert_not_closed(candidature)
    data = payload.model_dump(exclude_unset=True)
    if "statut" in data and data["statut"] is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le statut d'une pièce ne peut pas être null.",
        )
    new_status = data.get("statut")
    if new_status:
        data["statut"] = new_status.value
        now = datetime.now(timezone.utc)
        if new_status in {
            StatutPiece.RECUE,
            StatutPiece.VALIDEE,
            StatutPiece.REJETEE,
        } and not piece.date_depot:
            piece.date_depot = now
        if new_status in {StatutPiece.REQUISE, StatutPiece.RECUE}:
            piece.valide_par_id = None
            piece.date_validation = None
        if new_status == StatutPiece.REQUISE:
            piece.date_depot = None
        if new_status in {StatutPiece.VALIDEE, StatutPiece.REJETEE}:
            piece.valide_par_id = current_user.id
            piece.date_validation = now
    for field, value in data.items():
        setattr(piece, field, value)
    await db.commit()
    await db.refresh(piece)
    return piece


@router.post(
    "/candidatures/{candidature_id}/decisions",
    response_model=CandidatureResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enregistrer une décision d'admission",
)
async def decide_candidature(
    candidature_id: str,
    payload: DecisionAdmissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateur = Depends(require_admissions),
):
    candidature = await _load_candidature(db, candidature_id)
    if candidature.statut in {
        StatutCandidature.CONVERTI.value,
        StatutCandidature.ANNULEE.value,
        StatutCandidature.REFUSEE.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette candidature ne peut plus recevoir de décision.",
        )
    if candidature.statut not in {
        StatutCandidature.EN_VERIFICATION.value,
        StatutCandidature.COMPLETE.value,
        StatutCandidature.LISTE_ATTENTE.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Le dossier doit d'abord passer en vérification avant une décision.",
        )
    if payload.decision == TypeDecision.ACCEPTEE:
        if any(piece.statut == StatutPiece.REJETEE.value for piece in candidature.pieces):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Une pièce rejetée doit être corrigée avant l'acceptation.",
            )
        if any(piece.statut == StatutPiece.REQUISE.value for piece in candidature.pieces):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Toutes les pièces requises doivent être reçues avant l'acceptation.",
            )
    decision = DecisionAdmission(
        id=str(uuid.uuid4()),
        candidature_id=candidature.id,
        decision=payload.decision.value,
        motif=payload.motif,
        decisionnaire_id=current_user.id,
        date_decision=datetime.now(timezone.utc),
    )
    db.add(decision)
    candidature.statut = payload.decision.value
    await db.commit()
    return await _load_candidature(db, candidature_id)


@router.post(
    "/candidatures/{candidature_id}/convertir",
    response_model=CandidatureConversionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Convertir une candidature acceptée en dossier étudiant",
)
async def convert_candidature(
    candidature_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: Utilisateur = Depends(require_admissions),
):
    candidature = await _load_candidature(db, candidature_id)
    if candidature.statut != StatutCandidature.ACCEPTEE.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Seule une candidature acceptée peut être convertie en dossier étudiant.",
        )
    if candidature.etudiant_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette candidature est déjà liée à un dossier étudiant.",
        )
    existing = await db.execute(
        select(Etudiant).where(func.lower(Etudiant.email) == candidature.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un dossier étudiant utilise déjà cet email ; associez-le manuellement.",
        )
    if candidature.adresse and len(candidature.adresse) > 255:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="L'adresse ne peut pas dépasser 255 caractères pour le dossier étudiant.",
        )
    filiere = await db.get(Filiere, candidature.filiere_id)
    if not filiere:
        raise HTTPException(status_code=422, detail="La filière de la candidature est introuvable.")
    if len(filiere.nom) > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le nom de la filière dépasse la taille supported par le dossier étudiant.",
        )
    matricule = await generate_matricule(db, filiere_code=filiere.code)
    etudiant = Etudiant(
        id=str(uuid.uuid4()),
        matricule=matricule,
        nom=candidature.nom,
        prenom=candidature.prenom,
        sexe=candidature.sexe,
        email=candidature.email,
        telephone=candidature.telephone,
        date_naissance=candidature.date_naissance,
        adresse=candidature.adresse,
        filiere=filiere.nom,
        filiere_id=filiere.id,
        niveau=candidature.niveau,
        statut="Inscrit",
        date_inscription=date.today(),
        session_id=candidature.session_id,
    )
    db.add(etudiant)
    try:
        await db.flush()
        candidature.etudiant_id = etudiant.id
        candidature.statut = StatutCandidature.CONVERTI.value
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Impossible de créer le dossier étudiant : email ou matricule déjà utilisé.",
        ) from exc
    return CandidatureConversionResponse(
        candidature=await _load_candidature(db, candidature.id),
        etudiant=etudiant,
    )
