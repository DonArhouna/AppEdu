"""Schemas Pydantic V2 du RBAC dynamique.

Conventions de reponse :

- les cles metier sont en ``snake_case`` comme le reste de l'API ;
- ``code`` est l'identifiant technique stable d'une permission ou d'un role et
  sert de cle dans les URL ;
- ``roles`` (codes de roles dynamiques) et ``permissions`` (permissions
  effectives) sont des listes triees, donc caches-friendly ;
- ``utilisateurs`` d'un role et ``utilisateurs`` d'un role n'exposent que des
  metadonnees de compte (aucun secret, aucun jeton).
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.user import UserResponse


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------
class PermissionCreate(BaseModel):
    """Creation d'une permission hors catalogue livre par la migration."""

    code: str = Field(
        ...,
        min_length=3,
        max_length=100,
        pattern=r"^[a-z0-9_]+(\.[a-z0-9_]+)+$",
        description="Code technique au format domaine.action (minuscules).",
    )
    libelle: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=2000)
    actif: bool = True

    @field_validator("code")
    @classmethod
    def _normalize_code(cls, value: str) -> str:
        return value.strip().lower()


class PermissionUpdate(BaseModel):
    """Metadonnees modifiables.  Le ``code`` reste immuable."""

    libelle: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=2000)
    actif: Optional[bool] = None


class PermissionResponse(BaseModel):
    id: int
    code: str
    domaine: str
    action: str
    libelle: str
    description: Optional[str] = None
    systeme: bool
    actif: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------
class RoleCreate(BaseModel):
    """Creation d'un role dynamique libre (jamais herite d'un autre role)."""

    code: str = Field(..., min_length=2, max_length=50)
    libelle: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=2000)
    ordre: int = Field(0, ge=0, le=100000)
    actif: bool = True

    @field_validator("code")
    @classmethod
    def _normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class RoleUpdate(BaseModel):
    """Metadonnees modifiables.  Le ``code`` reste immuable."""

    libelle: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=2000)
    ordre: Optional[int] = Field(None, ge=0, le=100000)
    actif: Optional[bool] = None


class RoleResponse(BaseModel):
    id: int
    code: str
    libelle: str
    description: Optional[str] = None
    ordre: int
    systeme: bool
    actif: bool
    # Codes de permissions effectivement accordes au role (actives uniquement).
    permissions: List[str] = Field(default_factory=list)
    # Nombre d'utilisateurs ayant une affectation active sur ce role.
    utilisateurs: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Affectation de permissions a un role
# ---------------------------------------------------------------------------
class RolePermissionsSet(BaseModel):
    """Remplacement de l'ensemble des permissions d'un role (PUT).

    La liste recue fait autorite : une permission absente est retiree du role.
    L'ordre d'appel n'est jamais significatif.
    """

    permissions: List[str] = Field(default_factory=list, max_length=500)
    motif: Optional[str] = Field(None, max_length=2000)

    @field_validator("permissions")
    @classmethod
    def _normalize(cls, value: List[str]) -> List[str]:
        return sorted({(item or "").strip().lower() for item in value if (item or "").strip()})


class RolePermissionAdd(BaseModel):
    """Ajout incrementa d'une permission a un role (POST)."""

    permission: str = Field(..., min_length=3, max_length=100)
    motif: Optional[str] = Field(None, max_length=2000)

    @field_validator("permission")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return value.strip().lower()


# ---------------------------------------------------------------------------
# Affectation de roles a des utilisateurs
# ---------------------------------------------------------------------------
class RoleUsersAssign(BaseModel):
    """Affectation (ou reactivation) d'un role a une liste de comptes."""

    user_ids: List[int] = Field(..., min_length=1, max_length=500)
    motif: Optional[str] = Field(None, max_length=2000)
    aligner_role_legacy: bool = Field(
        False,
        description=(
            "Projette le role systeme sur la colonne legacy utilisateurs.role. "
            "Refuse pour un role sans equivalent legacy. "
            "Desactive l'affectation si elle existe deja au lieu d'echouer."
        ),
    )


class UserRoleAssignmentResponse(BaseModel):
    user_id: int
    role_id: int
    role_code: str
    role_libelle: str
    role_systeme: bool
    actif: bool
    motif: Optional[str] = None
    attribue_par: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoleUsersResponse(BaseModel):
    role_code: str
    affectes: List[int] = Field(default_factory=list)
    deja_affectes: List[int] = Field(default_factory=list)
    reponses: List[UserRoleAssignmentResponse] = Field(default_factory=list)
    legacy_role_aligne: Optional[str] = None


# ---------------------------------------------------------------------------
# Vues utilisateur
# ---------------------------------------------------------------------------
class RbacUserResponse(BaseModel):
    """Compte et ses roles/permissions dynamiques (aucun secret)."""

    id: int
    email: str
    nom: str
    prenom: str
    role: str
    is_active: bool
    roles: List[str] = Field(default_factory=list)
    role_labels: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    authz_version: Optional[str] = None


class EffectivePermissionsResponse(BaseModel):
    """Autorite effective resolue pour un compte donne."""

    user_id: int
    role: str
    legacy_role_is_admin: bool
    roles: List[str] = Field(default_factory=list)
    role_labels: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    permission_domains: List[str] = Field(default_factory=list)
    authz_version: Optional[str] = None


class CurrentUserResponse(UserResponse):
    """Contrat etendu de ``GET /auth/me``.

    Les champs legacy de ``UserResponse`` sont inchanges : les clients existants
    continuent de lire ``role``/``is_superuser``.  Les champs ``roles``,
    ``permissions``, ``permissions_effectives`` et ``authz_version`` sont additifs.

    Distinction importante entre les deux listes de permissions :

    - ``permissions`` est l'**autorite dynamique pure** : uniquement ce que les
      roles dynamiques affectes au compte accordent.  C'est la source de verite
      pour l'ecran d'administration des roles.
    - ``permissions_effectives`` est le **droit reellement exerçable** : la
      reunion des permissions dynamiques et de la fenetre de compatibilite du
      role legacy.  C'est ce que le backend accorde reellement sur chaque
      endpoint, et donc ce que l'interface doit utiliser pour afficher un menu
      ou autoriser une vue.  Les deux listes sont derivees de la meme table
      serveur : le frontend ne conserve aucune matrice locale.
    """

    roles: List[str] = Field(
        default_factory=list,
        description="Codes des roles dynamiques actifs portes par le compte.",
    )
    permissions: List[str] = Field(
        default_factory=list,
        description="Autorite dynamique pure (allow-only, sans heritage).",
    )
    permissions_effectives: List[str] = Field(
        default_factory=list,
        description=(
            "Droits reellement exerçables : permissions dynamiques reunionies "
            "avec la fenetre de compatibilite du role legacy."
        ),
    )
    authz_version: Optional[str] = Field(
        None,
        description="Horodatage ISO de la derniere modification d'autorite.",
    )


__all__ = [
    "CurrentUserResponse",
    "EffectivePermissionsResponse",
    "PermissionCreate",
    "PermissionResponse",
    "PermissionUpdate",
    "RbacUserResponse",
    "RoleCreate",
    "RolePermissionAdd",
    "RolePermissionsSet",
    "RoleResponse",
    "RoleUpdate",
    "RoleUsersAssign",
    "RoleUsersResponse",
    "UserRoleAssignmentResponse",
]
