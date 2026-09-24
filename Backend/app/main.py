"""
EduManagePro (EMP) — Backend API Application
FastAPI + SQLAlchemy 2.0 Async + PostgreSQL / Standalone Ready
"""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.database import async_session_factory
from app.api.v1.api import api_router


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestionnaire de cycle de vie de l'application :
    Exécuté au démarrage et à l'arrêt du serveur.
    """
    logger.info("Demarrage de %s v%s [%s]", settings.PROJECT_NAME, settings.VERSION, settings.ENVIRONMENT)
    logger.info("Mode tenant : %s", settings.TENANT_MODE)
    logger.info("Base de donnees cible : %s:%s", settings.DB_HOST, settings.DB_PORT)
    
    # Test préliminaire de connectivité DB (non bloquant au boot pour laisser le wizard accessible)
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        logger.info("Connexion a la base de donnees etablie avec succes.")
    except Exception as e:
        logger.warning("Base de donnees non connectee ou en attente d'initialisation : %s", e)
        logger.info("Le Setup Wizard (/setup) reste accessible pour la configuration initiale.")

    yield

    logger.info("Arret du serveur EduManagePro.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "API Backend d'EduManagePro (EMP) — Système de gestion scolaire et universitaire.\n\n"
        "Fonctionnalités clés :\n"
        "- Architecture Standalone prête pour une évolution multi-tenant\n"
        "- Assistant de configuration initiale Web (/api/v1/setup)\n"
        "- Gestion des sessions académiques et tranches d'échéances\n"
        "- Sécurité JWT avec contrôle d'accès basé sur les rôles (RBAC)"
    ),
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=None if settings.ENVIRONMENT.lower() == "production" else "/docs",
    redoc_url=None if settings.ENVIRONMENT.lower() == "production" else "/redoc",
    lifespan=lifespan,
)

from fastapi import Request
from fastapi.responses import JSONResponse
# Configuration CORS pour le frontend (React / Vite)
origins = [str(o).strip() for o in settings.BACKEND_CORS_ORIGINS if o]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=(
        r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
        if settings.ENVIRONMENT.lower() == "development"
        else None
    ),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Journalise l'erreur sans exposer de détails internes au client."""
    logger.exception("Erreur non gérée sur %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Une erreur interne est survenue."},
    )



@app.get("/", tags=["Système"], summary="Accueil API")
async def root():
    return {
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "docs": "/docs" if settings.ENVIRONMENT.lower() != "production" else None,
        "mode": settings.TENANT_MODE,
        "api_v1": settings.API_V1_STR,
    }


@app.get("/health", tags=["Système"], summary="Health Check")
async def health_check():
    """Vérification de la santé applicative et de la connexion SGBD."""
    db_ok = False
    details = "Opérationnel"
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        details = "Base de données inaccessible."

    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "details": details,
        "version": settings.VERSION,
    }


# Inclusion des routes API V1
app.include_router(api_router, prefix=settings.API_V1_STR)
