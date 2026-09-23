"""
Agrégation des routeurs de l'API v1.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import setup, auth, sessions, structure, etudiants, pedagogie, finances

api_router = APIRouter()

api_router.include_router(setup.router, prefix="/setup", tags=["Setup Wizard"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentification"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["Sessions Académiques"])
api_router.include_router(structure.router, prefix="/structure", tags=["Structure Académique"])
api_router.include_router(etudiants.router, prefix="/etudiants", tags=["Étudiants"])
api_router.include_router(pedagogie.router, prefix="/pedagogie", tags=["Pédagogie & Notes"])
api_router.include_router(finances.router, prefix="/finances", tags=["Finances & Encaissements"])

