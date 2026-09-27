"""
Agrégation des routeurs de l'API v1.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    setup,
    institution,
    matricule,
    deliberation,
    auth,
    sessions,
    structure,
    semestres,
    academic,
    etudiants,
    export,
    etudiants_import,
    documents,
    pedagogie,
    bulletins,
    note_import,
    finances,
    relances,
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
    deliberation.router,
    prefix="/deliberation",
    tags=["Deliberation & jury"],
)
api_router.include_router(
    institution.router,
    prefix="/institution",
    tags=["Configuration institutionnelle"],
)
api_router.include_router(
    matricule.router,
    prefix="/institution",
    tags=["Configuration institutionnelle"],
)
api_router.include_router(auth.router, prefix="/auth", tags=["Authentification"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["Sessions Académiques"])
api_router.include_router(structure.router, prefix="/structure", tags=["Structure Académique"])
# Les semestres sont montes sur ``/academic`` : ils appartiennent a
# une session, au meme titre qu'une promotion.
api_router.include_router(
    semestres.router,
    prefix="/academic",
    tags=["Semestres"],
)
api_router.include_router(academic.router, prefix="/academic", tags=["Socle Académique"])
# Documents officiels : consultation, emission, duplicata, telechargement.
api_router.include_router(
    documents.router, prefix="/documents", tags=["Documents officiels"]
)
# Import massif : analyse (dry-run) puis validation explicite.
# L'export se monte avant ``etudiants`` : ``/etudiants/{id}`` est
# un GET et capterait ``/etudiants/export``.
api_router.include_router(
    export.router,
    prefix="/etudiants",
    tags=["Registre étudiants"],
)
# Monte AVANT ``etudiants`` : ``/etudiants/{etudiant_id}`` est un GET et
# capterait sinon ``/etudiants/import``.
api_router.include_router(
    etudiants_import.router,
    prefix="/etudiants/import",
    tags=["Import massif d'étudiants"],
)
api_router.include_router(etudiants.router, prefix="/etudiants", tags=["Étudiants"])
# L'import de notes est sous ``/pedagogie/import/...``, pas
# ``/pedagogie/notes/import/...`` : ce dernier chemin serait capte par
# ``/notes/{note_id}``, qui est un GET. L'ordre de montage n'a donc ici
# aucune importance.
api_router.include_router(
    note_import.router,
    prefix="/pedagogie",
    tags=["Import de notes"],
)
api_router.include_router(pedagogie.router, prefix="/pedagogie", tags=["Pédagogie & Notes"])
# Le bulletin est montee sous ``/pedagogie`` : c'est un document de notes, et
# il se telecharge au meme endroit que les notes qu'il reprend. La route
# litterale ``/bulletins/...`` ne peut pas etre captee par une route a
# parametre de la pedagogie, qui n'en a pas de ce nom.
api_router.include_router(
    bulletins.router,
    prefix="/pedagogie",
    tags=["Bulletins de notes"],
)
api_router.include_router(finances.router, prefix="/finances", tags=["Finances & Encaissements"])
api_router.include_router(
    relances.router,
    prefix="/finances",
    tags=["Relances de facturation"],
)
api_router.include_router(users.router, prefix="/users", tags=["Administration des utilisateurs"])
api_router.include_router(portals.router, prefix="/portail", tags=["Portails auto-service"])
api_router.include_router(admissions.router, prefix="/admissions", tags=["Admissions"])
api_router.include_router(admission_views.router, prefix="/admissions", tags=["Vues d'admissions"])
api_router.include_router(context.router, prefix="/context", tags=["Contexte académique"])
api_router.include_router(audit.router, prefix="/audit", tags=["Audit de sécurité"])
# RBAC dynamique.  Toutes les routes exigent la permission ``roles.manage``,
# ce qui laisse passer ADMIN legacy pendant la transition.
api_router.include_router(rbac.router, prefix="/rbac", tags=["RBAC dynamique"])

