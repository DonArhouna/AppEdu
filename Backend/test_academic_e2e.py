"""E2E ciblé du socle académique (SQLite isolé).

Ce scénario est volontairement exécutable sans pytest :
    .\\venv\\Scripts\\python.exe test_academic_e2e.py

Il ne touche pas à une base locale : la base est un fichier temporaire et il
n'y a aucun reset d'une instance existante.
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


TEST_DIR = Path(tempfile.gettempdir()) / "appedu-academic-e2e"
TEST_DB_PATH = TEST_DIR / "academic.db"
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
from app.main import app  # noqa: E402


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


def _migrate() -> None:
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    config = Config(str(Path(__file__).resolve().parent / "alembic.ini"))
    # Le cycle demandé est vérifié avant le parcours métier.
    command.upgrade(config, "0011_security_audit")
    command.upgrade(config, "head")
    command.downgrade(config, "0011_security_audit")
    command.upgrade(config, "head")


async def _run() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://academic-test"
    ) as client:
        setup = await client.post(
            "/api/v1/setup/initialize",
            json={
                "etablissement": {
                    "nom": "Etablissement Academique Test",
                    "code": "ACAD-E2E",
                    "email": "contact@ecole-ci.org",
                    "devise": "XOF",
                },
                "admin": {
                    "nom": "Admin",
                    "prenom": " Academique",
                    "email": "admin.academique@ecole-ci.org",
                    "password": "Academic-E2E-2026!",
                },
            },
        )
        assert setup.status_code == 201, setup.text
        headers = {"Authorization": f"Bearer {setup.json()['access_token']}"}

        # Le secrétariat doit consulter les référentiels pour les formulaires,
        # mais ne doit pas pouvoir écrire la structure académique.
        secretary_user = await client.post(
            "/api/v1/users/",
            json={
                "email": "secretariat.academique@ecole-ci.org",
                "nom": "Secretariat",
                "prenom": "Academique",
                "role": "SECRETARIAT",
                "password": "Academic-Secretariat-2026!",
            },
            headers=headers,
        )
        assert secretary_user.status_code == 201, secretary_user.text
        secretary_login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "secretariat.academique@ecole-ci.org",
                "password": "Academic-Secretariat-2026!",
            },
        )
        assert secretary_login.status_code == 200, secretary_login.text
        secretary_headers = {
            "Authorization": f"Bearer {secretary_login.json()['access_token']}"
        }
        assert (
            await client.get("/api/v1/academic/cycles", headers=secretary_headers)
        ).status_code == 200
        forbidden_write = await client.post(
            "/api/v1/academic/cycles",
            json={"code": "SECRET", "nom": "Interdit", "ordre": 9},
            headers=secretary_headers,
        )
        assert forbidden_write.status_code == 403

        session_response = await client.post(
            "/api/v1/sessions/",
            json={
                "nom": "Session academique E2E",
                "code": "ACAD-SES-E2E",
                "annee_academique": "2026-2027",
                "date_debut": "2026-09-01",
                "date_fin": "2027-07-31",
                "statut": "active",
            },
            headers=headers,
        )
        assert session_response.status_code == 201, session_response.text
        session_id = session_response.json()["id"]

        filiere_response = await client.post(
            "/api/v1/structure/filieres",
            json={
                "nom": "Filiere Academique E2E",
                "code": "ACAD-F",
                "diplome": "Licence",
                "duree": 3,
            },
            headers=headers,
        )
        assert filiere_response.status_code == 201, filiere_response.text
        filiere_id = filiere_response.json()["id"]

        # Aucune donnée académique n'est créée par le setup.
        assert (await client.get("/api/v1/academic/cycles", headers=headers)).json() == []

        first_load = await client.post(
            "/api/v1/academic/modele-lmd/charger", headers=headers
        )
        assert first_load.status_code == 200, first_load.text
        assert first_load.json()["cycles_crees"] == 2
        assert first_load.json()["niveaux_crees"] == 5
        second_load = await client.post(
            "/api/v1/academic/modele-lmd", headers=headers
        )
        assert second_load.status_code == 200, second_load.text
        assert second_load.json()["cycles_crees"] == 0
        assert second_load.json()["niveaux_crees"] == 0
        niveau_l1 = next(
            niveau
            for niveau in second_load.json()["niveaux"]
            if niveau["code"] == "L1"
        )

        classe_response = await client.post(
            "/api/v1/academic/classes",
            json={"filiere_id": filiere_id, "niveau_id": niveau_l1["id"]},
            headers=headers,
        )
        assert classe_response.status_code == 201, classe_response.text
        classe = classe_response.json()
        assert classe["filiere"]["id"] == filiere_id
        assert classe["niveau"]["cycle"]["id"] == niveau_l1["cycle_id"]
        duplicate_classe = await client.post(
            "/api/v1/academic/classes",
            json={"filiere_id": filiere_id, "niveau_id": niveau_l1["id"]},
            headers=headers,
        )
        assert duplicate_classe.status_code == 409

        etudiant_response = await client.post(
            "/api/v1/etudiants/",
            json={
                "nom": "Etudiant",
                "prenom": "Canonique",
                "statut": "Inscrit",
                "classe_id": classe["id"],
                "session_id": session_id,
            },
            headers=headers,
        )
        assert etudiant_response.status_code == 201, etudiant_response.text
        etudiant = etudiant_response.json()
        assert etudiant["classe_id"] == classe["id"]
        assert etudiant["filiere_id"] == filiere_id
        assert etudiant["niveau"] == "Licence 1"

        # L'inscription est créée une seule fois et l'appel répété l'actualise.
        re_inscription = await client.post(
            f"/api/v1/etudiants/{etudiant['id']}/inscrire",
            json={"classe_id": classe["id"], "session_id": session_id},
            headers=headers,
        )
        assert re_inscription.status_code == 200, re_inscription.text
        inscriptions = await client.get(
            "/api/v1/academic/inscriptions", headers=headers
        )
        assert inscriptions.status_code == 200, inscriptions.text
        assert len(inscriptions.json()) == 1
        duplicate_inscription = await client.post(
            "/api/v1/academic/inscriptions",
            json={
                "etudiant_id": etudiant["id"],
                "classe_id": classe["id"],
                "session_id": session_id,
            },
            headers=headers,
        )
        assert duplicate_inscription.status_code == 409

        # Un changement de classe pendant la même session ferme l'ancienne
        # ligne et en crée une nouvelle : l'historique n'est jamais réécrit.
        niveau_l2 = next(
            niveau
            for niveau in second_load.json()["niveaux"]
            if niveau["code"] == "L2"
        )
        classe_l2_response = await client.post(
            "/api/v1/academic/classes",
            json={"filiere_id": filiere_id, "niveau_id": niveau_l2["id"]},
            headers=headers,
        )
        assert classe_l2_response.status_code == 201, classe_l2_response.text
        classe_l2 = classe_l2_response.json()
        reassignment = await client.post(
            f"/api/v1/etudiants/{etudiant['id']}/inscrire",
            json={"classe_id": classe_l2["id"], "session_id": session_id},
            headers=headers,
        )
        assert reassignment.status_code == 200, reassignment.text
        inscriptions_after_reassignment = (
            await client.get("/api/v1/academic/inscriptions", headers=headers)
        ).json()
        assert len(inscriptions_after_reassignment) == 2
        assert all(
            not item["actif"]
            for item in inscriptions_after_reassignment
            if item["classe_id"] == classe["id"]
        )
        assert any(
            item["actif"]
            for item in inscriptions_after_reassignment
            if item["classe_id"] == classe_l2["id"]
        )

        # Une fiche legacy reste une fiche legacy : aucune inscription/backfill.
        legacy_response = await client.post(
            "/api/v1/etudiants/",
            json={
                "nom": "Etudiant",
                "prenom": "Legacy",
                "filiere": "Ancienne Filiere",
                "niveau": "Licence 1",
                "statut": "actif",
                "session_id": session_id,
            },
            headers=headers,
        )
        assert legacy_response.status_code == 201, legacy_response.text
        assert legacy_response.json()["classe_id"] is None
        assert legacy_response.json()["filiere"] == "Ancienne Filiere"
        assert len((await client.get("/api/v1/academic/inscriptions", headers=headers)).json()) == 2

        assert (
            await client.delete(
                f"/api/v1/academic/classes/{classe['id']}", headers=headers
            )
        ).status_code == 409
        assert (
            await client.delete(
                f"/api/v1/academic/cycles/{niveau_l1['cycle_id']}", headers=headers
            )
        ).status_code == 409

    print("E2E socle academique : OK")


if __name__ == "__main__":
    asyncio.run(_cleanup())
    shutil.rmtree(TEST_DIR, ignore_errors=True)
    try:
        _migrate()
        asyncio.run(_run())
    finally:
        asyncio.run(_cleanup())
        shutil.rmtree(TEST_DIR, ignore_errors=True)
