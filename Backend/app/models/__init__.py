"""
Package models : exportation de tous les modèles ORM pour Alembic et l'application.
"""

from app.models.base import Base, TimestampMixin
from app.models.etablissement import Etablissement
from app.models.utilisateur import Utilisateur, UserRole, UserStatus
from app.models.audit import AuditEvent
from app.models.session_academique import SessionAcademique, PeriodePaiement
from app.models.structure import Campus, Departement, Filiere, UniteEnseignement, Matiere
from app.models.academic import Cycle, Niveau, Classe, Inscription
from app.models.etudiant import Etudiant
from app.models.pedagogie import Cours, Examen, Note, Absence
from app.models.admissions import Candidature, PieceCandidature, DecisionAdmission
from app.models.admission_views import VueAdmissions
from app.models.finance import GrilleTarifaire, Facture, Paiement, Recu
# RBAC dynamique.  Importe apres ``utilisateur`` : la table d'affectation y
# reference ``utilisateurs.id`` par cle etrangere.
from app.models.rbac import Permission, Role, RolePermission, UserRoleAssignment
# Import massif d'etudiants : reference ``etudiants`` et ``utilisateurs``
# par cle etrangere, donc importe apres les deux.
from app.models.etudiant_import import EtudiantImportBatch, EtudiantImportRow

__all__ = [
    "Base",
    "TimestampMixin",
    "Etablissement",
    "Utilisateur",
    "UserRole",
    "UserStatus",
    "AuditEvent",
    "SessionAcademique",
    "PeriodePaiement",
    "Campus",
    "Departement",
    "Filiere",
    "UniteEnseignement",
    "Matiere",
    "Cycle",
    "Niveau",
    "Classe",
    "Inscription",
    "Etudiant",
    "Cours",
    "Examen",
    "Note",
    "Absence",
    "Candidature",
    "PieceCandidature",
    "DecisionAdmission",
    "VueAdmissions",
    "GrilleTarifaire",
    "Facture",
    "Paiement",
    "Recu",
    "Permission",
    "Role",
    "RolePermission",
    "UserRoleAssignment",
    "EtudiantImportBatch",
    "EtudiantImportRow",
]
