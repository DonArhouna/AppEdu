"""
Script utilitaire pour réinitialiser la base de données (vider les tables)
afin de pouvoir ré-exécuter le Setup Wizard à volonté lors des phases de test.
Usage : python reset_db.py
"""

import asyncio
from app.core.database import get_engine_for_tenant
from app.models.base import Base
import app.models.etablissement
import app.models.utilisateur
import app.models.session_academique
import app.models.structure
import app.models.pedagogie
import app.models.etudiant
import app.models.finance


async def reset_database():
    engine = get_engine_for_tenant("default")
    print("[RESET] Suppression des tables existantes...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("[RESET] Re-creation des tables vierges...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("[RESET] Base de donnees reinitialisee avec succes ! Le Setup Wizard (/setup) est pret.")


if __name__ == "__main__":
    asyncio.run(reset_database())
