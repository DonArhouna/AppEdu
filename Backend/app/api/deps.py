"""
Dependances FastAPI (Injection de dependances) :
- Session de base de donnees asynchrone (get_db)
- Authentification JWT et utilisateur courant (get_current_user)
- Controle d'acces base sur les permissions dynamiques (require_permission)

La table declarative ``_GUARD_SPECS`` est l'unique source de verite du RBAC
metier.  Elle definit pour chaque guard :

- la **permission dynamique** exigee (autorite reelle) ;
- la **fenetre de compatibilite legacy**, c'est-a-dire les roles historiques
  qui avaient acces avant la bascule.

De cette table derive aussi ``LEGACY_PERMISSION_MATRIX``, exposee par
``/auth/me`` dans ``permissions_effectives`` : le frontend affiche donc
exactement ce que le backend autorise, sans maintenir de seconde matrice.

Les anciens ``RoleChecker`` (``require_admin``, ``require_secretariat``, ...)
sont conserves pour compatibilite d'import, mais **aucun endpoint metier ne les
utilise plus** : la transition est complete.

``utilisateurs.is_superuser`` n'est jamais consulte comme une autorite : c'est
une projection historique de ``utilisateurs.role``.
"""

from collections import OrderedDict
from types import MappingProxyType
from typing import AsyncGenerator, List, Mapping, Optional, Sequence

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.security import decode_access_token
from app.models.utilisateur import Utilisateur, UserRole
from app.services.rbac_service import effective_permissions


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Fournit une session SQLAlchemy asynchrone avec commit/rollback automatique."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> Utilisateur:
    """Valide le jeton JWT et retourne l'utilisateur courant."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants d'authentification invalides ou session expirée.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if not user_id:
        raise credentials_exception

    stmt = select(Utilisateur).where(Utilisateur.id == int(user_id))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Utilisateur = Depends(get_current_user)
) -> Utilisateur:
    """Vérifie que le compte utilisateur est actif."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce compte utilisateur est désactivé."
        )
    return current_user


class RoleChecker:
    """Vérifie que l'utilisateur possède l'un des rôles requis."""
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: Utilisateur = Depends(get_current_active_user)) -> Utilisateur:
        if user.role not in [role.value for role in self.allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissions insuffisantes pour effectuer cette action."
            )
        return user


require_admin = RoleChecker([UserRole.ADMIN])
require_pedagogie = RoleChecker([UserRole.ADMIN, UserRole.DIRECTEUR_ETUDES])
require_enseignant = RoleChecker([UserRole.ADMIN, UserRole.DIRECTEUR_ETUDES, UserRole.ENSEIGNANT])
require_comptabilite = RoleChecker([UserRole.ADMIN, UserRole.COMPTABILITE])
require_secretariat = RoleChecker([UserRole.ADMIN, UserRole.DIRECTEUR_ETUDES, UserRole.SECRETARIAT])
require_admissions = RoleChecker([UserRole.ADMIN, UserRole.DIRECTEUR_ETUDES, UserRole.SECRETARIAT])
require_academic_context = RoleChecker([UserRole.ADMIN, UserRole.DIRECTEUR_ETUDES])
require_staff = RoleChecker([
    UserRole.ADMIN,
    UserRole.DIRECTEUR_ETUDES,
    UserRole.SECRETARIAT,
    UserRole.ENSEIGNANT,
    UserRole.COMPTABILITE,
])
require_academic_staff = RoleChecker([
    UserRole.ADMIN,
    UserRole.DIRECTEUR_ETUDES,
    UserRole.SECRETARIAT,
    UserRole.ENSEIGNANT,
    UserRole.COMPTABILITE,
])
require_student_registry = RoleChecker([
    UserRole.ADMIN,
    UserRole.DIRECTEUR_ETUDES,
    UserRole.SECRETARIAT,
])
require_student_directory = RoleChecker([
    UserRole.ADMIN,
    UserRole.DIRECTEUR_ETUDES,
    UserRole.SECRETARIAT,
    UserRole.COMPTABILITE,
])


# ---------------------------------------------------------------------------
# Couche dynamique : permissions RBAC
# ---------------------------------------------------------------------------
class PermissionChecker:
    """Verifie qu'un compte porte une permission dynamique donnee.

    Autorise, dans cet ordre :

    1. le role legacy ``ADMIN`` (comptabilite de transition, afin qu'aucun
       compte existant ne perde l'acces pendant le deploiement) ;
    2. les roles legacy explicitement listes dans ``legacy_roles`` ;
    3. un role dynamique actif portant la permission.

    ``is_superuser`` n'est jamais consulte.  Aucune hierarchie de roles n'est
    parcourue : seule une affectation directe peut accorder la permission.
    """

    def __init__(
        self,
        permission_code: str,
        *,
        legacy_roles: Sequence[UserRole] = (),
    ) -> None:
        self.permission_code = permission_code
        self.legacy_roles = tuple(legacy_roles)

    async def __call__(
        self,
        db: AsyncSession = Depends(get_db),
        user: Utilisateur = Depends(get_current_active_user),
    ) -> Utilisateur:
        allowed_legacy = {role.value for role in self.legacy_roles}
        if user.role in allowed_legacy or user.role == UserRole.ADMIN.value:
            return user

        authorization = await effective_permissions(db, user)
        if self.permission_code in authorization.permission_codes:
            return user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Permission requise absente : {self.permission_code}. "
                "Aucun role dynamique ne l'accorde."
            ),
        )


def require_permission(
    permission_code: str,
    *,
    legacy_roles: Sequence[UserRole] = (),
) -> PermissionChecker:
    """Construit un guard exigeant une permission dynamique.

    Utilisation : ``_actor = Depends(require_permission("roles.manage"))``.
    """

    return PermissionChecker(permission_code, legacy_roles=legacy_roles)


#: Guardes de l'administration du RBAC.  Ils remplacent ``require_admin`` sur
#: les routes ``/api/v1/rbac`` : un compte non-admin peut desormais gerer les
#: roles s'il porte reellement ``roles.manage``.
require_rbac_admin = require_permission("roles.manage")
require_users_manage = require_permission("users.manage")
require_audit_read = require_permission("audit.read")


# ---------------------------------------------------------------------------
# Couche dynamique : guards metier consolides
# ---------------------------------------------------------------------------
# _GUARD_SPECS est l'unique source de verite du RBAC metier.  Chaque entree
# declare la permission dynamique exigee ET la fenetre de compatibilite legacy
# (les roles qui avaient acces avant la bascule, d'apres l'inventaire documente
# dans ``RBAC_DYNAMIC.md``).
#
# Deux invariants sont garantis par construction :
#
# 1. **Zero regression** : la fenetre legacy d'un guard contient exactement les
#    roles qui passes avant.  Aucune bascule n'elargit ni ne retrecit l'acces
#    d'un compte existant.
# 2. **Une seule verite** : ``LEGACY_PERMISSION_MATRIX`` est derive de cette
#    meme table, et non recopie.  ``/auth/me`` s'en sert pour exposer
#    ``permissions_effectives`` : le frontend affiche donc exactement ce que
#    le backend autorise, sans maintenir de deuxieme matrice locale.
#
# Aucune hierarchie de roles n'est parcourue : seule une affectation directe
# d'une permission dynamique accorde un acces nouveau.
_ADMIN = UserRole.ADMIN
_DIR = UserRole.DIRECTEUR_ETUDES
_SEC = UserRole.SECRETARIAT
_ENS = UserRole.ENSEIGNANT
_COM = UserRole.COMPTABILITE
_STAFF = (_ADMIN, _DIR, _SEC, _ENS, _COM)
_SECRETARIAT = (_ADMIN, _DIR, _SEC)
_ADMINISTRATION = (_ADMIN,)

_GUARD_SPECS: "OrderedDict[str, tuple[str, tuple[UserRole, ...]]]" = OrderedDict(
    (
        # -- Repertoire et socle academique ------------------------------
        # Campus, departements, filieres, UE, matieres, sessions : ancien
        # ``require_staff`` pour la lecture.
        ("require_academic_read", ("academic.read", _STAFF)),
        # Cycles, niveaux, classes, inscriptions : ancien
        # ``require_student_registry`` / ``require_secretariat`` en lecture.
        ("require_academic_registry_read", ("academic.read", _SECRETARIAT)),
        # Cycles, niveaux, classes, inscriptions, contexte : ancien
        # ``require_pedagogie`` / ``require_academic_context``.
        ("require_academic_write", ("academic.write", (_ADMIN, _DIR))),
        # Ecriture du referentiel structurel et des sessions : ancien
        # ``require_admin`` uniquement.
        ("require_academic_structure_write", ("academic.write", _ADMINISTRATION)),
        # -- Dossiers etudiants -------------------------------------------
        # Recherche et detail : ancien ``require_student_registry``.
        ("require_students_read", ("students.read", _SECRETARIAT)),
        # Repertoire etudiant minimal : ancien ``require_student_directory``.
        ("require_students_directory_read", ("students.read", (_ADMIN, _DIR, _SEC, _COM))),
        # Creation, modification, inscription : ancien ``require_secretariat``.
        ("require_students_write", ("students.write", _SECRETARIAT)),
        # Suppression : ancien ``require_admin`` uniquement.
        ("require_students_delete", ("students.write", _ADMINISTRATION)),
        # -- Admissions ----------------------------------------------------
        ("require_admissions_read", ("admissions.read", _SECRETARIAT)),
        ("require_admissions_write", ("admissions.write", _SECRETARIAT)),
        # -- Pedagogie -----------------------------------------------------
        # Cours, examens, absences : ancien ``require_academic_staff``.
        ("require_pedagogy_read", ("pedagogy.read", _STAFF)),
        # Consultation des notes : ancien ``require_enseignant``.
        ("require_pedagogy_grades_read", ("pedagogy.read", (_ADMIN, _DIR, _ENS))),
        # Saisie et modification : ancien ``require_pedagogie``/``require_enseignant``.
        ("require_pedagogy_write", ("pedagogy.write", (_ADMIN, _DIR, _ENS))),
        # Suppression d'un cours : ancien ``require_admin`` uniquement.
        ("require_pedagogy_delete", ("pedagogy.write", _ADMINISTRATION)),
        # -- Finances --------------------------------------------------------
        ("require_finance_read", ("finance.read", (_ADMIN, _COM))),
        ("require_finance_write", ("finance.write", (_ADMIN, _COM))),
    )
)


def _build_guard(permission_code: str, legacy_roles: "tuple[UserRole, ...]") -> PermissionChecker:
    return require_permission(permission_code, legacy_roles=legacy_roles)


def _build_legacy_matrix() -> "dict[str, frozenset[str]]":
    """Permissions exerables par chaque role legacy, derive de _GUARD_SPECS.

    Pour une permission donnee, le role est retenu si il figurait dans au
    moins une fenetre de compatibilite.  L'union par permission reste exacte :
    aucune permission n'est elargie au-dela des routes ou le role y avait
    historiquement acces.
    """

    matrix: "dict[str, set[str]]" = {}
    for permission_code, legacy_roles in _GUARD_SPECS.values():
        for role in legacy_roles:
            matrix.setdefault(role.value, set()).add(permission_code)
    return {role: frozenset(codes) for role, codes in matrix.items()}


#: Permissions Heritage des roles legacy, derivees de la table ci-dessus.
LEGACY_PERMISSION_MATRIX: "Mapping[str, frozenset[str]]" = MappingProxyType(
    _build_legacy_matrix()
)


def legacy_permissions_for(role: "Optional[str]") -> "frozenset[str]":
    """Permissions historiques d'un role legacy (vide si role inconnu)."""

    return LEGACY_PERMISSION_MATRIX.get((role or "").upper(), frozenset())


# Construction effective des guards a partir de la table.
for _name, _spec in _GUARD_SPECS.items():
    globals()[_name] = _build_guard(_spec[0], _spec[1])
del _name, _spec
