"""
Agrégation des routeurs de l'API v1.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    setup,
    institution,
    auth,
    sessions,
    structure,
    academic,
    etudiants,
    etudiants_import,
    documents,
    pedagogie,
    finances,
    users,
    portals,
    admissions,
    admission_views,
    context,
    audit,
    rbac,
)

api_router = APIRouter()

api_router.include_router(setup.router, prefix="/setup", tags=["Setup Wizard"])
api_router.include_router(
    institution.router,
    prefix="/institution",
    tags=["Configuration institutionnelle"],
)
api_router.include_router(auth.router, prefix="/auth", tags=["Authentification"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["Sessions Académiques"])
api_router.include_router(structure.router, prefix="/structure", tags=["Structure Académique"])
api_router.include_router(academic.router, prefix="/academic", tags=["Socle Académique"])
# Documents officiels : consultation, emission, duplicata, telechargement.
api_router.include_router(
    documents.router, prefix="/documents", tags=["Documents officiels"]
)
# Import massif : analyse (dry-run) puis validation explicite.
# Monte AVANT ``etudiants`` : ``/etudiants/{etudiant_id}`` est un GET et
# capterait sinon ``/etudiants/import``.
api_router.include_router(
    etudiants_import.router,
    prefix="/etudiants/import",
    tags=["Import massif d'étudiants"],
)
api_router.include_router(etudiants.router, prefix="/etudiants", tags=["Étudiants"])
api_router.include_router(pedagogie.router, prefix="/pedagogie", tags=["Pédagogie & Notes"])
api_router.include_router(finances.router, prefix="/finances", tags=["Finances & Encaissements"])
api_router.include_router(users.router, prefix="/users", tags=["Administration des utilisateurs"])
api_router.include_router(portals.router, prefix="/portail", tags=["Portails auto-service"])
api_router.include_router(admissions.router, prefix="/admissions", tags=["Admissions"])
api_router.include_router(admission_views.router, prefix="/admissions", tags=["Vues d'admissions"])
api_router.include_router(context.router, prefix="/context", tags=["Contexte académique"])
api_router.include_router(audit.router, prefix="/audit", tags=["Audit de sécurité"])
# RBAC dynamique.  Toutes les routes exigent la permission ``roles.manage``,
# ce qui laisse passer ADMIN legacy pendant la transition.
api_router.include_router(rbac.router, prefix="/rbac", tags=["RBAC dynamique"])

