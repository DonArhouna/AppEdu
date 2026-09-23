"""
Gestion des connexions asynchrones SQLAlchemy 2.0 et routage multi-tenant.
Supporte à la fois le mode Standalone (Client Unique On-premise) et Multi-Tenant (SaaS).
"""

from typing import Dict, AsyncGenerator, Any
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker
)
from app.core.config import settings
from app.models.base import Base

# Cache des moteurs de base de données par tenant pour réutilisation optimale des pools
_engines_cache: Dict[str, AsyncEngine] = {}
_sessionmakers_cache: Dict[str, async_sessionmaker[AsyncSession]] = {}


def get_tenant_database_url(tenant_id: str = "default") -> str:
    """
    Détermine l'URL de connexion PostgreSQL cible pour un tenant donné.
    En mode standalone, retourne la DATABASE_URL principale.
    En mode multi_tenant, génère la connexion isolée par tenant.
    """
    if settings.TENANT_MODE == "standalone" or tenant_id == "default":
        return settings.DATABASE_URL
    
    # Construction dynamique pour base dédiée par client
    safe_tenant = "".join(c for c in tenant_id if c.isalnum() or c in ("_", "-")).lower()
    return f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/emp_tenant_{safe_tenant}"


def get_engine_for_tenant(tenant_id: str = "default") -> AsyncEngine:
    """Retourne ou instancie le moteur asynchrone SQLAlchemy pour le tenant."""
    if tenant_id not in _engines_cache:
        db_url = get_tenant_database_url(tenant_id)
        kwargs: Dict[str, Any] = {
            "echo": settings.DEBUG and settings.ENVIRONMENT == "development",
        }
        if "sqlite" in db_url:
            kwargs["connect_args"] = {"check_same_thread": False}
        else:
            kwargs["pool_size"] = 10
            kwargs["max_overflow"] = 20
            kwargs["pool_pre_ping"] = True

        engine = create_async_engine(db_url, **kwargs)
        _engines_cache[tenant_id] = engine
    return _engines_cache[tenant_id]


def get_sessionmaker_for_tenant(tenant_id: str = "default") -> async_sessionmaker[AsyncSession]:
    """Retourne la fabrique de sessions asynchrones pour le tenant."""
    if tenant_id not in _sessionmakers_cache:
        engine = get_engine_for_tenant(tenant_id)
        session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False
        )
        _sessionmakers_cache[tenant_id] = session_factory
    return _sessionmakers_cache[tenant_id]


# Sessionmaker par défaut
async_session_factory = get_sessionmaker_for_tenant("default")


async def get_async_db(tenant_id: str = "default") -> AsyncGenerator[AsyncSession, None]:
    """Générateur de session asynchrone avec gestion automatique de transaction."""
    session_factory = get_sessionmaker_for_tenant(tenant_id)
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
