"""
Catalogue explicite des permissions techniques et des roles systeme.

Ce module est la source de verite unique partagee par :

- la migration Alembic ``0013_rbac_dynamic`` (seed idempotent du catalogue) ;
- l'application FastAPI (CRUD admin, guards, projection JSON de ``/auth/me``).

Volontaires :

- aucune dependance vers ``app.models`` ni vers la base de donnees, afin que la
  migration puisse importer le catalogue sans charger l'ORM ;
- aucune donnee metier inventee.  Les ``libelle``/``description`` sont des
  metadonnees d'interface (libelles de menu, regroupements) et non des regles
  fonctionnelles ;
- aucune matrice de permissions par role.  Les permissions accordées aux roles
  systeme sont decidées par l'administrateur via l'API, pas par le code.
"""

from types import MappingProxyType
from typing import Mapping


# ---------------------------------------------------------------------------
# Permissions techniques
# ---------------------------------------------------------------------------
class PermissionDefinition:
    """Definition immuable d'une permission technique du catalogue."""

    __slots__ = ("code", "libelle", "description", "domaine", "action")

    def __init__(self, code: str, libelle: str, description: str) -> None:
        self.code = code
        self.libelle = libelle
        self.description = description
        # Convention de nommage : "<domaine>.<action>".  Le découpage sert
        # uniquement au regroupement dans l'interface d'administration.
        self.domaine, _, self.action = code.partition(".")

    def __repr__(self) -> str:  # pragma: no cover - confort de debug
        return f"<PermissionDefinition {self.code}>"


def _permission(code: str, libelle: str, description: str) -> PermissionDefinition:
    if "." not in code:
        raise ValueError(f"Code de permission invalide (attendu domaine.action) : {code!r}")
    return PermissionDefinition(code=code, libelle=libelle, description=description)


#: Catalogue de reference.  Ces 14 permissions sont les seules entrees creees
#: par la migration 0013.  Toute autre permission doit etre creee explicitement
#: par un administrateur via ``POST /api/v1/rbac/permissions``.
PERMISSION_CATALOG: tuple[PermissionDefinition, ...] = (
    _permission("dashboard.read", "Consulter le tableau de bord", "Acces en lecture au tableau de bord et aux indicateurs affiches."),
    _permission("students.read", "Consulter les etudiants", "Acces en lecture au registre des dossiers etudiants."),
    _permission("students.write", "Gerer les etudiants", "Creation, modification et suppression des dossiers etudiants."),
    _permission("admissions.read", "Consulter les admissions", "Acces en lecture aux candidatures, pieces et decisions d'admission."),
    _permission("admissions.write", "Gerer les admissions", "Depot des pieces, decisions d'admission et conversion en dossier etudiant."),
    _permission("academic.read", "Consulter le socle academique", "Acces en lecture aux cycles, niveaux, filieres, unites d'enseignement et matieres."),
    _permission("academic.write", "Gerer le socle academique", "Creation et modification des referentiels du socle academique."),
    _permission("pedagogy.read", "Consulter la pedagogie", "Acces en lecture aux cours, notes, absences et deliberations."),
    _permission("pedagogy.write", "Gerer la pedagogie", "Saisie et modification des cours, notes, absences et parametres de deliberation."),
    _permission("finance.read", "Consulter les finances", "Acces en lecture aux grilles tarifaires, factures, paiements et recus."),
    _permission("finance.write", "Gerer les finances", "Creation et modification des grilles tarifaires, factures, paiements et recus."),
    _permission("users.manage", "Administrer les comptes", "Consultation et administration des comptes utilisateurs."),
    _permission(
        "documents.issue",
        "Emettre les documents officiels",
        "Generation des certificats de scolarite, releves de notes et quitus financiers.",
    ),
    _permission("roles.manage", "Administrer les roles et permissions", "Gestion du catalogue de permissions, des roles et des affectations."),
    _permission("audit.read", "Consulter le journal d'audit", "Acces en lecture des evenements de securite."),
)

#: Index pratique pour la resolution d'une permission depuis son code.
PERMISSION_CODES: frozenset[str] = frozenset(item.code for item in PERMISSION_CATALOG)

#: Regroupements stables pour l'interface d'administration.
PERMISSION_DOMAINS: tuple[str, ...] = tuple(
    dict.fromkeys(item.domaine for item in PERMISSION_CATALOG)
)


def get_permission_definition(code: str) -> PermissionDefinition | None:
    """Retourne la definition du catalogue pour ``code`` ou ``None``."""

    for item in PERMISSION_CATALOG:
        if item.code == code:
            return item
    return None


# ---------------------------------------------------------------------------
# Roles systeme
# ---------------------------------------------------------------------------
class SystemRoleDefinition:
    """Role systeme aligne sur un role legacy ``Utilisateur.role``.

    ``legacy_role`` est la valeur de la colonne historique ``utilisateurs.role``.
    Elle n'est jamais lue comme une autorite : elle sert uniquement de
    projection de compatibilite pour les guards statiques existants.  Elle vaut
    ``None`` pour un role systeme sans equivalent legacy.
    """

    __slots__ = ("code", "libelle", "description", "ordre", "legacy_role")

    def __init__(
        self,
        code: str,
        libelle: str,
        description: str,
        ordre: int,
        legacy_role: str | None = None,
    ) -> None:
        self.code = code
        self.libelle = libelle
        self.description = description
        self.ordre = ordre
        self.legacy_role = legacy_role

    def __repr__(self) -> str:  # pragma: no cover - confort de debug
        return f"<SystemRoleDefinition {self.code} legacy_role={self.legacy_role}>"


#: Les six roles systeme crees par la migration 0013.  Aucun compte n'est cree :
#: seule la structure du role existe, sans permission accordee.
SYSTEM_ROLES: tuple[SystemRoleDefinition, ...] = (
    SystemRoleDefinition(
        "ROLE_ADMIN",
        "Administrateur",
        "Role systeme aligne sur le role legacy ADMIN.",
        10,
        "ADMIN",
    ),
    SystemRoleDefinition(
        "ROLE_DIRECTEUR_ETUDES",
        "Directeur des etudes",
        "Role systeme aligne sur le role legacy DIRECTEUR_ETUDES.",
        20,
        "DIRECTEUR_ETUDES",
    ),
    SystemRoleDefinition(
        "ROLE_SECRETARIAT",
        "Secretariat",
        "Role systeme aligne sur le role legacy SECRETARIAT.",
        30,
        "SECRETARIAT",
    ),
    SystemRoleDefinition(
        "ROLE_COMPTABILITE",
        "Comptabilite",
        "Role systeme aligne sur le role legacy COMPTABILITE.",
        40,
        "COMPTABILITE",
    ),
    SystemRoleDefinition(
        "ROLE_ENSEIGNANT",
        "Enseignant",
        "Role systeme aligne sur le role legacy ENSEIGNANT.",
        50,
        "ENSEIGNANT",
    ),
    SystemRoleDefinition(
        "ROLE_ETUDIANT",
        "Etudiant",
        "Role systeme aligne sur le role legacy ETUDIANT.",
        60,
        "ETUDIANT",
    ),
)

SYSTEM_ROLE_CODES: frozenset[str] = frozenset(item.code for item in SYSTEM_ROLES)

LEGACY_ROLE_TO_SYSTEM_CODE: Mapping[str, str] = MappingProxyType(
    {
        item.legacy_role: item.code
        for item in SYSTEM_ROLES
        if item.legacy_role is not None
    }
)

SYSTEM_CODE_TO_LEGACY_ROLE: Mapping[str, str] = MappingProxyType(
    {
        item.code: item.legacy_role
        for item in SYSTEM_ROLES
        if item.legacy_role is not None
    }
)


def get_system_role_definition(code: str) -> SystemRoleDefinition | None:
    """Retourne la definition d'un role systeme ou ``None``."""

    for item in SYSTEM_ROLES:
        if item.code == code:
            return item
    return None


def normalize_code(value: str) -> str:
    """Normalise un code de role ou de permission (casse et espaces)."""

    return (value or "").strip().upper()


__all__ = [
    "PermissionDefinition",
    "SystemRoleDefinition",
    "PERMISSION_CATALOG",
    "PERMISSION_CODES",
    "PERMISSION_DOMAINS",
    "SYSTEM_ROLES",
    "SYSTEM_ROLE_CODES",
    "LEGACY_ROLE_TO_SYSTEM_CODE",
    "SYSTEM_CODE_TO_LEGACY_ROLE",
    "get_permission_definition",
    "get_system_role_definition",
    "normalize_code",
]
