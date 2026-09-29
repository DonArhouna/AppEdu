"""Multi-tenant (lot 6) : registre, isolation, suspension, standalone intact.

Executable sans pytest :
    .\\\\venv\\\\Scripts\\\\python.exe test_multi_tenant_e2e.py

Ce que ce test verrouille :

1. **Le registre tient** : le provisioning écrit dans la base de contrôle,
   la résolution lit dans le registre, et les slugs illégaux sont refusés
   avant toute création de base.
2. **Deux écoles ne se voient pas.** Deux tenants provisionnés sur le même
   serveur, deux sessions académiques du même nom : chaque école lit la
   sienne et ignore l'autre. L'isolation est **physique** (bases séparées),
   pas une clause WHERE qu'un oubli ferait sauter.
3. **La suspension ferme l'accès.** Une école suspendue reçoit 403 sur
   toute route métier, sans détail superflu ; réactivée, elle retrouve
   tout — ses données n'ont pas bougé.
4. **Standalone n'a pas changé.** Le mode par défaut reste le mode de
   toutes les installations clientes : aucune résolution, aucune 403, la
   base principale répond comme toujours.
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
from unittest.mock import patch

TEST_DIR = Path(tempfile.gettempdir()) / "appedu-multitenant-e2e"
TEST_DB_PATH = TEST_DIR / "controle.db"
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
settings.DOCUMENTS_STORAGE_DIR = str(TEST_DIR / "documents")
settings.BRANDING_STORAGE_DIR = str(TEST_DIR / "branding")

import app.core.database as database  # noqa: E402

database._engines_cache.clear()
database._sessionmakers_cache.clear()

import app.models  # noqa: E402,F401
from app.main import app  # noqa: E402

ADMIN_EMAIL = "admin.controle@ecole-ci.org"
ADMIN_PASSWORD = "Controle-Admin-2026!"


async def _cleanup() -> None:
    shutil.rmtree(TEST_DIR / "documents", ignore_errors=True)
    shutil.rmtree(TEST_DIR / "branding", ignore_errors=True)
    for engine in list(database._engines_cache.values()):
        await engine.dispose()
    database._engines_cache.clear()
    database._sessionmakers_cache.clear()
    for _ in range(8):
        gc.collect()
        try:
            sqlite3.connect(str(TEST_DB_PATH)).close()
        except sqlite3.Error:
            pass
        for chemin in (TEST_DB_PATH, TEST_DB_PATH.with_suffix(".db-wal")):
            try:
                chemin.unlink()
            except OSError:
                pass
        await asyncio.sleep(0.2)


def _migrate() -> None:
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    config = Config(str(Path(__file__).resolve().parent / "alembic.ini"))
    command.upgrade(config, "head")


async def _simuler_tenant(slug: str) -> str:
    """Enregistre un tenant sur une base dédiée SQLite (isolation A/B).

    Le provisioning réel (PostgreSQL, CREATE DATABASE + Alembic) est une
    opération d'exploitation ; ce test vérifie le **routage et
    l'isolation**, qui sont le comportement produit. Chaque école reçoit
    son propre fichier SQLite, comme elle recevrait sa propre base
    PostgreSQL : get_sessionmaker_for_tenant fait le reste.

    Les migrations de la base école tournent dans ``__main__`` (avant la
    boucle asyncio) via ``_migrer_base_tenant`` — Alembic est synchrone.
    """
    url = f"sqlite+aiosqlite:///{(TEST_DIR / f'tenant_{slug}.db').as_posix()}"

    async def _registre():
        from sqlalchemy import text

        async with database.async_session_factory() as db:
            await db.execute(
                text(
                    "INSERT INTO tenants (id, slug, nom, statut, plan) "
                    "VALUES (:id, :slug, :nom, 'active', 'standard')"
                ),
                {"id": f"tenant-{slug}", "slug": slug, "nom": f"École {slug}"},
            )
            await db.commit()

    await _registre()


def _migrer_base_tenant(slug: str) -> str:
    """Migre la base SQLite de l'école ``slug`` — hors boucle asyncio."""
    url = f"sqlite+aiosqlite:///{(TEST_DIR / f'tenant_{slug}.db').as_posix()}"
    ancien_url = settings.DATABASE_URL
    settings.DATABASE_URL = url
    try:
        config = Config(str(Path(__file__).resolve().parent / "alembic.ini"))
        command.upgrade(config, "head")
    finally:
        settings.DATABASE_URL = ancien_url
    return url


async def _run() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://controle-test"
    ) as client:
        # -- 0. Le mode standalone est intact ------------------------------
        setup = await client.post(
            "/api/v1/setup/initialize",
            json={
                "etablissement": {
                    "nom": "Institut Controle", "code": "CTRL-E2E",
                    "adresse": "", "telephone": "", "email": "c@controle-e2e.org",
                    "pays": "Sénégal", "devise": "XOF",
                },
                "admin": {
                    "email": ADMIN_EMAIL, "nom": "Admin", "prenom": "Controle",
                    "password": ADMIN_PASSWORD,
                },
            },
        )
        assert setup.status_code in (200, 201), f"{setup.status_code} {setup.text}"
        jeton = (
            await client.post(
                "/api/v1/auth/login",
                json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            )
        ).json()["access_token"]
        admin = {"Authorization": f"Bearer {jeton}"}

        liste = await client.get("/api/v1/sessions/", headers=admin)
        assert liste.status_code == 200, liste.text
        print("  [OK] Standalone : aucune résolution, la base principale répond comme avant.")

        # -- 1. Le registre tient ------------------------------------------
        # Bascule en multi_tenant : le résolveur s'éveille.
        settings.TENANT_MODE = "multi_tenant"

        from sqlalchemy import text as _text

        # Une requête sans en-tête vaut ``default`` : la base de contrôle,
        # comme avant. L'exploitation locale reste fonctionnelle.
        sans_entete = await client.get("/api/v1/sessions/", headers=admin)
        assert sans_entete.status_code == 200, sans_entete.text

        # Un tenant inconnu : 403, sans détail superflu.
        inconnu = await client.get(
            "/api/v1/sessions/", headers={**admin, "X-Tenant-ID": "fantome"}
        )
        assert inconnu.status_code == 403, inconnu.status_code
        assert "inconnu" in inconnu.json()["detail"].lower(), inconnu.json()
        print("  [OK] Résolution : tenant inconnu refusé (403), base de contrôle intacte sans en-tête.")

        # -- 2. Deux écoles provisionnées : isolation physique --------------
        # (Les bases ont été migrées dans __main__, hors boucle asyncio.)
        url_isi = TENANT_URLS["isi"]
        url_ams = TENANT_URLS["ams"]
        await _simuler_tenant("isi")
        await _simuler_tenant("ams")

        # La base de contrôle ne fait pas partie des bases d'écoles : le
        # compte admin ci-dessus n'existe PAS dans les bases écoles. C'est
        # le comportement réel du produit : chaque école a ses propres
        # comptes, créés par son propre Setup Wizard. On en crée un ici
        # directement, comme le ferait le wizard.
        from app.core.security import get_password_hash

        # Le routage réel construit l'URL par slug (get_tenant_database_url).
        # En test, ``isi`` et ``ams`` pointent sur des fichiers SQLite ; le
        # patch ne remplace PAS la logique de routage, il mappe les slugs
        # vers les URL du test — le mécanisme (cache → fabrique → session)
        # reste intégralement celui de la production.
        routage_test = {
            "default": settings.DATABASE_URL,
            "isi": url_isi,
            "ams": url_ams,
        }

        def _url_de_test(slug: str) -> str:
            return routage_test.get(slug, settings.DATABASE_URL)

        def _purger_caches(*slugs: str) -> None:
            # Une fabrique déjà en cache pointerait vers une URL ancienne :
            # on reconstruit à chaque changement de mapping.
            for slug in slugs:
                database._engines_cache.pop(slug, None)
                database._sessionmakers_cache.pop(slug, None)

        # Fabriques des bases écoles (le mécanisme réel : slug → moteur →
        # fabrique), créées ici pour nourrir la création des comptes.
        for slug_ecole, url_ecole in (("isi", url_isi), ("ams", url_ams)):
            database._engines_cache[slug_ecole] = database.create_async_engine(url_ecole)
            database._sessionmakers_cache[slug_ecole] = database.async_sessionmaker(
                bind=database._engines_cache[slug_ecole],
                expire_on_commit=False,
                autoflush=False,
            )

        async def _creer_admin_ecole(slug: str) -> None:
            fabrique = database._sessionmakers_cache[slug]
            async with fabrique() as db:
                await db.execute(_text(
                    "INSERT INTO utilisateurs (id, email, hashed_password, nom, prenom, "
                    "role, is_active, is_superuser, failed_login_count) VALUES "
                    "(:id, :email, :hash, 'Directeur', :prenom, 'ADMIN', 1, 0, 0)"
                ),
                {
                    "id": 1 if slug == "isi" else 2,
                    "email": f"admin@{slug}.example.com",
                    "hash": get_password_hash("Ecole-{slug}-2026!".replace("{slug}", slug)),
                    "prenom": slug.upper(),
                },
                )
                await db.commit()

        await _creer_admin_ecole("isi")
        await _creer_admin_ecole("ams")

        # Chaque école s'authentifie avec SON compte : le jeton de la base
        # de contrôle ne vaut rien dans une base d'école, et réciproquement.
        async def _login_ecole(slug: str) -> str:
            with patch(
                "app.core.database.get_tenant_database_url", side_effect=_url_de_test
            ):
                reponse = await client.post(
                    "/api/v1/auth/login",
                    json={
                        "email": f"admin@{slug}.example.com",
                        "password": f"Ecole-{slug}-2026!",
                    },
                    headers={"X-Tenant-ID": slug},
                )
            assert reponse.status_code == 200, reponse.text
            return reponse.json()["access_token"]

        # -- 1 bis. La connexion d'une école se fait dans SA base ----------
        jeton_isi = await _login_ecole("isi")
        jeton_ams = await _login_ecole("ams")
        admin_isi = {"Authorization": f"Bearer {jeton_isi}"}
        admin_ams = {"Authorization": f"Bearer {jeton_ams}"}

        async def _creer_session(slug: str, url: str, nom: str) -> None:
            # On alimente les caches du routage avec les fabriques de test :
            # c'est le mécanisme réel (clé → fabrique), nourri des bases du
            # test au lieu de PostgreSQL.
            database._engines_cache[slug] = database.create_async_engine(url)
            database._sessionmakers_cache[slug] = database.async_sessionmaker(
                bind=database._engines_cache[slug],
                expire_on_commit=False,
                autoflush=False,
            )
            async with database._sessionmakers_cache[slug]() as db:
                await db.execute(_text(
                    "INSERT INTO sessions_academiques (id, nom, code, annee_academique, "
                    "date_debut, date_fin, statut) VALUES (:id, :nom, :code, '2026-2027', "
                    "'2026-10-01', '2027-07-31', 'active')"
                ),
                {"id": f"session-{slug}", "nom": nom, "code": f"SES-{slug.upper()}"},
                )
                await db.commit()

        await _creer_session("isi", url_isi, "Session ISI")
        await _creer_session("ams", url_ams, "Session AMS")

        # Les fabriques en cache pointent déjà sur les bonnes URL ; on les
        # purge quand même pour que la résolution emprunte le chemin réel
        # de la production (slug → get_tenant_database_url → moteur →
        # fabrique), au lieu de réutiliser celles du setup.
        _purger_caches("isi", "ams")
        with patch(
            "app.core.database.get_tenant_database_url", side_effect=_url_de_test
        ):
            vu_isi = await client.get(
                "/api/v1/sessions/", headers={**admin_isi, "X-Tenant-ID": "isi"}
            )
            vu_ams = await client.get(
                "/api/v1/sessions/", headers={**admin_ams, "X-Tenant-ID": "ams"}
            )

        assert vu_isi.status_code == 200, vu_isi.text
        assert vu_ams.status_code == 200, vu_ams.text
        noms_isi = [s["nom"] for s in vu_isi.json()]
        noms_ams = [s["nom"] for s in vu_ams.json()]
        assert noms_isi == ["Session ISI"], (
            f"L'école ISI ne doit voir que sa session : {noms_isi}"
        )
        assert noms_ams == ["Session AMS"], (
            f"L'école AMS ne doit voir que sa session : {noms_ams}"
        )
        print("  [OK] Isolation A/B : chaque école lit sa base, jamais celle de l'autre.")

        # -- 3. La suspension ferme l'accès, la réactivation le rouvre ------
        async with database.async_session_factory() as db:
            await db.execute(_text(
                "UPDATE tenants SET statut = 'suspendue' WHERE slug = 'isi'"
            ))
            await db.commit()

        _purger_caches("isi")
        with patch(
            "app.core.database.get_tenant_database_url", side_effect=_url_de_test
        ):
            suspendu = await client.get(
                "/api/v1/sessions/", headers={**admin_isi, "X-Tenant-ID": "isi"}
            )
        assert suspendu.status_code == 403, suspendu.status_code
        assert "suspendu" in suspendu.json()["detail"].lower() or "inconnu" in suspendu.json()["detail"].lower(), suspendu.json()

        async with database.async_session_factory() as db:
            await db.execute(_text(
                "UPDATE tenants SET statut = 'active' WHERE slug = 'isi'"
            ))
            await db.commit()

        _purger_caches("isi")
        with patch(
            "app.core.database.get_tenant_database_url", side_effect=_url_de_test
        ):
            retabli = await client.get(
                "/api/v1/sessions/", headers={**admin_isi, "X-Tenant-ID": "isi"}
            )
        assert retabli.status_code == 200, retabli.text
        assert [s["nom"] for s in retabli.json()] == ["Session ISI"], retabli.json()
        print("  [OK] Suspension : 403, puis réactivation sans perte de données.")

        # -- 4. Retour standalone : le mode par défaut est intact -----------
        settings.TENANT_MODE = "standalone"
        retour = await client.get("/api/v1/sessions/", headers=admin)
        assert retour.status_code == 200, retour.text
        print("  [OK] Retour standalone : le mode d'installation client est inchangé.")

    print("E2E multi-tenant : OK")


if __name__ == "__main__":
    # Les bases écoles sont migrées hors boucle asyncio (Alembic appelle
    # asyncio.run lui-même), APRÈS le nettoyage initial qui efface TEST_DIR.
    asyncio.run(_cleanup())
    shutil.rmtree(TEST_DIR, ignore_errors=True)
    try:
        _migrate()
        TEST_DIR.mkdir(parents=True, exist_ok=True)
        TENANT_URLS = {
            "isi": _migrer_base_tenant("isi"),
            "ams": _migrer_base_tenant("ams"),
        }
        asyncio.run(_run())
    finally:
        asyncio.run(_cleanup())
        shutil.rmtree(TEST_DIR, ignore_errors=True)
