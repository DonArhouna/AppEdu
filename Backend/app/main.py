"""
EduManagePro (EMP) — Backend API Application
FastAPI + SQLAlchemy 2.0 Async + PostgreSQL / Multi-Tenant Ready
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.database import async_session_factory
from app.api.v1.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestionnaire de cycle de vie de l'application :
    Exécuté au démarrage et à l'arrêt du serveur.
    """
    print(f"🚀 Démarrage de {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")
    print(f"⚙️  Mode Tenant : {settings.TENANT_MODE}")
    print(f"🔗 Base de données cible : {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME if hasattr(settings, 'DB_NAME') else 'edumanagepro'}")
    
    # Test préliminaire de connectivité DB (non bloquant au boot pour laisser le wizard accessible)
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        print("✅ Connexion à la base de données établie avec succès.")
    except Exception as e:
        print(f"⚠️  Attention : Base de données non connectée ou en attente d'initialisation : {e}")
        print("👉 Le Setup Wizard (/setup) reste accessible pour la configuration initiale.")

    yield

    print("🛑 Arrêt du serveur EduManagePro.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "API Backend d'EduManagePro (EMP) — Système de gestion scolaire et universitaire.\n\n"
        "Fonctionnalités clés :\n"
        "- Architecture Hybride Standalone / Multi-Tenant\n"
        "- Assistant de configuration initiale Web (/api/v1/setup)\n"
        "- Gestion des sessions académiques et tranches d'échéances\n"
        "- Sécurité JWT avec contrôle d'accès basé sur les rôles (RBAC)"
    ),
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

from fastapi import Request
from fastapi.responses import JSONResponse
import traceback

# Configuration CORS pour le frontend (React / Vite)
origins = [str(o).strip() for o in settings.BACKEND_CORS_ORIGINS if o]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Garantit que même en cas d'erreur interne 500, les en-têtes CORS sont préservés."""
    traceback.print_exc()
    origin = request.headers.get("origin", "*")
    response = JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Erreur interne du serveur: {str(exc)}"},
    )
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response



@app.get("/", tags=["Système"], summary="Accueil API")
async def root():
    return {
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "docs": "/docs",
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
    except Exception as e:
        details = f"Base de données inaccessible: {str(e)}"

    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "details": details,
        "version": settings.VERSION,
    }


# Inclusion des routes API V1
app.include_router(api_router, prefix=settings.API_V1_STR)
