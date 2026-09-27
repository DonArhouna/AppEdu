"""E2E de l'export de la liste des etudiants (SQLite isole).

Executable sans pytest :
    .\\\\venv\\\\Scripts\\\\python.exe test_export_e2e.py

Ce qui est verrouille :

1. le classeur est relu par un **decodeur reel** (openpyxl), pas compare a une
   taille : un fichier corrompu peut peser exactement le bon nombre d'octets ;
2. les en-tetes sont ceux du registre humain (« Prénom »), pas ceux de la
   colonne en base ;
3. le filtre de classe restreint reellement, et l'export n'est **pas** pagine :
   un institut qui exporte sa promotion veut tous ses eleves ;
4. une classe sans etudiant produit un classeur **avec en-tetes et sans
   lignes** — un fichier vide sans en-tete n'est pas devinable ;
5. une classe inexistante est un **404**, pas un fichier vide : un classeur sans
   ligne se lirait « cette classe est vide » ;
6. le CSV porte un BOM UTF-8 et des point-virgules, sans quoi Excel francais
   affiche « Ma?le Dupont » ;
7. le nom de fichier nomme la promotion, et l'en-tete ``X-Export-Etudiants``
   donne le nombre de lignes : l'institut verifie d'un coup d'oeil.
"""

import asyncio
import gc
import io
import os
import shutil
import sqlite3
import tempfile
from datetime import date
from pathlib import Path

from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient

TEST_DIR = Path(tempfile.gettempdir()) / "appedu-export-e2e"
TEST_DB_PATH = TEST_DIR / "export.db"
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

ADMIN_EMAIL = "admin.export@ecole-ci.org"
ADMIN_PASSWORD = "Export-Admin-2026!"
DEVISE = "XOF"

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


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
    command.downgrade(config, "0018_relances_facturation")
    command.upgrade(config, "head")


def _lire_classeur(contenu: bytes):
    """Relit le classeur avec un decodeur reel, pas avec une comparaison d'octets."""

    from openpyxl import load_workbook

    return load_workbook(io.BytesIO(contenu), data_only=True)


async def _run() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://export-test"
    ) as client:
        setup = await client.post(
            "/api/v1/setup/initialize",
            json={
                "etablissement": {
                    "nom": "Institut Export E2E", "code": "EXP-E2E",
                    "adresse": "", "telephone": "", "email": "c@export-e2e.org",
                    "pays": "Sénégal", "devise": DEVISE,
                },
                "admin": {
                    "email": ADMIN_EMAIL, "nom": "Admin", "prenom": "Export",
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

        filiere = (
            await client.post(
                "/api/v1/structure/filieres",
                json={
                    "nom": "Genie Logiciel Export", "code": "GLE",
                    "duree": 3, "diplome": "Licence", "niveau": "L1",
                },
                headers=admin,
            )
        ).json()
        await client.post(
            "/api/v1/structure/finances/grilles-tarifaires",
            json={
                "filiere": filiere["nom"], "filiere_id": filiere["id"], "niveau": "L1",
                "droits_inscription": 100000, "scolarite_mensuelle": 75000,
                "nombre_mois": 8, "actif": True,
            },
            headers=admin,
        )
        session = (
            await client.post(
                "/api/v1/sessions/",
                json={
                    "nom": "Session Export", "code": "SES-EXP",
                    "annee_academique": "2026-2027",
                    "date_debut": "2026-10-01", "date_fin": "2027-07-31",
                    "statut": "active",
                },
                headers=admin,
            )
        ).json()
        cycle = (
            await client.post(
                "/api/v1/academic/cycles",
                json={"nom": "Licence", "code": "LIC"}, headers=admin,
            )
        ).json()

        async def _classe(code: str, nom: str, niveau_code: str) -> dict:
            niveau = (
                await client.post(
                    "/api/v1/academic/niveaux",
                    json={
                        "code": niveau_code, "nom": f"Niveau {niveau_code}",
                        "cycle_id": cycle["id"],
                    },
                    headers=admin,
                )
            ).json()
            return (
                await client.post(
                    "/api/v1/academic/classes",
                    json={
                        "code": code, "nom": nom,
                        "filiere_id": filiere["id"], "niveau_id": niveau["id"],
                    },
                    headers=admin,
                )
            ).json()

        classe_peuplee = await _classe("EXP-A", "Genie Logiciel A", "L1A")
        classe_vide = await _classe("EXP-B", "Genie Logiciel B", "L1B")

        async def _etudiant(prenom: str, nom: str, classe: dict) -> None:
            cree = await client.post(
                "/api/v1/etudiants/",
                json={
                    "nom": nom, "prenom": prenom, "sexe": "M",
                    "date_naissance": "2004-01-15",
                    "filiere": filiere["nom"], "niveau": "L1A",
                    "classe_id": classe["id"], "session_id": session["id"],
                    "telephone": "+22177000000",
                },
                headers=admin,
            )
            assert cree.status_code in (200, 201), cree.text

        # Volontairement desordre a l'insertion : l'export doit trier.
        await _etudiant("Zoe", "Alpha", classe_peuplee)
        await _etudiant("Amine", "Zeta", classe_peuplee)
        await _etudiant("Ibra", "Beta", classe_peuplee)
        print("  [OK] Mise en place : une classe peuplee, une classe vide.")

        # ------------------------------------------------------------------
        # 1. Classeur relu par un decodeur reel
        # ------------------------------------------------------------------
        rep = await client.get(
            "/api/v1/etudiants/export", params={"classe_id": classe_peuplee["id"]},
            headers=admin,
        )
        assert rep.status_code == 200, rep.text
        assert rep.headers["content-type"] == XLSX, rep.headers["content-type"]
        assert "attachment" in rep.headers["content-disposition"], rep.headers
        assert "Genie-Logiciel-A" in rep.headers["content-disposition"], (
            "Le nom de fichier ne nomme pas la promotion : l'institut ne peut "
            f"plus savoir ce qu'il a exporte. {rep.headers['content-disposition']}"
        )
        assert rep.headers.get("X-Export-Etudiants") == "3", rep.headers

        classeur = _lire_classeur(rep.content)
        feuille = classeur.active
        lignes = list(feuille.iter_rows(values_only=True))
        entetes = list(lignes[0])
        assert "Prénom" in entetes and "Nom" in entetes, entetes
        assert "Matricule" in entetes, entetes
        # Les en-tetes sont ceux du registre, pas « prenom ».
        assert "prenom" not in entetes, entetes

        corps = lignes[1:]
        assert len(corps) == 3, f"3 etudiants attendus, {len(corps)} exportes"
        noms = [(ligne[1], ligne[0]) for ligne in corps]
        assert noms == [("Alpha", "Zoe"), ("Beta", "Ibra"), ("Zeta", "Amine")], (
            f"L'export n'est pas trie par nom puis prenom : {noms}"
        )
        matricules = [ligne[2] for ligne in corps]
        assert all(str(m).strip() for m in matricules), f"Matricule vide : {matricules}"
        # La date est formatee pour un humain, pas en ISO brut.
        naissance = corps[0][entetes.index("Date de naissance")]
        assert isinstance(naissance, str) and naissance.count("/") == 2, naissance
        print("  [OK] Classeur valide, en-tetes humains, lignes triees.")

        # ------------------------------------------------------------------
        # 2. Le filtre de classe restreint reellement
        # ------------------------------------------------------------------
        tous = await client.get("/api/v1/etudiants/export", headers=admin)
        assert tous.status_code == 200, tous.text
        tous_lignes = list(_lire_classeur(tous.content).active.iter_rows(values_only=True))
        assert tous_lignes[0][0] == "Prénom", tous_lignes[0]
        # 3 etudiants, tous de la meme classe : l'export global les contient tous.
        assert tous.headers.get("X-Export-Etudiants") == "3", tous.headers
        assert "sans-nom" not in tous.headers["content-disposition"], (
            tous.headers["content-disposition"]
        )
        print("  [OK] Export global et export par classe concordent.")

        # ------------------------------------------------------------------
        # 3. Une classe vide donne un classeur lisible, pas un fichier casse
        # ------------------------------------------------------------------
        vide = await client.get(
            "/api/v1/etudiants/export", params={"classe_id": classe_vide["id"]},
            headers=admin,
        )
        assert vide.status_code == 200, vide.text
        lignes_vides = list(_lire_classeur(vide.content).active.iter_rows(values_only=True))
        assert len(lignes_vides) == 1, (
            f"Le classeur d'une classe vide doit avoir les en-tetes et rien "
            f"d'autre, il a {len(lignes_vides)} ligne(s)."
        )
        assert lignes_vides[0][0] == "Prénom", lignes_vides[0]
        assert vide.headers.get("X-Export-Etudiants") == "0", vide.headers
        print("  [OK] Classe vide : classeur avec en-tetes, zero ligne.")

        # ------------------------------------------------------------------
        # 4. Une classe inexistante est un 404 explicite
        # ------------------------------------------------------------------
        introuvable = await client.get(
            "/api/v1/etudiants/export",
            params={"classe_id": "classe-qui-nexiste-pas"},
            headers=admin,
        )
        assert introuvable.status_code == 404, introuvable.text
        assert introuvable.json()["detail"], introuvable.text
        print("  [OK] Classe inexistante : 404 dit pourquoi, pas un fichier vide.")

        # ------------------------------------------------------------------
        # 5. Le CSV : BOM et point-virgules
        # ------------------------------------------------------------------
        csv_rep = await client.get(
            "/api/v1/etudiants/export",
            params={"classe_id": classe_peuplee["id"], "format": "csv"},
            headers=admin,
        )
        assert csv_rep.status_code == 200, csv_rep.text
        assert csv_rep.headers["content-type"].startswith("text/csv"), csv_rep.headers
        assert csv_rep.content.startswith(b"\xef\xbb\xbf"), (
            "Le CSV ne porte pas de BOM UTF-8 : Excel francais affichera les "
            "accents en caractere de remplacement."
        )
        texte = csv_rep.content.decode("utf-8-sig")
        premiere = texte.splitlines()[0]
        assert "Prénom" in premiere, premiere
        assert ";" in premiere and "," not in premiere, (
            f"Le CSV doit utiliser le point-virgule attendu par Excel francais : "
            f"{premiere!r}"
        )
        assert len(texte.strip().splitlines()) == 4, texte
        print("  [OK] CSV : BOM UTF-8, point-virgules, lignes attendues.")

        # ------------------------------------------------------------------
        # 6. Format inconnu refuse
        # ------------------------------------------------------------------
        mauvais = await client.get(
            "/api/v1/etudiants/export", params={"format": "pdf"}, headers=admin
        )
        assert mauvais.status_code == 400, mauvais.text
        assert "xlsx" in mauvais.json()["detail"], mauvais.json()
        print("  [OK] Format inconnu refuse, avec la liste des formats.")

    print("E2E export de la liste des etudiants : OK")


if __name__ == "__main__":
    asyncio.run(_cleanup())
    shutil.rmtree(TEST_DIR, ignore_errors=True)
    try:
        _migrate()
        asyncio.run(_run())
    finally:
        asyncio.run(_cleanup())
        shutil.rmtree(TEST_DIR, ignore_errors=True)
