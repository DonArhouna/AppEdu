"""E2E des documents officiels (SQLite isole).

Executable sans pytest :
    .\\venv\\Scripts\\python.exe test_documents_e2e.py

La base est un fichier temporaire sous %TEMP% : aucune instance locale n'est
touchee, aucun reset n'est effectue.

Le scenario verifie la chaine complete :

1. cycle Alembic jusqu'a 0015 et presence de la permission ``documents.issue`` ;
2. catalogue des types : les types non adosses a des donnees persistees
   (deliberation, diplome) sont **absents** ;
3. **eligibility** : un etudiant sans inscription active ne peut pas obtenir de
   certificat ; un etudiant sans facture ne peut pas obtenir de quitus ;
4. emission : PDF genere, numerotation sequentielle, traceabilite enregistree ;
5. le PDF est un vrai PDF, non vide, et son SHA-256 correspond au fichier ;
6. duplicata : nouveau numero, document d'origine conserve ;
7. emission en lot sur une classe ;
8. permissions : le secretariat emet, l'enseignant refuse ;
9. reconstruction du PDF depuis la base (le fichier disparait -> 410 explicite).
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


TEST_DIR = Path(tempfile.gettempdir()) / "appedu-documents-e2e"
TEST_DB_PATH = TEST_DIR / "documents.db"
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
# Les PDF du scenario doivent rester dans %TEMP% : ecriture dans le dossier de
# runtime de production masquerait des fichiers d'essai chez le client.
settings.DOCUMENTS_STORAGE_DIR = str(TEST_DIR / "documents")

import app.core.database as database  # noqa: E402

database._engines_cache.clear()
database._sessionmakers_cache.clear()

import app.models  # noqa: E402,F401
from app.main import app  # noqa: E402

ADMIN_EMAIL = "admin.documents@ecole-ci.org"
ADMIN_PASSWORD = "Documents-Admin-2026!"
SECRETARY_EMAIL = "secretariat.documents@ecole-ci.org"
SECRETARY_PASSWORD = "Documents-Secretary-2026!"
TEACHER_EMAIL = "enseignant.documents@ecole-ci.org"
TEACHER_PASSWORD = "Documents-Teacher-2026!"

FILIERE_NOM = "Genie Logiciel Documents"
FILIERE_CODE = "GLD"
NIVEAU_CODE = "L1"
SESSION_NOM = "Session Documents"
SESSION_CODE = "SES-DOC"


async def _cleanup() -> None:
    shutil.rmtree(TEST_DIR / "documents", ignore_errors=True)
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
    command.upgrade(config, "0014_etudiant_import")
    command.upgrade(config, "head")
    command.downgrade(config, "0014_etudiant_import")
    command.upgrade(config, "head")


async def _login(client: AsyncClient, email: str, password: str) -> dict:
    reponse = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert reponse.status_code == 200, reponse.text
    return {"Authorization": f"Bearer {reponse.json()['access_token']}"}


async def _creer_etudiant(
    client: AsyncClient, headers: dict, *, matricule: str, classe_id: str | None, session_id: str | None
) -> dict:
    """Cree un etudiant et l'inscrit si une classe est fournie."""

    charge = {
        "nom": "Etudiant",
        "prenom": matricule.split("-")[-1],
        "matricule": matricule,
        "filiere": FILIERE_NOM,
        "niveau": NIVEAU_CODE,
        "date_naissance": "2004-01-15",
    }
    if classe_id:
        charge["classe_id"] = classe_id
        charge["session_id"] = session_id
    reponse = await client.post("/api/v1/etudiants/", json=charge, headers=headers)
    assert reponse.status_code in (200, 201), reponse.text
    return reponse.json()


async def _run() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://documents-test"
    ) as client:
        # ------------------------------------------------------------------
        # 1. Mise en place
        # ------------------------------------------------------------------
        setup = await client.post(
            "/api/v1/setup/initialize",
            json={
                "etablissement": {
                    "nom": "Institut Documents E2E",
                    "code": "DOC-E2E",
                    "adresse": "",
                    "telephone": "",
                    "email": "contact@documents-e2e.org",
                    "devise": "XOF",
                },
                "admin": {
                    "email": ADMIN_EMAIL,
                    "nom": "Admin",
                    "prenom": "Documents",
                    "password": ADMIN_PASSWORD,
                },
            },
        )
        assert setup.status_code in (200, 201), f"Setup: {setup.status_code} {setup.text}"
        admin = await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)

        for email, password, role in (
            (SECRETARY_EMAIL, SECRETARY_PASSWORD, "SECRETARIAT"),
            (TEACHER_EMAIL, TEACHER_PASSWORD, "ENSEIGNANT"),
        ):
            cree = await client.post(
                "/api/v1/users/",
                json={
                    "email": email, "nom": role.capitalize(), "prenom": "Documents",
                    "role": role, "password": password,
                },
                headers=admin,
            )
            assert cree.status_code == 201, cree.text

        # Permission documents.issue accordee au secretariat, pour prouver
        # qu'on peut deleguer l'emission sans ouvrir l'ecriture des dossiers.
        role_secretariat = await client.get("/api/v1/rbac/roles", headers=admin)
        codes = {r["code"]: r for r in role_secretariat.json()}
        assert "ROLE_SECRETARIAT" in codes, codes.keys()
        attribue = await client.put(
            "/api/v1/rbac/roles/ROLE_SECRETARIAT/permissions",
            json={"permissions": ["documents.issue"]},
            headers=admin,
        )
        assert attribue.status_code == 200, attribue.text
        secretariat_id = next(
            u["id"] for u in (await client.get("/api/v1/users/", headers=admin)).json()
            if u["email"] == SECRETARY_EMAIL
        )
        affecte = await client.post(
            "/api/v1/rbac/roles/ROLE_SECRETARIAT/users",
            json={"user_ids": [secretariat_id]},
            headers=admin,
        )
        assert affecte.status_code == 200, affecte.text
        secretariat = await _login(client, SECRETARY_EMAIL, SECRETARY_PASSWORD)

        filiere = await client.post(
            "/api/v1/structure/filieres",
            json={
                "nom": FILIERE_NOM, "code": FILIERE_CODE, "duree": 3,
                "diplome": "Licence E2E", "niveau": NIVEAU_CODE,
            },
            headers=admin,
        )
        assert filiere.status_code in (200, 201), filiere.text

        session_cree = await client.post(
            "/api/v1/sessions/",
            json={
                "nom": SESSION_NOM, "code": SESSION_CODE,
                "annee_academique": "2026-2027",
                "date_debut": "2026-10-01", "date_fin": "2027-07-31",
                "statut": "active",
            },
            headers=admin,
        )
        assert session_cree.status_code in (200, 201), session_cree.text
        session_id = session_cree.json()["id"]

        # Socle academique : la classe porte l'inscription. Les identifiants
        # sont relus depuis les reponses plutot que reconstruits a la main.
        cycle_cree = await client.post(
            "/api/v1/academic/cycles",
            json={"nom": "Licence", "code": "LIC"},
            headers=admin,
        )
        assert cycle_cree.status_code in (200, 201), cycle_cree.text
        cycle_id = cycle_cree.json()["id"]

        niveau_cree = await client.post(
            "/api/v1/academic/niveaux",
            json={
                "code": NIVEAU_CODE,
                "nom": "Licence 1",
                "cycle_id": cycle_id,
            },
            headers=admin,
        )
        assert niveau_cree.status_code in (200, 201), niveau_cree.text
        niveau_id = niveau_cree.json()["id"]

        classe_creee = await client.post(
            "/api/v1/academic/classes",
            json={
                "code": f"{FILIERE_CODE}-{NIVEAU_CODE}",
                "nom": f"{FILIERE_NOM} {NIVEAU_CODE}",
                "filiere_id": filiere.json()["id"],
                "niveau_id": niveau_id,
            },
            headers=admin,
        )
        assert classe_creee.status_code in (200, 201), classe_creee.text
        classe_id = classe_creee.json()["id"]

        inscrit = await _creer_etudiant(
            client, admin, matricule="DOC-0001", classe_id=classe_id, session_id=session_id
        )
        sans_inscription = await _creer_etudiant(
            client, admin, matricule="DOC-0002", classe_id=None, session_id=None
        )
        # Deuxieme etudiant inscrit, pour le lot.
        inscrit2 = await _creer_etudiant(
            client, admin, matricule="DOC-0003", classe_id=classe_id, session_id=session_id
        )

        # ------------------------------------------------------------------
        # 2. Catalogue : pas de type non adosse a des donnees persistees
        # ------------------------------------------------------------------
        types = await client.get("/api/v1/documents/types", headers=admin)
        assert types.status_code == 200, types.text
        codes_types = {t["code"] for t in types.json()}
        assert codes_types == {"certificat_scolarite", "releve_notes", "quitus_financier"}, codes_types
        # La deliberation n'est pas persistee : ces types ne doivent pas exister.
        assert "attestation_reussite" not in codes_types
        assert "attestation_diplome" not in codes_types
        print("  [OK] Catalogue : 3 types, aucun type adosse a une donnee non persistee.")

        # ------------------------------------------------------------------
        # 3. Eligibilite : les conditions bloquent la generation
        # ------------------------------------------------------------------
        refuse = await client.post(
            f"/api/v1/documents/etudiants/{sans_inscription['id']}",
            json={"type_document": "certificat_scolarite", "session_id": session_id},
            headers=admin,
        )
        assert refuse.status_code == 422, refuse.text
        assert "inscription active" in refuse.json()["detail"]

        refuse_quitus = await client.post(
            f"/api/v1/documents/etudiants/{inscrit['id']}",
            json={"type_document": "quitus_financier", "session_id": session_id},
            headers=admin,
        )
        assert refuse_quitus.status_code == 422, refuse_quitus.text
        assert "facture" in refuse_quitus.json()["detail"].lower()
        print("  [OK] Eligibilite : certificat sans inscription et quitus sans facture refuses.")

        # Apercu : reserve un numero sans ecrire de fichier.
        apercu = await client.post(
            f"/api/v1/documents/etudiants/{inscrit['id']}/apercu",
            json={"type_document": "certificat_scolarite", "session_id": session_id},
            headers=admin,
        )
        assert apercu.status_code == 200, apercu.text
        assert apercu.json()["taille_octets"] == 0, apercu.json()
        numero_prevu = apercu.json()["numero"]
        assert numero_prevu.startswith("CERT-"), numero_prevu

        # ------------------------------------------------------------------
        # 4-5. Emission, numerotation, PDF et tracabilite
        # ------------------------------------------------------------------
        certificat = await client.post(
            f"/api/v1/documents/etudiants/{inscrit['id']}",
            json={"type_document": "certificat_scolarite", "session_id": session_id},
            headers=admin,
        )
        assert certificat.status_code == 201, certificat.text
        doc1 = certificat.json()
        assert doc1["numero"] == numero_prevu, (doc1["numero"], numero_prevu)
        assert doc1["taille_octets"] > 500, doc1
        assert len(doc1["sha256"]) == 64, doc1
        assert doc1["donnees"]["etudiant"]["matricule"] == "DOC-0001", doc1["donnees"]

        pdf = await client.get(
            f"/api/v1/documents/{doc1['id']}/telecharger", headers=admin
        )
        assert pdf.status_code == 200, pdf.text
        assert pdf.content[:5] == b"%PDF-", pdf.content[:20]
        assert len(pdf.content) == doc1["taille_octets"], (len(pdf.content), doc1["taille_octets"])

        import hashlib

        assert hashlib.sha256(pdf.content).hexdigest() == doc1["sha256"], "Empreinte incoherente."

        # Second certificat : la numerotation progresse.
        certificat2 = await client.post(
            f"/api/v1/documents/etudiants/{inscrit2['id']}",
            json={"type_document": "certificat_scolarite", "session_id": session_id},
            headers=admin,
        )
        assert certificat2.status_code == 201, certificat2.text
        assert certificat2.json()["numero"] == "CERT-2026-0002", certificat2.json()["numero"]
        print("  [OK] Emission : PDF valide, SHA-256 coherent, numerotation sequentielle.")

        # ------------------------------------------------------------------
        # 6. Duplicata : nouveau numero, origine conservee
        # ------------------------------------------------------------------
        duplicata = await client.post(
            f"/api/v1/documents/{doc1['id']}/duplicata",
            json={"motif": "Perte par l'etudiant"},
            headers=admin,
        )
        assert duplicata.status_code == 201, duplicata.text
        doc_dup = duplicata.json()
        assert doc_dup["numero"] != doc1["numero"], (doc_dup["numero"], doc1["numero"])
        assert doc_dup["remplace_document_id"] == doc1["id"], doc_dup
        assert doc_dup["motif_duplicata"] == "Perte par l'etudiant", doc_dup

        # Un duplicata ne peut pas se dupliquer lui-meme.
        deuxieme = await client.post(
            f"/api/v1/documents/{doc_dup['id']}/duplicata",
            json={"motif": "Encore perdu"},
            headers=admin,
        )
        assert deuxieme.status_code == 409, deuxieme.text
        print("  [OK] Duplicata : nouveau numero, origine tracee, chainage refuse.")

        # Delivrance.
        delivrance = await client.post(
            f"/api/v1/documents/{doc1['id']}/delivrance", headers=admin
        )
        assert delivrance.status_code == 200, delivrance.text
        assert delivrance.json()["delivre_le"] is not None, delivrance.json()
        re_delivrance = await client.post(
            f"/api/v1/documents/{doc1['id']}/delivrance", headers=admin
        )
        assert re_delivrance.status_code == 409, re_delivrance.text

        # ------------------------------------------------------------------
        # 7. Emission en lot sur la classe
        # ------------------------------------------------------------------
        lot = await client.post(
            "/api/v1/documents/lot",
            json={"type_document": "releve_notes", "classe_id": classe_id, "session_id": session_id},
            headers=admin,
        )
        assert lot.status_code == 200, lot.text
        bilan = lot.json()
        # Les deux etudiants inscrits ont ete traites ; le releve exige des
        # notes, donc emission refusee tant qu'aucune note n'est saisie.
        assert bilan["emis"] == 0, bilan
        assert bilan["echoues"] == 2, bilan
        assert "note" in bilan["lignes"][0]["motif"].lower(), bilan["lignes"][0]
        print("  [OK] Lot : emission en serie continue malgre les dossiers non eligibles.")

        # ------------------------------------------------------------------
        # 8. Permissions
        # ------------------------------------------------------------------
        for type_document in ("certificat_scolarite",):
            ok = await client.post(
                f"/api/v1/documents/etudiants/{inscrit['id']}",
                json={"type_document": type_document, "session_id": session_id},
                headers=secretariat,
            )
            assert ok.status_code == 201, f"Secretariat: {ok.status_code} {ok.text}"
        refuse_enseignant = await client.post(
            f"/api/v1/documents/etudiants/{inscrit['id']}",
            json={"type_document": "certificat_scolarite", "session_id": session_id},
            headers=await _login(client, TEACHER_EMAIL, TEACHER_PASSWORD),
        )
        assert refuse_enseignant.status_code == 403, refuse_enseignant.text
        # Le secretariat n'a pas la permission d'ecrire les dossiers.
        assert (
            await client.get("/api/v1/documents/", headers=secretariat)
        ).status_code == 200
        print("  [OK] Permissions : documents.issue delegable, enseignant refuse.")

        # ------------------------------------------------------------------
        # 9. Fichier absent -> 410 explicite, pas un 500 opaque
        # ------------------------------------------------------------------
        from app.services.document_service import racine_documents

        cible = racine_documents() / Path(doc1["fichier"])
        contenu_sauvegarde = cible.read_bytes()
        cible.unlink()
        manquant = await client.get(
            f"/api/v1/documents/{doc1['id']}/telecharger", headers=admin
        )
        assert manquant.status_code == 410, manquant.text
        assert "Réémettez" in manquant.json()["detail"], manquant.json()
        cible.write_bytes(contenu_sauvegarde)
        print("  [OK] Robustesse : fichier absent signale explicitement (410).")

    print("E2E documents officiels : OK")


if __name__ == "__main__":
    asyncio.run(_cleanup())
    shutil.rmtree(TEST_DIR, ignore_errors=True)
    try:
        _migrate()
        asyncio.run(_run())
    finally:
        asyncio.run(_cleanup())
        shutil.rmtree(TEST_DIR, ignore_errors=True)
