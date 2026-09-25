"""
Setup Wizard Endpoints :
- GET /status : Vérifie si le système est déjà initialisé
- POST /initialize : Initialise l'établissement, l'administrateur et les paramètres initiaux
"""

from datetime import datetime, timezone
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.api.deps import get_db
from app.core.config import settings
from app.core.security import get_password_hash, create_access_token
from app.models.etablissement import Etablissement
from app.models.utilisateur import Utilisateur, UserRole
import app.models.structure
import app.models.pedagogie
import app.models.etudiant
import app.models.finance
from app.schemas.setup import SetupStatusResponse, SetupInitRequest, SetupInitResponse
from app.schemas.user import UserResponse
from app.services.audit_service import record_audit_event

router = APIRouter()

_SETUP_ADVISORY_LOCK_ID = 7_310_024_001


async def _lock_setup_initialization(db: AsyncSession) -> None:
    """Sérialise le premier setup dans PostgreSQL jusqu'au commit."""

    if db.get_bind().dialect.name == "postgresql":
        await db.execute(
            text("SELECT pg_advisory_xact_lock(:lock_id)"),
            {"lock_id": _SETUP_ADVISORY_LOCK_ID},
        )


@router.get("/status", response_model=SetupStatusResponse, summary="État d'initialisation du système")
async def get_setup_status(db: AsyncSession = Depends(get_db)):
    """
    Retourne le statut d'initialisation du système.
    Permet au frontend de savoir s'il faut rediriger l'utilisateur vers /setup ou vers /login.
    """
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        return SetupStatusResponse(
            is_configured=False,
            version=settings.VERSION,
            tenant_mode=settings.TENANT_MODE,
            database_connected=False,
            details="Impossible de se connecter à la base de données."
        )

    # Vérification de l'existence d'un établissement configuré
    try:
        stmt = select(Etablissement).limit(1)
        result = await db.execute(stmt)
        etablissement = result.scalar_one_or_none()

        if etablissement and etablissement.is_configured:
            return SetupStatusResponse(
                is_configured=True,
                etablissement_nom=etablissement.nom,
                etablissement_code=etablissement.code,
                devise=etablissement.devise,
                version=settings.VERSION,
                tenant_mode=settings.TENANT_MODE,
                database_connected=True,
            )
    except Exception:
        return SetupStatusResponse(
            is_configured=False,
            version=settings.VERSION,
            tenant_mode=settings.TENANT_MODE,
            database_connected=True,
            details="Le schéma de la base de données n'est pas initialisé."
        )

    return SetupStatusResponse(
        is_configured=False,
        version=settings.VERSION,
        tenant_mode=settings.TENANT_MODE,
        database_connected=True,
        details="Système prêt pour le premier paramétrage."
    )


@router.post("/initialize", response_model=SetupInitResponse, status_code=status.HTTP_201_CREATED, summary="Initialisation de l'instance")
async def initialize_system(
    payload: SetupInitRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Exécute le premier paramétrage de l'établissement :
    1. Création ou mise à jour de l'Etablissement (nom, code, devise, licence)
    2. Création du compte Administrateur initial (SuperUser)
    3. Génération d'un JWT d'accès à titre de confirmation technique.
    Les données métier sont ensuite saisies progressivement via les modules API.
    """
    # 1. Sérialiser puis vérifier si l'instance est déjà configurée.
    try:
        await _lock_setup_initialization(db)
        stmt = select(Etablissement).where(Etablissement.is_configured == True)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Le système a déjà été configuré. Veuillez vous connecter."
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Le schéma de la base de données n'est pas initialisé. Exécutez les migrations Alembic.",
        ) from exc

    # 2. Créer l'établissement
    etablissement = Etablissement(
        id=str(uuid.uuid4()),
        nom=payload.etablissement.nom,
        sigle=payload.etablissement.code,
        adresse=payload.etablissement.adresse,
        telephone=payload.etablissement.telephone or "",
        email=str(payload.etablissement.email),
        devise=payload.etablissement.devise,
        licence_cle=payload.etablissement.license_key,
        licence_statut="pending_validation" if payload.etablissement.license_key else "active",
        is_configured=True,
        date_configuration=datetime.now(timezone.utc),
    )
    db.add(etablissement)

    # 3. Créer l'administrateur
    admin_user = Utilisateur(
        email=str(payload.admin.email).lower(),
        hashed_password=get_password_hash(payload.admin.password),
        nom=payload.admin.nom,
        prenom=payload.admin.prenom,
        telephone=payload.admin.telephone,
        role=UserRole.ADMIN.value,
        is_active=True,
        is_superuser=True,
        last_login=datetime.now(timezone.utc)
    )
    db.add(admin_user)
    await db.flush()  # Pour récupérer l'id autogénéré
    await record_audit_event(
        db,
        actor_id=admin_user.id,
        actor_email=admin_user.email,
        action="security.setup.initialized",
        resource_type="etablissement",
        resource_id=etablissement.id,
        details={
            "admin_user_id": admin_user.id,
            "admin_role": admin_user.role,
        },
    )

    await db.commit()
    await db.refresh(admin_user)

    # 5. Générer le jeton JWT
    token = create_access_token(
        subject=admin_user.id,
        claims={"email": admin_user.email, "role": admin_user.role}
    )

    return SetupInitResponse(
        success=True,
        message="Établissement et compte administrateur configurés avec succès.",
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(admin_user)
    )
