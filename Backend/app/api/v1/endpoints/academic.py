"""Endpoints du socle académique.

Les écritures sont reservees a l'administration/direction pedagogique.  Le
chargement LMD est une action explicite et idempotente : il n'est appele par
aucun startup, setup wizard ou autre endpoint.
"""

from datetime import date
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, require_academic_registry_read, require_academic_write
from app.models.academic import Classe, Cycle, Inscription, Niveau
from app.models.admissions import Candidature
from app.models.etudiant import Etudiant
from app.models.session_academique import SessionAcademique
from app.models.structure import Filiere
from app.schemas.academic import (
    ClasseCreate,
    ClasseResponse,
    ClasseUpdate,
    CycleCreate,
    CycleResponse,
    CycleUpdate,
    InscriptionCreate,
    InscriptionResponse,
    ModeleLMDChargeRequest,
    ModeleLMDChargeResponse,
    NiveauCreate,
    NiveauResponse,
    NiveauUpdate,
)
from app.services.academic_service import (
    class_projections,
    get_classe,
    get_filiere,
    get_niveau as get_niveau_record,
    get_session,
    load_inscription,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers de chargement et de gestion des conflits
# ---------------------------------------------------------------------------
def _classe_options():
    return (
        selectinload(Classe.filiere),
        selectinload(Classe.niveau).selectinload(Niveau.cycle),
    )


def _niveau_options():
    return (selectinload(Niveau.cycle),)


async def _get_cycle(db: AsyncSession, cycle_id: str) -> Cycle:
    cycle = await db.get(Cycle, cycle_id)
    if cycle is None:
        raise HTTPException(status_code=404, detail="Cycle introuvable.")
    return cycle


async def _get_niveau(db: AsyncSession, niveau_id: str) -> Niveau:
    result = await db.execute(
        select(Niveau).options(*_niveau_options()).where(Niveau.id == niveau_id)
    )
    niveau = result.scalar_one_or_none()
    if niveau is None:
        raise HTTPException(status_code=404, detail="Niveau introuvable.")
    return niveau


async def _get_classe(db: AsyncSession, classe_id: str) -> Classe:
    classe = await get_classe(db, classe_id)
    if classe is None:
        raise HTTPException(status_code=404, detail="Classe introuvable.")
    return classe


async def _reload_cycle(db: AsyncSession, cycle_id: str) -> Cycle:
    return await _get_cycle(db, cycle_id)


async def _reload_niveau(db: AsyncSession, niveau_id: str) -> Niveau:
    return await _get_niveau(db, niveau_id)


async def _reload_classe(db: AsyncSession, classe_id: str) -> Classe:
    return await _get_classe(db, classe_id)


def _not_found_dependency(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _payload_without_alias(payload) -> dict:
    data = payload.model_dump(exclude_unset=True)
    data.pop("libelle", None)
    return data


# ---------------------------------------------------------------------------
# Charges/actions/templates
# ---------------------------------------------------------------------------
# Ces routes sont declarees avant les routes dynamiques pour ne jamais etre
# interpretees comme un identifiant.
_LMD_CYCLES = (
    ("LICENCE", "Licence", 1),
    ("MASTER", "Master", 2),
)
_LMD_NIVEAUX = {
    "LICENCE": (("L1", "Licence 1", 1), ("L2", "Licence 2", 2), ("L3", "Licence 3", 3)),
    "MASTER": (("M1", "Master 1", 1), ("M2", "Master 2", 2)),
}
_LMD_CYCLE_CODES = {
    "LICENCE": ("LICENCE", "LIC", "LIC-1", "L1C"),
    "MASTER": ("MASTER", "MAS", "MST", "M"),
}


@router.post(
    "/modele-lmd/charger",
    response_model=ModeleLMDChargeResponse,
    summary="Charger explicitement le modèle LMD (idempotent)",
)
@router.post(
    "/modele-lmd/load",
    response_model=ModeleLMDChargeResponse,
    include_in_schema=False,
)
@router.post(
    "/modele-lmd",
    response_model=ModeleLMDChargeResponse,
    include_in_schema=False,
)
@router.post(
    "/actions/modele-lmd",
    response_model=ModeleLMDChargeResponse,
    include_in_schema=False,
)
@router.post(
    "/lmd/charger",
    response_model=ModeleLMDChargeResponse,
    include_in_schema=False,
)
@router.post(
    "/lmd/load",
    response_model=ModeleLMDChargeResponse,
    include_in_schema=False,
)
async def charger_modele_lmd(
    payload: Optional[ModeleLMDChargeRequest] = None,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_write),
):
    """Charge les cycles et niveaux LMD sans toucher aux classes/etudiants.

    L'action est volontairement absente de tout callback automatique.  Une
    deuxieme invocation retrouve les lignes existantes par code et ne cree
    aucun doublon.
    """
    # Le corps est optionnel afin de rester appelable avec POST sans payload.
    # ``confirmer`` est documenté pour le contrat, mais l'action HTTP est
    # elle-même l confirmation explicite.
    del payload

    cycles_crees = 0
    niveaux_crees = 0
    cycles: list[Cycle] = []

    for code, nom, ordre in _LMD_CYCLES:
        candidates = _LMD_CYCLE_CODES[code]
        result = await db.execute(
            select(Cycle).where(
                or_(
                    Cycle.code.in_(candidates),
                    func.lower(Cycle.nom) == nom.lower(),
                )
            )
        )
        cycle = result.scalars().first()
        if cycle is None:
            cycle = Cycle(
                id=f"cycle-{code.lower()}",
                code=code,
                nom=nom,
                ordre=ordre,
                actif=True,
            )
            db.add(cycle)
            cycles_crees += 1
        cycles.append(cycle)

    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Le modèle LMD entre en conflit avec des référentiels existants.",
        ) from exc

    niveaux: list[Niveau] = []
    for cycle, (code, _nom_cycle, _ordre_cycle) in zip(cycles, _LMD_CYCLES):
        for niveau_code, niveau_nom, ordre in _LMD_NIVEAUX[code]:
            result = await db.execute(
                select(Niveau).where(
                    Niveau.cycle_id == cycle.id,
                    Niveau.code == niveau_code,
                )
            )
            niveau = result.scalars().first()
            if niveau is None:
                niveau = Niveau(
                    id=f"niveau-{niveau_code.lower()}-{code.lower()}",
                    cycle_id=cycle.id,
                    code=niveau_code,
                    nom=niveau_nom,
                    ordre=ordre,
                    actif=True,
                )
                db.add(niveau)
                niveaux_crees += 1
            niveaux.append(niveau)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Le modèle LMD entre en conflit avec des référentiels existants.",
        ) from exc

    # Recharge les relations apres commit pour une réponse complète.
    loaded_cycles: list[Cycle] = []
    for cycle in cycles:
        loaded_cycles.append(await _reload_cycle(db, cycle.id))
    loaded_niveaux: list[Niveau] = []
    for niveau in niveaux:
        loaded_niveaux.append(await _reload_niveau(db, niveau.id))

    return ModeleLMDChargeResponse(
        cycles=loaded_cycles,
        niveaux=loaded_niveaux,
        cycles_crees=cycles_crees,
        niveaux_crees=niveaux_crees,
        total_cycles=len(loaded_cycles),
        total_niveaux=len(loaded_niveaux),
        created=bool(cycles_crees or niveaux_crees),
        idempotent=not bool(cycles_crees or niveaux_crees),
    )


# ---------------------------------------------------------------------------
# Cycles
# ---------------------------------------------------------------------------
@router.get("/cycles", response_model=List[CycleResponse], summary="Lister les cycles")
async def list_cycles(
    actif: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_registry_read),
):
    stmt = select(Cycle)
    if actif is not None:
        stmt = stmt.where(Cycle.actif == actif)
    result = await db.execute(stmt.order_by(Cycle.ordre, Cycle.nom))
    return result.scalars().all()


@router.post(
    "/cycles",
    response_model=CycleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un cycle",
)
async def create_cycle(
    payload: CycleCreate,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_write),
):
    duplicate = await db.execute(select(Cycle).where(Cycle.code == payload.code))
    if duplicate.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ce code de cycle est déjà utilisé.")
    cycle = Cycle(
        id=payload.id or str(uuid.uuid4()),
        code=payload.code,
        nom=payload.nom or payload.libelle or "",
        description=payload.description,
        ordre=payload.ordre,
        actif=payload.actif,
    )
    db.add(cycle)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Ce cycle existe déjà.") from exc
    return await _reload_cycle(db, cycle.id)


@router.get("/cycles/{cycle_id}", response_model=CycleResponse, summary="Détail d'un cycle")
async def get_cycle(
    cycle_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_registry_read),
):
    return await _get_cycle(db, cycle_id)


@router.put("/cycles/{cycle_id}", response_model=CycleResponse, summary="Modifier un cycle")
async def update_cycle(
    cycle_id: str,
    payload: CycleUpdate,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_write),
):
    cycle = await _get_cycle(db, cycle_id)
    data = _payload_without_alias(payload)
    if "code" in data and data["code"] is None:
        raise HTTPException(status_code=422, detail="Le code du cycle ne peut pas être null.")
    if "nom" in data and data["nom"] is None:
        raise HTTPException(status_code=422, detail="Le nom du cycle ne peut pas être null.")
    if "libelle" in payload.model_fields_set and "nom" not in data:
        data["nom"] = payload.libelle
    if "code" in data:
        duplicate = await db.execute(
            select(Cycle).where(Cycle.code == data["code"], Cycle.id != cycle_id)
        )
        if duplicate.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Ce code de cycle est déjà utilisé.")
    for field, value in data.items():
        setattr(cycle, field, value)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Conflit lors de la modification du cycle.") from exc
    return await _reload_cycle(db, cycle_id)


@router.delete(
    "/cycles/{cycle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un cycle non référencé",
)
async def delete_cycle(
    cycle_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_write),
):
    cycle = await _get_cycle(db, cycle_id)
    used = await db.execute(
        select(Niveau.id).where(Niveau.cycle_id == cycle_id).limit(1)
    )
    if used.scalar_one_or_none():
        raise _not_found_dependency("Le cycle est référencé par un niveau.")
    await db.delete(cycle)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _not_found_dependency("Le cycle est référencé par une donnée historique.") from exc


# ---------------------------------------------------------------------------
# Niveaux
# ---------------------------------------------------------------------------
@router.get("/niveaux", response_model=List[NiveauResponse], summary="Lister les niveaux")
async def list_niveaux(
    cycle_id: Optional[str] = None,
    actif: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_registry_read),
):
    stmt = select(Niveau).options(*_niveau_options())
    if cycle_id:
        stmt = stmt.where(Niveau.cycle_id == cycle_id)
    if actif is not None:
        stmt = stmt.where(Niveau.actif == actif)
    result = await db.execute(stmt.order_by(Niveau.cycle_id, Niveau.ordre, Niveau.code))
    return result.scalars().all()


@router.post(
    "/niveaux",
    response_model=NiveauResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un niveau",
)
async def create_niveau(
    payload: NiveauCreate,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_write),
):
    await _get_cycle(db, payload.cycle_id)
    duplicate = await db.execute(
        select(Niveau).where(
            Niveau.cycle_id == payload.cycle_id,
            Niveau.code == payload.code,
        )
    )
    if duplicate.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Ce code de niveau existe déjà pour ce cycle.",
        )
    niveau = Niveau(
        id=payload.id or str(uuid.uuid4()),
        cycle_id=payload.cycle_id,
        code=payload.code,
        nom=payload.nom or payload.libelle or payload.code,
        description=payload.description,
        ordre=payload.ordre,
        actif=payload.actif,
    )
    db.add(niveau)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Ce niveau existe déjà.") from exc
    return await _reload_niveau(db, niveau.id)


@router.get("/niveaux/{niveau_id}", response_model=NiveauResponse, summary="Détail d'un niveau")
async def get_niveau(
    niveau_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_registry_read),
):
    return await _get_niveau(db, niveau_id)


@router.put("/niveaux/{niveau_id}", response_model=NiveauResponse, summary="Modifier un niveau")
async def update_niveau(
    niveau_id: str,
    payload: NiveauUpdate,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_write),
):
    niveau = await _get_niveau(db, niveau_id)
    data = _payload_without_alias(payload)
    if "code" in data and data["code"] is None:
        raise HTTPException(status_code=422, detail="Le code du niveau ne peut pas être null.")
    if "cycle_id" in data and data["cycle_id"] is None:
        raise HTTPException(status_code=422, detail="Le cycle du niveau ne peut pas être null.")
    if "nom" in data and data["nom"] is None:
        raise HTTPException(status_code=422, detail="Le nom du niveau ne peut pas être null.")
    if "libelle" in payload.model_fields_set and "nom" not in data:
        data["nom"] = payload.libelle
    target_cycle_id = data.get("cycle_id", niveau.cycle_id)
    target_code = data.get("code", niveau.code)
    if target_cycle_id != niveau.cycle_id or target_code != niveau.code:
        used_class = await db.execute(
            select(Classe.id).where(Classe.niveau_id == niveau_id).limit(1)
        )
        if used_class.scalar_one_or_none():
            raise _not_found_dependency(
                "L'identité d'un niveau référencé par une classe ne peut pas être modifiée."
            )
        used_candidature = await db.execute(
            select(Candidature.id).where(Candidature.niveau_id == niveau_id).limit(1)
        )
        if used_candidature.scalar_one_or_none():
            raise _not_found_dependency(
                "L'identité d'un niveau référencé par une candidature ne peut pas être modifiée."
            )
    if target_cycle_id != niveau.cycle_id:
        await _get_cycle(db, target_cycle_id)
    duplicate = await db.execute(
        select(Niveau).where(
            Niveau.cycle_id == target_cycle_id,
            Niveau.code == target_code,
            Niveau.id != niveau_id,
        )
    )
    if duplicate.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ce code de niveau existe déjà pour ce cycle.")
    for field, value in data.items():
        setattr(niveau, field, value)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Conflit lors de la modification du niveau.") from exc
    return await _reload_niveau(db, niveau_id)


@router.delete(
    "/niveaux/{niveau_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un niveau non référencé",
)
async def delete_niveau(
    niveau_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_write),
):
    niveau = await _get_niveau(db, niveau_id)
    used = await db.execute(select(Classe.id).where(Classe.niveau_id == niveau_id).limit(1))
    if used.scalar_one_or_none():
        raise _not_found_dependency("Le niveau est référencé par une classe.")
    used_candidature = await db.execute(
        select(Candidature.id).where(Candidature.niveau_id == niveau_id).limit(1)
    )
    if used_candidature.scalar_one_or_none():
        raise _not_found_dependency("Le niveau est référencé par une candidature.")
    await db.delete(niveau)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _not_found_dependency("Le niveau est référencé par une donnée historique.") from exc


# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------
@router.get("/classes", response_model=List[ClasseResponse], summary="Lister les classes")
async def list_classes(
    filiere_id: Optional[str] = None,
    niveau_id: Optional[str] = None,
    cycle_id: Optional[str] = None,
    actif: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_registry_read),
):
    stmt = select(Classe).options(*_classe_options())
    if filiere_id:
        stmt = stmt.where(Classe.filiere_id == filiere_id)
    if niveau_id:
        stmt = stmt.where(Classe.niveau_id == niveau_id)
    if cycle_id:
        stmt = stmt.join(Niveau, Classe.niveau_id == Niveau.id).where(Niveau.cycle_id == cycle_id)
    if actif is not None:
        stmt = stmt.where(Classe.actif == actif)
    result = await db.execute(stmt.order_by(Classe.nom, Classe.id))
    return result.scalars().unique().all()


@router.post(
    "/classes",
    response_model=ClasseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une classe",
)
async def create_classe(
    payload: ClasseCreate,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_write),
):
    if await get_filiere(db, payload.filiere_id) is None:
        raise HTTPException(status_code=422, detail="La filière sélectionnée n'existe pas.")
    if await get_niveau_record(db, payload.niveau_id) is None:
        raise HTTPException(status_code=422, detail="Le niveau sélectionné n'existe pas.")
    duplicate = await db.execute(
        select(Classe).where(
            Classe.filiere_id == payload.filiere_id,
            Classe.niveau_id == payload.niveau_id,
        )
    )
    if duplicate.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Une classe existe déjà pour cette filière et ce niveau.",
        )
    classe = Classe(
        id=payload.id or str(uuid.uuid4()),
        filiere_id=payload.filiere_id,
        niveau_id=payload.niveau_id,
        nom=payload.nom,
        actif=payload.actif,
    )
    db.add(classe)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Une classe existe déjà pour cette filière et ce niveau.",
        ) from exc
    return await _reload_classe(db, classe.id)


@router.get("/classes/{classe_id}", response_model=ClasseResponse, summary="Détail d'une classe")
async def get_classe_endpoint(
    classe_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_registry_read),
):
    return await _get_classe(db, classe_id)


@router.put("/classes/{classe_id}", response_model=ClasseResponse, summary="Modifier une classe")
async def update_classe(
    classe_id: str,
    payload: ClasseUpdate,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_write),
):
    classe = await _get_classe(db, classe_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("filiere_id", classe.filiere_id) is None:
        raise HTTPException(status_code=422, detail="La filière d'une classe ne peut pas être null.")
    if data.get("niveau_id", classe.niveau_id) is None:
        raise HTTPException(status_code=422, detail="Le niveau d'une classe ne peut pas être null.")
    target_filiere_id = data.get("filiere_id", classe.filiere_id)
    target_niveau_id = data.get("niveau_id", classe.niveau_id)
    if target_filiere_id != classe.filiere_id or target_niveau_id != classe.niveau_id:
        used = await db.execute(
            select(Inscription.id)
            .where(Inscription.classe_id == classe_id)
            .limit(1)
        )
        if used.scalar_one_or_none():
            raise _not_found_dependency(
                "L'identité d'une classe référencée par une inscription ne peut pas être modifiée."
            )
        used_student = await db.execute(
            select(Etudiant.id).where(Etudiant.classe_id == classe_id).limit(1)
        )
        if used_student.scalar_one_or_none():
            raise _not_found_dependency(
                "L'identité d'une classe rattachée à un étudiant ne peut pas être modifiée."
            )
        used_candidature = await db.execute(
            select(Candidature.id).where(Candidature.classe_id == classe_id).limit(1)
        )
        if used_candidature.scalar_one_or_none():
            raise _not_found_dependency(
                "L'identité d'une classe référencée par une candidature ne peut pas être modifiée."
            )
    if target_filiere_id != classe.filiere_id and await get_filiere(db, target_filiere_id) is None:
        raise HTTPException(status_code=422, detail="La filière sélectionnée n'existe pas.")
    if target_niveau_id != classe.niveau_id and await get_niveau_record(db, target_niveau_id) is None:
        raise HTTPException(status_code=422, detail="Le niveau sélectionné n'existe pas.")
    duplicate = await db.execute(
        select(Classe).where(
            Classe.filiere_id == target_filiere_id,
            Classe.niveau_id == target_niveau_id,
            Classe.id != classe_id,
        )
    )
    if duplicate.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Une classe existe déjà pour cette filière et ce niveau.",
        )
    for field, value in data.items():
        setattr(classe, field, value)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Conflit lors de la modification de la classe.") from exc
    return await _reload_classe(db, classe_id)


@router.delete(
    "/classes/{classe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une classe non référencée",
)
async def delete_classe(
    classe_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_write),
):
    classe = await _get_classe(db, classe_id)
    for model, column, message in (
        (Etudiant, Etudiant.classe_id, "des étudiants"),
        (Candidature, Candidature.classe_id, "des candidatures"),
        (Inscription, Inscription.classe_id, "des inscriptions"),
    ):
        result = await db.execute(select(model.id).where(column == classe_id).limit(1))
        if result.scalar_one_or_none():
            raise _not_found_dependency(f"La classe est référencée par {message}.")
    await db.delete(classe)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _not_found_dependency("La classe est référencée par une donnée historique.") from exc


# ---------------------------------------------------------------------------
# Inscriptions
# ---------------------------------------------------------------------------
@router.get(
    "/inscriptions",
    response_model=List[InscriptionResponse],
    summary="Lister les inscriptions",
)
async def list_inscriptions(
    etudiant_id: Optional[str] = None,
    classe_id: Optional[str] = None,
    session_id: Optional[str] = None,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_registry_read),
):
    stmt = select(Inscription).options(
        selectinload(Inscription.etudiant),
        selectinload(Inscription.classe).selectinload(Classe.filiere),
        selectinload(Inscription.classe).selectinload(Classe.niveau).selectinload(Niveau.cycle),
        selectinload(Inscription.session).selectinload(SessionAcademique.periodes),
    )
    if etudiant_id:
        stmt = stmt.where(Inscription.etudiant_id == etudiant_id)
    if classe_id:
        stmt = stmt.where(Inscription.classe_id == classe_id)
    if session_id:
        stmt = stmt.where(Inscription.session_id == session_id)
    if active_only:
        stmt = stmt.where(Inscription.actif.is_(True))
    result = await db.execute(stmt.order_by(Inscription.date_inscription.desc(), Inscription.id))
    return result.scalars().unique().all()


@router.post(
    "/inscriptions",
    response_model=InscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une inscription",
)
async def create_inscription(
    payload: InscriptionCreate,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_write),
):
    etudiant = await db.get(Etudiant, payload.etudiant_id)
    if etudiant is None:
        raise HTTPException(status_code=422, detail="L'étudiant sélectionné n'existe pas.")
    classe = await get_classe(db, payload.classe_id)
    if classe is None:
        raise HTTPException(status_code=422, detail="La classe sélectionnée n'existe pas.")
    if await get_session(db, payload.session_id) is None:
        raise HTTPException(status_code=422, detail="La session sélectionnée n'existe pas.")
    statut = (payload.statut or "active").strip().lower()
    actif = payload.actif if payload.actif is not None else statut == "active"
    if not actif:
        statut = statut if statut != "active" else "inactive"
    if actif:
        existing = await db.execute(
            select(Inscription).where(
                Inscription.etudiant_id == payload.etudiant_id,
                Inscription.session_id == payload.session_id,
                Inscription.actif.is_(True),
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail="Une inscription active existe déjà pour cet étudiant et cette session.",
            )
        projections = class_projections(classe)
        etudiant.classe_id = classe.id
        etudiant.filiere_id = projections["filiere_id"]
        etudiant.filiere = projections["filiere"]
        etudiant.niveau = projections["niveau"]
        etudiant.session_id = payload.session_id
    inscription = Inscription(
        id=payload.id or str(uuid.uuid4()),
        etudiant_id=payload.etudiant_id,
        classe_id=payload.classe_id,
        session_id=payload.session_id,
        actif=actif,
        statut=statut,
        date_inscription=payload.date_inscription or date.today(),
    )
    db.add(inscription)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Une inscription active existe déjà pour cet étudiant et cette session.",
        ) from exc
    loaded = await load_inscription(db, inscription.id)
    return loaded


@router.get(
    "/inscriptions/{inscription_id}",
    response_model=InscriptionResponse,
    summary="Détail d'une inscription",
)
async def get_inscription(
    inscription_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_registry_read),
):
    inscription = await load_inscription(db, inscription_id)
    if inscription is None:
        raise HTTPException(status_code=404, detail="Inscription introuvable.")
    return inscription


__all__ = ["router"]
