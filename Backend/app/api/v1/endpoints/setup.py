"""
Setup Wizard Endpoints :
- GET /status : Vérifie si le système est déjà initialisé
- POST /initialize : Initialise l'établissement, l'administrateur et les paramètres initiaux
"""

from datetime import datetime, timezone, date
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.api.deps import get_db
from app.core.config import settings
from app.core.database import get_engine_for_tenant
from app.core.security import get_password_hash, create_access_token
from app.models.base import Base
from app.models.etablissement import Etablissement
from app.models.utilisateur import Utilisateur, UserRole
from app.models.session_academique import SessionAcademique, PeriodePaiement
import app.models.structure
import app.models.pedagogie
import app.models.etudiant
import app.models.finance
from app.schemas.setup import SetupStatusResponse, SetupInitRequest, SetupInitResponse
from app.schemas.user import UserResponse

router = APIRouter()


@router.get("/status", response_model=SetupStatusResponse, summary="État d'initialisation du système")
async def get_setup_status(db: AsyncSession = Depends(get_db)):
    """
    Retourne le statut d'initialisation du système.
    Permet au frontend de savoir s'il faut rediriger l'utilisateur vers /setup ou vers /login.
    """
    db_connected = False
    try:
        await db.execute(text("SELECT 1"))
        db_connected = True
    except Exception as e:
        return SetupStatusResponse(
            is_configured=False,
            version=settings.VERSION,
            tenant_mode=settings.TENANT_MODE,
            database_connected=False,
            details=f"Impossible de se connecter à la base de données: {str(e)}"
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
                version=settings.VERSION,
                tenant_mode=settings.TENANT_MODE,
                database_connected=True,
            )
    except Exception as e:
        return SetupStatusResponse(
            is_configured=False,
            version=settings.VERSION,
            tenant_mode=settings.TENANT_MODE,
            database_connected=True,
            details=f"Tables non initialisées: {str(e)}"
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
    3. Optionnel : Création d'une session académique par défaut avec périodes de paiement
    4. Génération immédiate d'un JWT d'accès pour connexion automatique.
    """
    # 1. Vérifier si déjà configuré
    try:
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
    except Exception:
        pass

    # S'assurer que les tables sont créées dans la base cible
    try:
        engine = get_engine_for_tenant("default")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        print(f"Notice: Table initialization sync: {e}")

    # 2. Créer l'établissement
    etablissement = Etablissement(
        nom=payload.etablissement.nom,
        sigle=payload.etablissement.code or "EMP",
        adresse=payload.etablissement.adresse,
        telephone=payload.etablissement.telephone or "",
        email=str(payload.etablissement.email) if payload.etablissement.email else "contact@emp.com",
        devise=payload.etablissement.devise or "FCFA",
        licence_cle=payload.etablissement.license_key,
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

    # 4. Créer la session académique par défaut si demandé
    if payload.init_default_academic_session:
        session_id = "session-2025-2026"
        session_defaut = SessionAcademique(
            id=session_id,
            nom="Année Académique 2025-2026",
            code="2025-2026",
            annee_academique="2025-2026",
            date_debut=date(2025, 10, 1),
            date_fin=date(2026, 7, 31),
            statut="active",
            description="Session académique initiale générée lors de la configuration."
        )
        db.add(session_defaut)

        # 10 périodes mensuelles d'octobre à juillet
        mois_periodes = [
            ("Tranche 1 - Octobre", "Octobre", date(2025, 10, 15), 1),
            ("Tranche 2 - Novembre", "Novembre", date(2025, 11, 15), 2),
            ("Tranche 3 - Décembre", "Décembre", date(2025, 12, 15), 3),
            ("Tranche 4 - Janvier", "Janvier", date(2026, 1, 15), 4),
            ("Tranche 5 - Février", "Février", date(2026, 2, 15), 5),
            ("Tranche 6 - Mars", "Mars", date(2026, 3, 15), 6),
            ("Tranche 7 - Avril", "Avril", date(2026, 4, 15), 7),
            ("Tranche 8 - Mai", "Mai", date(2026, 5, 15), 8),
            ("Tranche 9 - Juin", "Juin", date(2026, 6, 15), 9),
            ("Tranche 10 - Juillet", "Juillet", date(2026, 7, 15), 10),
        ]

        for nom_p, mois_p, echeance, ordre in mois_periodes:
            p = PeriodePaiement(
                id=str(uuid.uuid4()),
                session_id=session_id,
                nom=nom_p,
                mois=mois_p,
                date_echeance=echeance,
                montant_estime=60000.0,
                ordre=ordre
            )
            db.add(p)

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
