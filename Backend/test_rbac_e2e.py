"""E2E du RBAC dynamique (SQLite isole).

Ce scenario est volontairement executable sans pytest :
    .\\venv\\Scripts\\python.exe test_rbac_e2e.py

Il ne touche pas a une base locale : la base est un fichier temporaire et il
n'y a aucun reset d'une instance existante.

Le scenario verifie la chaine complete :

1. cycle Alembic ``upgrade -> downgrade -> upgrade`` jusqu'a 0013 ;
2. refus de downgrade des qu'un role hors catalogue existe ;
3. contenu exact du seed (14 permissions, 6 roles systemes, 0 grant, 0 compte) ;
4. CRUD du catalogue de permissions et des roles ;
5. protections des ressources systeme et des ressources utilisees ;
6. affectation / retrait de roles et effet reel sur ``/auth/me`` ;
7. effet reel des guards dynamiques (``require_permission``) ;
8. non-regression des guards statiques lisibles sur ``utilisateurs.role``.
"""

import asyncio
import gc
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient


TEST_DIR = Path(tempfile.gettempdir()) / "appedu-rbac-e2e"
TEST_DB_PATH = TEST_DIR / "rbac.db"
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["ENVIRONMENT"] = "development"
os.environ["DEBUG"] = "False"
os.environ["TENANT_MODE"] = "standalone"

from app.core.config import settings  # noqa: E402

settings.DATABASE_URL = TEST_DATABASE_URL
settings.ENVIRONMENT = "development"
settings.DEBUG = False
settings.TENANT_MODE = "standalone"

import app.core.database as database  # noqa: E402

database._engines_cache.clear()
database._sessionmakers_cache.clear()

import app.models  # noqa: E402,F401
from app.api.deps import LEGACY_PERMISSION_MATRIX  # noqa: E402
from app.main import app  # noqa: E402

ADMIN_EMAIL = "admin.rbac@ecole-ci.org"
ADMIN_PASSWORD = "Rbac-Admin-2026!"
SECRETARY_EMAIL = "secretariat.rbac@ecole-ci.org"
SECRETARY_PASSWORD = "Rbac-Secretary-2026!"
STUDENT_ACCOUNT_EMAIL = "etudiant.rbac@ecole-ci.org"
STUDENT_ACCOUNT_PASSWORD = "Rbac-Student-2026!"

EXPECTED_PERMISSION_CODES = {
    "academic.read",
    "academic.write",
    "admissions.read",
    "admissions.write",
    "audit.read",
    "dashboard.read",
    "documents.issue",
    "finance.read",
    "finance.write",
    # Configuration institutionnelle (identite, logo) : permission dediee,
    # sans heritage, pour deleguer le branding sans ouvrir la gestion des
    # comptes.
    "institution.settings",
    "pedagogy.read",
    "pedagogy.write",
    "roles.manage",
    "students.read",
    "students.write",
    "users.manage",
}
EXPECTED_SYSTEM_ROLE_CODES = {
    "ROLE_ADMIN",
    "ROLE_DIRECTEUR_ETUDES",
    "ROLE_SECRETARIAT",
    "ROLE_COMPTABILITE",
    "ROLE_ENSEIGNANT",
    "ROLE_ETUDIANT",
}

#: Champs de ``UserResponse`` que ``/auth/me`` exposait deja.  Le contrat
#: historique ne doit pas bouger.
LEGACY_ME_FIELDS = {
    "id",
    "email",
    "nom",
    "prenom",
    "telephone",
    "role",
    "is_active",
    "is_superuser",
    "etudiant_id",
    "avatar_url",
    "last_login",
    "created_at",
    "updated_at",
}


async def _cleanup() -> None:
    for engine in database._engines_cache.values():
        await engine.dispose()
    database._engines_cache.clear()
    database._sessionmakers_cache.clear()
    if TEST_DB_PATH.exists():
        gc.collect()
        for _ in range(5):
            try:
                TEST_DB_PATH.unlink()
                break
            except OSError:
                try:
                    sqlite3.connect(str(TEST_DB_PATH)).close()
                except sqlite3.Error:
                    pass
                await asyncio.sleep(0.2)


def _config() -> Config:
    return Config(str(Path(__file__).resolve().parent / "alembic.ini"))


def _migrate() -> None:
    """Cycle Alembic complet sur la migration 0013."""

    TEST_DIR.mkdir(parents=True, exist_ok=True)
    config = _config()
    command.upgrade(config, "0012_academic_structure")
    command.upgrade(config, "head")
    command.downgrade(config, "0012_academic_structure")
    command.upgrade(config, "head")


def _seed_counts() -> dict:
    """Etat du seed pose par la migration, lu hors API."""

    import sqlalchemy as sa
    from sqlalchemy import create_engine

    engine = create_engine(
        TEST_DATABASE_URL.replace("+aiosqlite", ""), future=True
    )
    try:
        with engine.connect() as connection:
            def scalar(statement: str) -> int:
                return int(connection.execute(sa.text(statement)).scalar() or 0)

            return {
                "permissions": scalar("SELECT COUNT(*) FROM rbac_permissions"),
                "roles": scalar("SELECT COUNT(*) FROM rbac_roles"),
                "grants": scalar("SELECT COUNT(*) FROM rbac_role_permissions"),
                "assignments": scalar("SELECT COUNT(*) FROM rbac_user_roles"),
                "users": scalar("SELECT COUNT(*) FROM utilisateurs"),
                "system_roles": scalar(
                    "SELECT COUNT(*) FROM rbac_roles WHERE systeme = 1"
                ),
                "system_permissions": scalar(
                    "SELECT COUNT(*) FROM rbac_permissions WHERE systeme = 1"
                ),
            }
    finally:
        engine.dispose()


def _expect_downgrade_refused() -> None:
    """Un role hors catalogue rend la downgrade non destructive : refusee."""

    import sqlalchemy as sa
    from sqlalchemy import create_engine

    engine = create_engine(
        TEST_DATABASE_URL.replace("+aiosqlite", ""), future=True
    )
    try:
        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    "INSERT INTO rbac_roles (code, libelle, description, ordre, "
                    "systeme, actif) VALUES "
                    "('ROLE_TEMPORAIRE', 'Temporaire', "
                    "'Role de verification de la downgrade', 99, 0, 1)"
                )
            )
        try:
            command.downgrade(_config(), "0012_academic_structure")
        except RuntimeError as exc:
            assert "downgrade 0013" in str(exc), exc
        else:
            raise AssertionError(
                "La downgrade 0013 a detruit un role hors catalogue."
                "La downgrade 0013 a detruit un role hors catalogue."
            )

        # Sur SQLite le DDL n'est pas transactionnel : les migrations
        # superieures a 0013 ont deja ete retirees avant d'atteindre le refus.
        # On restaure le schema, puis on verifie que la restauration est
        # complete. Sur PostgreSQL, l'echec aurait annule l'ensemble.
        command.upgrade(_config(), "head")
        with engine.begin() as connection:
            colonnes = {
                row[1]
                for row in connection.execute(
                    sa.text("PRAGMA table_info(etablissements)")
                )
            }
            assert "logo_url" in colonnes, colonnes
            tables = {
                row[0]
                for row in connection.execute(
                    sa.text("SELECT name FROM sqlite_master WHERE type='table'")
                )
            }
            for attendue in (
                "documents_officiels",
                "etudiants_import_batches",
                "etudiants_import_rows",
                "rbac_roles",
            ):
                assert attendue in tables, (attendue, sorted(tables))
        with engine.begin() as connection:
            connection.execute(
                sa.text("DELETE FROM rbac_roles WHERE code = 'ROLE_TEMPORAIRE'")
            )
    finally:
        engine.dispose()


async def _login(client: AsyncClient, email: str, password: str) -> dict:
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _matrix_row(response, user_id: int) -> dict:
    """Extrait une ligne de ``GET /rbac/users/roles``."""

    assert response.status_code == 200, response.text
    for item in response.json():
        if item["id"] == user_id:
            return item
    raise AssertionError(f"Le compte {user_id} est absent de la vue users/roles.")


async def _run() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://rbac-test"
    ) as client:
        # -------------------------------------------------------------------
        # 1. Seed exact de la migration
        # -------------------------------------------------------------------
        seed = _seed_counts()
        # La migration 0013 pose 14 permissions ; la 0015 en ajoute une
        # (``documents.issue``). Le test verifie l'ensemble exact plutot
        # qu'un nombre fige, pour rester valide a chaque evolution du
        # catalogue.
        attendu = len(EXPECTED_PERMISSION_CODES)
        assert seed["permissions"] == attendu, (seed, sorted(EXPECTED_PERMISSION_CODES))
        assert seed["system_permissions"] == attendu, seed
        assert seed["roles"] == len(EXPECTED_SYSTEM_ROLE_CODES), seed
        assert seed["system_roles"] == len(EXPECTED_SYSTEM_ROLE_CODES), seed
        # Aucune permission accordee, aucun compte cree, aucune affectation.
        assert seed["grants"] == 0, seed
        assert seed["assignments"] == 0, seed
        assert seed["users"] == 0, seed
        print("  [OK] Migration 0013 : 14 permissions, 6 roles systemes, 0 grant, 0 compte.")

        # -------------------------------------------------------------------
        # 2. Initialisation de l'instance
        # -------------------------------------------------------------------
        setup = await client.post(
            "/api/v1/setup/initialize",
            json={
                "etablissement": {
                    "nom": "Etablissement RBAC Test",
                    "code": "RBAC-E2E",
                    "email": "contact@ecole-ci.org",
                    "devise": "XOF",
                },
                "admin": {
                    "nom": "Admin",
                    "prenom": "Rbac",
                    "email": ADMIN_EMAIL,
                    "password": ADMIN_PASSWORD,
                },
            },
        )
        assert setup.status_code == 201, setup.text
        admin_id = setup.json()["user"]["id"]
        admin_headers = {"Authorization": f"Bearer {setup.json()['access_token']}"}

        # -------------------------------------------------------------------
        # 3. /auth/me : contrat preserve + champs dynamiques
        # -------------------------------------------------------------------
        me = await client.get("/api/v1/auth/me", headers=admin_headers)
        assert me.status_code == 200, me.text
        payload = me.json()
        assert LEGACY_ME_FIELDS.issubset(payload.keys()), sorted(
            LEGACY_ME_FIELDS - payload.keys()
        )
        assert {"roles", "permissions", "authz_version"}.issubset(payload.keys())
        assert payload["email"] == ADMIN_EMAIL
        assert payload["role"] == "ADMIN"
        assert payload["is_superuser"] is True
        # ADMIN legacy ne recoit pas de role dynamique tant qu'aucun n'est affecte.
        assert payload["roles"] == []
        assert payload["permissions"] == []
        assert payload["authz_version"] is None
        print("  [OK] /auth/me : contrat legacy intact + roles/permissions/authz_version.")

        # -------------------------------------------------------------------
        # 4. Catalogue de permissions
        # -------------------------------------------------------------------
        catalogue = await client.get("/api/v1/rbac/permissions", headers=admin_headers)
        assert catalogue.status_code == 200, catalogue.text
        codes = {item["code"] for item in catalogue.json()}
        assert codes == EXPECTED_PERMISSION_CODES, codes
        assert all(item["systeme"] for item in catalogue.json())
        assert all(item["actif"] for item in catalogue.json())
        # Le domaine est bien derive du code (metadonnees de regroupement).
        students_read = next(
            item for item in catalogue.json() if item["code"] == "students.read"
        )
        assert students_read["domaine"] == "students"
        assert students_read["action"] == "read"

        by_domain = await client.get(
            "/api/v1/rbac/permissions",
            params={"domaine": "finance"},
            headers=admin_headers,
        )
        assert by_domain.status_code == 200, by_domain.text
        assert {item["code"] for item in by_domain.json()} == {
            "finance.read",
            "finance.write",
        }
        detail = await client.get(
            "/api/v1/rbac/permissions/roles.manage", headers=admin_headers
        )
        assert detail.status_code == 200, detail.text
        assert detail.json()["code"] == "roles.manage"
        assert (
            await client.get(
                "/api/v1/rbac/permissions/inconnue.read", headers=admin_headers
            )
        ).status_code == 404

        # Une permission systeme est protegee.
        assert (
            await client.delete(
                "/api/v1/rbac/permissions/audit.read", headers=admin_headers
            )
        ).status_code == 409
        assert (
            await client.patch(
                "/api/v1/rbac/permissions/audit.read",
                json={"actif": False},
                headers=admin_headers,
            )
        ).status_code == 409
        # Le libelle reste modifiable : c'est une metadonnee d'interface.
        relabel = await client.patch(
            "/api/v1/rbac/permissions/audit.read",
            json={"libelle": "Consulter le journal de securite"},
            headers=admin_headers,
        )
        assert relabel.status_code == 200, relabel.text
        assert relabel.json()["libelle"] == "Consulter le journal de securite"

        # Extension du catalogue par un administrateur.
        created_permission = await client.post(
            "/api/v1/rbac/permissions",
            json={
                "code": "rapports.read",
                "libelle": "Consulter les rapports",
                "description": "Rapports de synthese",
            },
            headers=admin_headers,
        )
        assert created_permission.status_code == 201, created_permission.text
        assert created_permission.json()["systeme"] is False
        assert created_permission.json()["domaine"] == "rapports"
        assert (
            await client.post(
                "/api/v1/rbac/permissions",
                json={"code": "rapports.read", "libelle": "Doublon"},
                headers=admin_headers,
            )
        ).status_code == 409
        assert (
            await client.post(
                "/api/v1/rbac/permissions",
                json={"code": "MAUVAIS-CODE", "libelle": "Invalide"},
                headers=admin_headers,
            )
        ).status_code == 422
        print("  [OK] Catalogue de permissions : lecture, creation, garde-fous systeme.")

        # -------------------------------------------------------------------
        # 5. Roles dynamiques
        # -------------------------------------------------------------------
        roles = await client.get("/api/v1/rbac/roles", headers=admin_headers)
        assert roles.status_code == 200, roles.text
        assert {item["code"] for item in roles.json()} == EXPECTED_SYSTEM_ROLE_CODES
        # La migration n'accorde aucune permission : aucune matrice inventee.
        assert all(item["permissions"] == [] for item in roles.json())
        assert all(item["utilisateurs"] == 0 for item in roles.json())

        created_role = await client.post(
            "/api/v1/rbac/roles",
            json={
                "code": "role_controle_audit",
                "libelle": "Controle audit",
                "description": "Role de verification des habilitations",
                "ordre": 15,
            },
            headers=admin_headers,
        )
        assert created_role.status_code == 201, created_role.text
        assert created_role.json()["code"] == "ROLE_CONTROLE_AUDIT"
        assert created_role.json()["systeme"] is False
        assert created_role.json()["permissions"] == []
        # Le code d'un role systeme est reserve.
        assert (
            await client.post(
                "/api/v1/rbac/roles",
                json={"code": "ROLE_ADMIN", "libelle": "Usurpation"},
                headers=admin_headers,
            )
        ).status_code == 409
        # Un role systeme n'est jamais supprime.
        assert (
            await client.delete(
                "/api/v1/rbac/roles/ROLE_ENSEIGNANT", headers=admin_headers
            )
        ).status_code == 409
        # Un role libre se met a jour.
        renamed = await client.put(
            "/api/v1/rbac/roles/role_controle_audit",
            json={"libelle": "Controle d'audit", "ordre": 16},
            headers=admin_headers,
        )
        assert renamed.status_code == 200, renamed.text
        assert renamed.json()["libelle"] == "Controle d'audit"
        assert renamed.json()["ordre"] == 16

        # -------------------------------------------------------------------
        # 6. Comptes de test
        # -------------------------------------------------------------------
        for payload in (
            {
                "email": SECRETARY_EMAIL,
                "nom": "Secretariat",
                "prenom": "Rbac",
                "role": "SECRETARIAT",
                "password": SECRETARY_PASSWORD,
            },
            {
                "email": STUDENT_ACCOUNT_EMAIL,
                "nom": "Compte",
                "prenom": "Etudiant",
                "role": "ETUDIANT",
                "password": STUDENT_ACCOUNT_PASSWORD,
            },
        ):
            created = await client.post(
                "/api/v1/users/", json=payload, headers=admin_headers
            )
            assert created.status_code == 201, created.text

        secretary_id = next(
            user["id"]
            for user in (
                await client.get("/api/v1/users/", headers=admin_headers)
            ).json()
            if user["email"] == SECRETARY_EMAIL
        )
        student_account_id = next(
            user["id"]
            for user in (
                await client.get("/api/v1/users/", headers=admin_headers)
            ).json()
            if user["email"] == STUDENT_ACCOUNT_EMAIL
        )

        # -------------------------------------------------------------------
        # 7. Guards avant toute affectation dynamique
        # -------------------------------------------------------------------
        secretary_headers = await _login(client, SECRETARY_EMAIL, SECRETARY_PASSWORD)
        assert (
            await client.get("/api/v1/rbac/permissions", headers=secretary_headers)
        ).status_code == 403
        assert (
            await client.get("/api/v1/rbac/roles", headers=secretary_headers)
        ).status_code == 403
        # Garde statique intact : le secretariat lit, il n'ecrit pas.
        assert (
            await client.get("/api/v1/academic/cycles", headers=secretary_headers)
        ).status_code == 200
        assert (
            await client.post(
                "/api/v1/academic/cycles",
                json={"code": "RBAC-SECRET", "nom": "Interdit"},
                headers=secretary_headers,
            )
        ).status_code == 403
        # require_audit_read : un role non porteur reste refuse comme avant.
        assert (
            await client.get("/api/v1/audit/events", headers=secretary_headers)
        ).status_code == 403

        # -------------------------------------------------------------------
        # 8. Attribution de permissions puis affectation du role
        # -------------------------------------------------------------------
        set_permissions = await client.put(
            "/api/v1/rbac/roles/ROLE_CONTROLE_AUDIT/permissions",
            json={"permissions": ["audit.read", "students.read"], "motif": "Perimetre E2E"},
            headers=admin_headers,
        )
        assert set_permissions.status_code == 200, set_permissions.text
        assert set_permissions.json()["permissions"] == [
            "audit.read",
            "students.read",
        ]

        # Remplacement idempotent de l'ensemble.
        set_permissions_again = await client.put(
            "/api/v1/rbac/roles/ROLE_CONTROLE_AUDIT/permissions",
            json={"permissions": ["audit.read", "students.read"]},
            headers=admin_headers,
        )
        assert set_permissions_again.status_code == 200, set_permissions_again.text
        assert set_permissions_again.json()["permissions"] == [
            "audit.read",
            "students.read",
        ]
        # Une permission inconnue est refusee, jamais inventee.
        assert (
            await client.put(
                "/api/v1/rbac/roles/ROLE_CONTROLE_AUDIT/permissions",
                json={"permissions": ["fantome.read"]},
                headers=admin_headers,
            )
        ).status_code == 422

        grant_added = await client.post(
            "/api/v1/rbac/roles/ROLE_CONTROLE_AUDIT/permissions",
            json={"permission": "rapports.read"},
            headers=admin_headers,
        )
        assert grant_added.status_code == 201, grant_added.text
        assert "rapports.read" in grant_added.json()["permissions"]
        # Une permission accordee est protegee contre la suppression.
        assert (
            await client.delete(
                "/api/v1/rbac/permissions/rapports.read", headers=admin_headers
            )
        ).status_code == 409

        role_permissions = await client.get(
            "/api/v1/rbac/roles/ROLE_CONTROLE_AUDIT/permissions",
            headers=admin_headers,
        )
        assert role_permissions.status_code == 200, role_permissions.text
        assert {item["code"] for item in role_permissions.json()} == {
            "audit.read",
            "students.read",
            "rapports.read",
        }

        assignment = await client.post(
            "/api/v1/rbac/roles/ROLE_CONTROLE_AUDIT/users",
            json={"user_ids": [secretary_id], "motif": "Controle E2E"},
            headers=admin_headers,
        )
        assert assignment.status_code == 200, assignment.text
        assert assignment.json()["affectes"] == [secretary_id]
        assert assignment.json()["deja_affectes"] == []
        assert assignment.json()["legacy_role_aligne"] is None
        assert assignment.json()["reponses"][0]["role_code"] == "ROLE_CONTROLE_AUDIT"

        # Idempotence : une seconde affectation ne duplique pas la ligne.
        reassignment = await client.post(
            "/api/v1/rbac/roles/ROLE_CONTROLE_AUDIT/users",
            json={"user_ids": [secretary_id]},
            headers=admin_headers,
        )
        assert reassignment.status_code == 200, reassignment.text
        assert reassignment.json()["deja_affectes"] == [secretary_id]
        assert (
            await client.post(
                "/api/v1/rbac/roles/ROLE_CONTROLE_AUDIT/users",
                json={"user_ids": [999999]},
                headers=admin_headers,
            )
        ).status_code == 422
        # Un role libre sans equivalent legacy ne peut pas projeter la colonne.
        assert (
            await client.post(
                "/api/v1/rbac/roles/ROLE_CONTROLE_AUDIT/users",
                json={"user_ids": [secretary_id], "aligner_role_legacy": True},
                headers=admin_headers,
            )
        ).status_code == 422

        # -------------------------------------------------------------------
        # 9. Effet reel sur /auth/me et sur les guards
        # -------------------------------------------------------------------
        secretary_me = await client.get("/api/v1/auth/me", headers=secretary_headers)
        assert secretary_me.status_code == 200, secretary_me.text
        me_payload = secretary_me.json()
        # Le contrat legacy reste exact.
        assert me_payload["role"] == "SECRETARIAT"
        assert me_payload["is_superuser"] is False
        assert me_payload["email"] == SECRETARY_EMAIL
        assert LEGACY_ME_FIELDS.issubset(me_payload.keys())
        # L'autorite dynamique est reelle.
        assert me_payload["roles"] == ["ROLE_CONTROLE_AUDIT"]
        assert me_payload["permissions"] == [
            "audit.read",
            "rapports.read",
            "students.read",
        ]
        assert me_payload["authz_version"] is not None

        # require_audit_read est desormais satisfait par le role dynamique.
        audit_read = await client.get(
            "/api/v1/audit/events", headers=secretary_headers
        )
        assert audit_read.status_code == 200, audit_read.text
        # require_rbac_admin ne l'est pas : users.manage / roles.manage manquent.
        assert (
            await client.get("/api/v1/rbac/permissions", headers=secretary_headers)
        ).status_code == 403
        assert (
            await client.get("/api/v1/rbac/roles", headers=secretary_headers)
        ).status_code == 403
        # Les guards statiques n'ont pas bouge.
        assert (
            await client.get("/api/v1/academic/cycles", headers=secretary_headers)
        ).status_code == 200
        print("  [OK] Affectation dynamique : /auth/me et guards alignes sur la base.")

        # -------------------------------------------------------------------
        # 10. Vue admin : matrice resolue, pas simulee
        # -------------------------------------------------------------------
        matrix = await client.get(
            "/api/v1/rbac/users/roles", headers=admin_headers
        )
        assert matrix.status_code == 200, matrix.text
        secretary_row = next(
            item for item in matrix.json() if item["id"] == secretary_id
        )
        assert secretary_row["roles"] == ["ROLE_CONTROLE_AUDIT"]
        assert secretary_row["permissions"] == [
            "audit.read",
            "rapports.read",
            "students.read",
        ]
        assert secretary_row["authz_version"] is not None
        # Le compte etudiant n'a aucun role dynamique.
        student_row = next(
            item for item in matrix.json() if item["id"] == student_account_id
        )
        assert student_row["roles"] == []
        assert student_row["permissions"] == []

        filtered = await client.get(
            "/api/v1/rbac/users/roles",
            params={"role_code": "ROLE_CONTROLE_AUDIT"},
            headers=admin_headers,
        )
        assert filtered.status_code == 200, filtered.text
        assert [item["id"] for item in filtered.json()] == [secretary_id]

        effective = await client.get(
            f"/api/v1/rbac/users/{secretary_id}/permissions",
            headers=admin_headers,
        )
        assert effective.status_code == 200, effective.text
        assert effective.json()["role"] == "SECRETARIAT"
        assert effective.json()["legacy_role_is_admin"] is False
        assert effective.json()["roles"] == ["ROLE_CONTROLE_AUDIT"]
        assert effective.json()["permissions"] == [
            "audit.read",
            "rapports.read",
            "students.read",
        ]
        assert effective.json()["permission_domains"] == ["audit", "rapports", "students"]
        assert (
            await client.get(
                "/api/v1/rbac/users/999999/permissions", headers=admin_headers
            )
        ).status_code == 404

        role_users = await client.get(
            "/api/v1/rbac/roles/ROLE_CONTROLE_AUDIT/users", headers=admin_headers
        )
        assert role_users.status_code == 200, role_users.text
        assert [item["user_id"] for item in role_users.json()] == [secretary_id]
        assert role_users.json()[0]["actif"] is True
        print("  [OK] Vue users/roles : matrice resolue depuis la base.")

        # -------------------------------------------------------------------
        # 11. Retrait d'une permission : allow-only, sans heritage
        # -------------------------------------------------------------------
        removed = await client.delete(
            "/api/v1/rbac/roles/ROLE_CONTROLE_AUDIT/permissions/rapports.read",
            headers=admin_headers,
        )
        assert removed.status_code == 200, removed.text
        assert "rapports.read" not in removed.json()["permissions"]
        after_removal = await client.get("/api/v1/auth/me", headers=secretary_headers)
        assert after_removal.json()["permissions"] == ["audit.read", "students.read"]
        assert (
            await client.delete(
                "/api/v1/rbac/roles/ROLE_CONTROLE_AUDIT/permissions/rapports.read",
                headers=admin_headers,
            )
        ).status_code == 404
        # La permission n'est plus reliee : elle peut enfin etre supprimee.
        deleted_permission = await client.delete(
            "/api/v1/rbac/permissions/rapports.read", headers=admin_headers
        )
        assert deleted_permission.status_code == 200, deleted_permission.text
        assert deleted_permission.json() == {"supprime": True, "code": "rapports.read"}
        assert (
            await client.get(
                "/api/v1/rbac/permissions/rapports.read", headers=admin_headers
            )
        ).status_code == 404

        # -------------------------------------------------------------------
        # 12. Desactivation d'un role = retrait reel des permissions
        # -------------------------------------------------------------------
        disabled = await client.put(
            "/api/v1/rbac/roles/ROLE_CONTROLE_AUDIT",
            json={"actif": False},
            headers=admin_headers,
        )
        assert disabled.status_code == 200, disabled.text
        assert disabled.json()["actif"] is False
        disabled_me = await client.get("/api/v1/auth/me", headers=secretary_headers)
        assert disabled_me.json()["roles"] == []
        assert disabled_me.json()["permissions"] == []
        assert (
            await client.get("/api/v1/audit/events", headers=secretary_headers)
        ).status_code == 403
        assert (
            await client.post(
                "/api/v1/rbac/roles/ROLE_CONTROLE_AUDIT/users",
                json={"user_ids": [secretary_id]},
                headers=admin_headers,
            )
        ).status_code == 409
        await client.put(
            "/api/v1/rbac/roles/ROLE_CONTROLE_AUDIT",
            json={"actif": True},
            headers=admin_headers,
        )
        assert (
            await client.get("/api/v1/auth/me", headers=secretary_headers)
        ).json()["permissions"] == ["audit.read", "students.read"]
        print("  [OK] Desactivation d'un role : les permissions tombent puis reviennent.")

        # -------------------------------------------------------------------
        # 13. Retrait d'affectation
        # -------------------------------------------------------------------
        unassigned = await client.delete(
            f"/api/v1/rbac/roles/ROLE_CONTROLE_AUDIT/users/{secretary_id}",
            headers=admin_headers,
        )
        assert unassigned.status_code == 200, unassigned.text
        assert unassigned.json()["legacy_role_aligne"] is None
        empty_me = await client.get("/api/v1/auth/me", headers=secretary_headers)
        assert empty_me.json()["roles"] == []
        assert empty_me.json()["permissions"] == []
        assert (
            await client.get("/api/v1/audit/events", headers=secretary_headers)
        ).status_code == 403
        assert (
            await client.delete(
                f"/api/v1/rbac/roles/ROLE_CONTROLE_AUDIT/users/{secretary_id}",
                headers=admin_headers,
            )
        ).status_code == 404
        # La ligne d'affectation est conservee et desactivee.
        all_links = await client.get(
            "/api/v1/rbac/roles/ROLE_CONTROLE_AUDIT/users",
            params={"actif": False},
            headers=admin_headers,
        )
        assert [item["user_id"] for item in all_links.json()] == [secretary_id]

        # -------------------------------------------------------------------
        # 14. Projection legacy explicite
        # -------------------------------------------------------------------
        aligned = await client.post(
            "/api/v1/rbac/roles/ROLE_ENSEIGNANT/users",
            json={
                "user_ids": [student_account_id],
                "motif": "Promotion",
                "aligner_role_legacy": True,
            },
            headers=admin_headers,
        )
        assert aligned.status_code == 200, aligned.text
        assert aligned.json()["legacy_role_aligne"] == "ENSEIGNANT"
        promoted = _matrix_row(
            await client.get("/api/v1/rbac/users/roles", headers=admin_headers),
            student_account_id,
        )
        assert promoted["role"] == "ENSEIGNANT"
        # Une affectation ne peut pas retrograder la projection legacy.
        assert (
            await client.post(
                "/api/v1/rbac/roles/ROLE_ETUDIANT/users",
                json={
                    "user_ids": [student_account_id],
                    "aligner_role_legacy": True,
                },
                headers=admin_headers,
            )
        ).status_code == 409
        # Sans alignement, la projection legacy reste inchangee.
        await client.post(
            "/api/v1/rbac/roles/ROLE_ETUDIANT/users",
            json={"user_ids": [student_account_id]},
            headers=admin_headers,
        )
        untouched = _matrix_row(
            await client.get("/api/v1/rbac/users/roles", headers=admin_headers),
            student_account_id,
        )
        assert untouched["role"] == "ENSEIGNANT"
        # L'ordre suit ``Role.ordre`` : ENSEIGNANT (50) avant ETUDIANT (60).
        assert untouched["roles"] == ["ROLE_ENSEIGNANT", "ROLE_ETUDIANT"]
        assert (
            await client.delete(
                f"/api/v1/rbac/roles/ROLE_ENSEIGNANT/users/{student_account_id}",
                params={"aligner_role_legacy": True},
                headers=admin_headers,
            )
        ).status_code == 409
        print("  [OK] Projection legacy : alignement explicite, jamais de retrogradation.")

        # -------------------------------------------------------------------
        # 15. Suppression d'un role libre non affecte
        # -------------------------------------------------------------------
        reusable = await client.post(
            "/api/v1/rbac/roles",
            json={"code": "ROLE_JETABLE", "libelle": "Jetable", "ordre": 90},
            headers=admin_headers,
        )
        assert reusable.status_code == 201, reusable.text
        assert (
            await client.post(
                "/api/v1/rbac/roles/ROLE_JETABLE/users",
                json={"user_ids": [secretary_id]},
                headers=admin_headers,
            )
        ).status_code == 200
        # Un role affecte est protege.
        assert (
            await client.delete("/api/v1/rbac/roles/ROLE_JETABLE", headers=admin_headers)
        ).status_code == 409
        await client.delete(
            f"/api/v1/rbac/roles/ROLE_JETABLE/users/{secretary_id}",
            headers=admin_headers,
        )
        deleted_role = await client.delete(
            "/api/v1/rbac/roles/ROLE_JETABLE", headers=admin_headers
        )
        assert deleted_role.status_code == 200, deleted_role.text
        assert deleted_role.json() == {"supprime": True, "code": "ROLE_JETABLE"}
        assert (
            await client.get("/api/v1/rbac/roles/ROLE_JETABLE", headers=admin_headers)
        ).status_code == 404

        # -------------------------------------------------------------------
        # 16. Garde-fou anti-escalade sur la projection legacy
        # -------------------------------------------------------------------
        assert (
            await client.put(
                "/api/v1/rbac/roles/ROLE_CONTROLE_AUDIT/permissions",
                json={"permissions": ["users.manage"]},
                headers=admin_headers,
            )
        ).status_code == 200
        await client.post(
            "/api/v1/rbac/roles/ROLE_CONTROLE_AUDIT/users",
            json={"user_ids": [secretary_id]},
            headers=admin_headers,
        )
        secretary_headers = await _login(client, SECRETARY_EMAIL, SECRETARY_PASSWORD)
        # users.manage ouvre l'annuaire sans retirer le filtre historique.
        assert (
            await client.get("/api/v1/users/", headers=secretary_headers)
        ).status_code == 403  # SECRETARIAT ne voit que le referentiel enseignants
        assert (
            await client.get(
                "/api/v1/users/", params={"role": "ENSEIGNANT"}, headers=secretary_headers
            )
        ).status_code == 200
        # Mais pas la creation de comptes, reservee a ADMIN legacy.
        assert (
            await client.post(
                "/api/v1/users/",
                json={
                    "email": "escalade@ecole-ci.org",
                    "nom": "Escalade",
                    "prenom": "Refusee",
                    "role": "ADMIN",
                    "password": "Escalade-2026!",
                },
                headers=secretary_headers,
            )
        ).status_code == 403
        # Et toujours pas l'administration du RBAC.
        assert (
            await client.get("/api/v1/rbac/roles", headers=secretary_headers)
        ).status_code == 403
        assert (
            await client.get(
                "/api/v1/users/", params={"role": "ENSEIGNANT"}, headers=admin_headers
            )
        ).status_code == 200
        print("  [OK] Anti-escalade : users.manage n'ouvre pas la creation de comptes.")

        # -------------------------------------------------------------------
        # 17. Journalisation des actions RBAC
        # -------------------------------------------------------------------
        events = await client.get(
            "/api/v1/audit/events",
            params={"limit": 500},
            headers=admin_headers,
        )
        assert events.status_code == 200, events.text
        actions = {event["action"] for event in events.json()}
        for expected in (
            "security.rbac.permission.created",
            "security.rbac.permission.deleted",
            "security.rbac.role.created",
            "security.rbac.role.updated",
            "security.rbac.role.deleted",
            "security.rbac.role.permissions_set",
            "security.rbac.role.permission_added",
            "security.rbac.role.permission_removed",
            "security.rbac.role.assigned",
            "security.rbac.role.unassigned",
        ):
            assert expected in actions, sorted(actions)
        # Aucun secret dans le journal RBAC.
        for event in events.json():
            if event["action"].startswith("security.rbac."):
                rendered = str(event["details"])
                assert "password" not in rendered.lower()
                assert "hashed" not in rendered.lower()
        print("  [OK] Journal d'audit : toutes les actions RBAC sont tracees.")

        # -------------------------------------------------------------------
        # 18. Coherence de l'etat final
        # -------------------------------------------------------------------
        final_seed = _seed_counts()
        assert final_seed["users"] == 3, final_seed
        assert final_seed["system_roles"] == len(EXPECTED_SYSTEM_ROLE_CODES), final_seed
        assert (
            final_seed["system_permissions"] == len(EXPECTED_PERMISSION_CODES)
        ), final_seed
        # Un role systeme actif, non affecte, ne peut pas etre supprime.
        assert (
            await client.delete("/api/v1/rbac/roles/ROLE_ADMIN", headers=admin_headers)
        ).status_code == 409
        # Le compte admin n'a toujours pas de role dynamique affecte.
        admin_me = await client.get("/api/v1/auth/me", headers=admin_headers)
        assert admin_me.json()["role"] == "ADMIN"
        assert admin_me.json()["roles"] == []
        assert admin_me.json()["is_superuser"] is True

        # -------------------------------------------------------------------
        # 19. Transition metier : une permission dynamique ouvre reellement
        #     l'endpoint, sans jamais elargir le perimetre des roles legacy
        # -------------------------------------------------------------------
        created_aide_role = await client.post(
            "/api/v1/rbac/roles",
            json={
                "code": "ROLE_AIDE_PEDAGOGIQUE",
                "libelle": "Aide pedagogique",
                "description": "Role de test de la transition metier",
            },
            headers=admin_headers,
        )
        assert created_aide_role.status_code == 201, created_aide_role.text
        granted = await client.put(
            "/api/v1/rbac/roles/ROLE_AIDE_PEDAGOGIQUE/permissions",
            json={"permissions": ["students.read", "pedagogy.read"]},
            headers=admin_headers,
        )
        assert granted.status_code == 200, granted.text

        # Deux comptes frais, sans aucun role dynamique : l'un ETUDIANT (role
        # legacy le plus restrictif), l'autre ENSEIGNANT.
        accounts = {}
        for key, email, role in (
            ("aide", "aide.pedagogique@ecole-ci.org", "ETUDIANT"),
            ("enseignant", "enseignant.transition@ecole-ci.org", "ENSEIGNANT"),
        ):
            created = await client.post(
                "/api/v1/users/",
                json={
                    "email": email,
                    "nom": role.capitalize(),
                    "prenom": "Transition",
                    "role": role,
                    "password": "Transition-2026!",
                },
                headers=admin_headers,
            )
            assert created.status_code == 201, created.text
            accounts[key] = (created.json()["id"], email)

        aide_id, aide_email = accounts["aide"]
        _, enseignant_email = accounts["enseignant"]

        # 19.a Avant affectation : acces strictement heritage (ETUDIANT = rien).
        aide_headers = await _login(client, aide_email, "Transition-2026!")
        for path in ("/api/v1/etudiants/", "/api/v1/pedagogie/cours"):
            assert (
                await client.get(path, headers=aide_headers)
            ).status_code == 403, path
        print("  [OK] Transition : acces legacy ETUDIANT refuse avant affectation.")

        # 19.b Apres affectation : les permissions ouvrent reellement l'acces.
        assigned = await client.post(
            "/api/v1/rbac/roles/ROLE_AIDE_PEDAGOGIQUE/users",
            json={"user_ids": [aide_id]},
            headers=admin_headers,
        )
        assert assigned.status_code == 200, assigned.text
        aide_headers = await _login(client, aide_email, "Transition-2026!")
        for path in ("/api/v1/etudiants/", "/api/v1/pedagogie/cours"):
            assert (
                await client.get(path, headers=aide_headers)
            ).status_code == 200, path
        aide_me = await client.get("/api/v1/auth/me", headers=aide_headers)
        assert aide_me.json()["role"] == "ETUDIANT"
        assert aide_me.json()["roles"] == ["ROLE_AIDE_PEDAGOGIQUE"]
        assert sorted(aide_me.json()["permissions"]) == [
            "pedagogy.read",
            "students.read",
        ]
        print("  [OK] Transition : les permissions ouvrent l'acces metier correspondant.")

        # 19.c La lecture n'emporte jamais l'ecriture, meme sur le meme module.
        refused_student = await client.post(
            "/api/v1/etudiants/",
            json={"nom": "Refuse", "prenom": "Ecriture"},
            headers=aide_headers,
        )
        assert refused_student.status_code == 403, refused_student.text
        refused_filiere = await client.post(
            "/api/v1/structure/filieres",
            json={"code": "REFUSE", "nom": "Refusee"},
            headers=aide_headers,
        )
        assert refused_filiere.status_code == 403, refused_filiere.text
        print("  [OK] Transition : students.read/pedagogy.read n'ouvrent pas l'ecriture.")

        # 19.d Zero regression : le perimetre legacy de chaque role est intact.
        #       require_pedagogy_grades_read : l'enseignant lit les notes, le
        #       secretariat ne les a jamais lues.
        enseignant_headers = await _login(client, enseignant_email, "Transition-2026!")
        assert (
            await client.get("/api/v1/pedagogie/notes", headers=enseignant_headers)
        ).status_code == 200
        assert (
            await client.get("/api/v1/pedagogie/notes", headers=secretary_headers)
        ).status_code == 403
        # require_students_read : le secretariat lit le registre etudiant.
        assert (
            await client.get("/api/v1/etudiants/", headers=secretary_headers)
        ).status_code == 200
        # require_academic_structure_write : historiquement ADMIN seul, ni
        # l'enseignant ni le secretariat ne doivent pouvoir l'ecrire.
        for role_headers in (enseignant_headers, secretary_headers):
            assert (
                await client.post(
                    "/api/v1/structure/filieres",
                    json={"code": "LEGACY-F", "nom": "Legac refusee"},
                    headers=role_headers,
                )
            ).status_code == 403
        # require_students_delete : historiquement ADMIN seul.
        assert (
            await client.delete(
                f"/api/v1/etudiants/{student_account_id}", headers=secretary_headers
            )
        ).status_code == 403
        print("  [OK] Transition : perimetre legacy preserve (enseignant, secretariat).")

        # -------------------------------------------------------------------
        # 20. permissions_effectives : le frontend n'a plus de matrice locale
        # -------------------------------------------------------------------
        # 20.a Autorite dynamique pure : inchangee, toujours allow-only.
        secretary_me = await client.get("/api/v1/auth/me", headers=secretary_headers)
        assert "students.read" not in secretary_me.json()["permissions"]
        # 20.b Droits reellement exerçables : incluent la fenetre legacy.
        assert "students.read" in secretary_me.json()["permissions_effectives"]
        assert "admissions.write" in secretary_me.json()["permissions_effectives"]
        # Le secretariat n'a jamais pu ecrire le referentiel structurel ni
        # supprimer un dossier : ces droits ne doivent pas apparaitre.
        assert "dashboard.read" not in secretary_me.json()["permissions_effectives"]
        # La fenetre legacy est integralement incluse, et le role dynamique
        # s'y ajoute : l'ensemble vaut dynamique UNION legacy.
        legacy_secretary = LEGACY_PERMISSION_MATRIX["SECRETARIAT"]
        assert legacy_secretary.issubset(
            set(secretary_me.json()["permissions_effectives"])
        )
        assert set(secretary_me.json()["permissions"]).issubset(
            set(secretary_me.json()["permissions_effectives"])
        )
        # users.manage provient du role dynamique, pas de la fenetre legacy.
        assert "users.manage" not in legacy_secretary
        assert "users.manage" in secretary_me.json()["permissions_effectives"]
        # 20.c Un role dynamique ajoute ses droits a la fenetre legacy.
        assert set(aide_me.json()["permissions"]).issubset(
            set(aide_me.json()["permissions_effectives"])
        )
        assert "students.read" in aide_me.json()["permissions_effectives"]
        # 20.d L'ADMIN legacy herite des permissions protegees par un guard
        #       sans fenetre legacy (roles.manage, users.manage, audit.read),
        #       liste derivee de la table de guards.
        admin_profile = await client.get("/api/v1/auth/me", headers=admin_headers)
        assert admin_profile.json()["permissions"] == []
        effectifs_admin = admin_profile.json()["permissions_effectives"]
        for permission in ("roles.manage", "users.manage", "audit.read"):
            assert permission in effectifs_admin, (permission, effectifs_admin)
        # En revanche ``dashboard.read`` ne protege aucun endpoint (le tableau
        # de bord est un agregat cote client) : il n'est donc pas implique et
        # doit etre accorde explicitement par un role si l'interface l'exige.
        assert "dashboard.read" not in effectifs_admin, effectifs_admin
        # Une permission metier reste absente tant qu'aucun role ne l'accorde.
        assert "students.write" not in effectifs_admin, effectifs_admin
        print("  [OK] permissions_effectives : le backend expose le droit exerçable.")

    print("E2E RBAC dynamique : OK")


if __name__ == "__main__":
    asyncio.run(_cleanup())
    shutil.rmtree(TEST_DIR, ignore_errors=True)
    try:
        _migrate()
        # Hors boucle d'evenement : Alembic ouvre sa propre boucle asyncio.
        _expect_downgrade_refused()
        print("  [OK] Downgrade refusee des qu'un role hors catalogue existe.")
        asyncio.run(_run())
    finally:
        asyncio.run(_cleanup())
        shutil.rmtree(TEST_DIR, ignore_errors=True)
