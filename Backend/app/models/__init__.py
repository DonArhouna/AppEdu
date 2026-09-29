"""
Package models : exportation de tous les modèles ORM pour Alembic et l'application.
"""

from app.models.base import Base, TimestampMixin
# Registre des écoles (lot 6) : vit sur la base de contrôle, sans clé
# étrangère vers les bases métier — celles-ci sont physiquement séparées.
from app.models.tenant import Tenant
from app.models.etablissement import Etablissement
from app.models.utilisateur import Utilisateur, UserRole, UserStatus
from app.models.audit import AuditEvent
# Durcissement de l'authentification : reference ``utilisateurs`` par cle
# etrangere, donc importe apres.
from app.models.auth_securite import LoginAttempt, RefreshToken
from app.models.session_academique import SessionAcademique, PeriodePaiement
from app.models.structure import Campus, Departement, Filiere, UniteEnseignement, Matiere
from app.models.academic import Cycle, Niveau, Classe, Inscription
# Salles physiques : reference ``campuses`` par cle etrangere, donc importe
# apres la structure.
from app.models.salle import Salle
from app.models.etudiant import Etudiant
from app.models.pedagogie import Cours, Examen, Note, Absence
from app.models.admissions import Candidature, PieceCandidature, DecisionAdmission
from app.models.admission_views import VueAdmissions
from app.models.finance import GrilleTarifaire, Facture, Paiement, Recu
# Paiements en ligne : reference ``factures``/``etudiants``/``utilisateurs``
# par cle etrangere, donc importe apres eux.
from app.models.paiement_intent import PaiementIntent
# RBAC dynamique.  Importe apres ``utilisateur`` : la table d'affectation y
# reference ``utilisateurs.id`` par cle etrangere.
from app.models.rbac import Permission, Role, RolePermission, UserRoleAssignment
# Import massif d'etudiants : reference ``etudiants`` et ``utilisateurs``
# par cle etrangere, donc importe apres les deux.
from app.models.etudiant_import import EtudiantImportBatch, EtudiantImportRow
# Documents officiels : reference ``etudiants``, ``sessions_academiques``
# et ``utilisateurs`` par cle etrangere, donc importe apres les trois.
from app.models.document_officiel import DocumentOfficiel
# Journal des versions de la configuration institutionnelle : reference
# ``etablissements`` et ``utilisateurs`` par cle etrangere, donc importe apres
# les deux.
from app.models.configuration import ConfigurationVersion
# Deliberation : reference ``etablissements``, ``utilisateurs`` par cle
# etrangere, donc apres les deux ; et ``classes`` / ``sessions_academiques`` /
# ``etudiants``, donc apres le socle academique.
from app.models.deliberation import (
    Deliberation,
    DeliberationDecision,
    ReglesDeliberation,
)
# Relances de facturation : reference ``etudiants`` et ``utilisateurs`` par
# cle etrangere, donc apres les deux.
from app.models.relance import Relance
# Nomenclature de matricule : reference ``etablissements`` et ``utilisateurs``.
from app.models.parametres_matricule import ParametresMatricule

__all__ = [
    "Base",
    "TimestampMixin",
    "Tenant",
    "Etablissement",
    "Utilisateur",
    "UserRole",
    "UserStatus",
    "AuditEvent",
    "LoginAttempt",
    "RefreshToken",
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
    "Salle",
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
    "PaiementIntent",
    "Permission",
    "Role",
    "RolePermission",
    "UserRoleAssignment",
    "EtudiantImportBatch",
    "EtudiantImportRow",
    "DocumentOfficiel",
    "ConfigurationVersion",
    "ReglesDeliberation",
    "Deliberation",
    "DeliberationDecision",
    "Relance",
    "ParametresMatricule",
    "Semestre",
]
