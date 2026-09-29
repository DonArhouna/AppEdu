"""E2E du telechargement groupe des bulletins (SQLite isole).

Executable sans pytest :
    .\\venv\\Scripts\\python.exe test_bulletins_lot_e2e.py

Ce qui est verrouche :

1. **la route litterale ne se fait pas capter** par
   ``/bulletins/{etudiant_id}/{semestre_id}`` : l'archive classe existe, et
   le PDF individuel marche toujours ;
2. **le ZIP produit un PDF par etudiant inscrit**, aux noms distincts ;
3. **chaque PDF est un vrai document** (en-tete ``%PDF``), rendu par le meme
   ``rendre_bulletin_pour`` que le telechargement individuel — les chiffres du
   lot ne peuvent pas diverger du bulletin signe un par un ;
4. **une classe inconnue est un 404 nomme**, pas un ZIP vide ;
5. **une classe sans etudiant est refusee** : un ZIP vide se lirait comme des
   bulletins perdus, jamais comme une promotion sans eleve ;
6. **un etudiant en erreur n'interrompt pas le lot** : les autres PDF sortent,
   et un rapport ``_bulletins-non-produits.txt`` nomme l'eleve et la raison ;
7. **l'archive est protegee** comme le bulletin individuel : un compte
   COMPTABILITE, qui n'a pas ``pedagogy.read``, recoit 403.
"""

import asyncio
import gc
import io
import os
import shutil
import sqlite3
import tempfile
import zipfile
from pathlib import Path

from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient

TEST_DIR = Path(tempfile.gettempdir()) / "appedu-bulletins-lot-e2e"
TEST_DB_PATH = TEST_DIR / "bulletins-lot.db"
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

ADMIN_EMAIL = "admin.bulletins-lot@ecole-ci.org"
ADMIN_PASSWORD = "BulletinsLot-Admin-2026!"
COMPTA_EMAIL = "compta.bulletins-lot@ecole-ci.org"
COMPTA_PASSWORD = "BulletinsLot-Compta-2026!"


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
    # Aller-retour : la migration doit etre reversible sans residue.
    command.downgrade(config, "0018_relances_facturation")
    command.upgrade(config, "head")


async def _login(client: AsyncClient, email: str, password: str) -> dict:
    reponse = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert reponse.status_code == 200, reponse.text
    return {"Authorization": f"Bearer {reponse.json()['access_token']}"}


async def _run() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://bulletins-lot-test"
    ) as client:
        # ------------------------------------------------------------------
        # 1. Mise en place : classe, deux UE, deux matieres, trois etudiants
        # ------------------------------------------------------------------
        setup = await client.post(
            "/api/v1/setup/initialize",
            json={
                "etablissement": {
                    "nom": "Institut Bulletins Lot E2E", "code": "BLOT-E2E",
                    "adresse": "", "telephone": "",
                    "email": "c@bulletins-lot-e2e.org", "pays": "Côte d'Ivoire",
                    "devise": "XOF",
                },
                "admin": {
                    "email": ADMIN_EMAIL, "nom": "Admin", "prenom": "Bulletins",
                    "password": ADMIN_PASSWORD,
                },
            },
        )
        assert setup.status_code in (200, 201), f"{setup.status_code} {setup.text}"
        admin = await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)

        cree = await client.post(
            "/api/v1/users/",
            json={
                "email": COMPTA_EMAIL, "nom": "Compta", "prenom": "Bulletins",
                "role": "COMPTABILITE", "password": COMPTA_PASSWORD,
            },
            headers=admin,
        )
        assert cree.status_code == 201, cree.text
        compta = await _login(client, COMPTA_EMAIL, COMPTA_PASSWORD)

        filiere = (
            await client.post(
                "/api/v1/structure/filieres",
                json={
                    "nom": "Genie Logiciel Bulletins", "code": "GLB", "duree": 3,
                    "diplome": "Licence", "niveau": "L1",
                },
                headers=admin,
            )
        ).json()

        session = (
            await client.post(
                "/api/v1/sessions/",
                json={
                    "nom": "Session Bulletins Lot", "code": "SES-BLOT",
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
        niveau = (
            await client.post(
                "/api/v1/academic/niveaux",
                json={"code": "L1", "nom": "Licence 1", "cycle_id": cycle["id"]},
                headers=admin,
            )
        ).json()
        classe = (
            await client.post(
                "/api/v1/academic/classes",
                json={
                    "code": "GLB-L1", "nom": "Genie Logiciel L1",
                    "filiere_id": filiere["id"], "niveau_id": niveau["id"],
                },
                headers=admin,
            )
        ).json()

        semestres = (
            await client.get(
                "/api/v1/academic/semestres/repartition",
                params={"session_id": session["id"]},
                headers=admin,
            )
        ).json()["semestres"]
        assert semestres, "La session doit porter ses deux semestres initiaux."
        semestre = semestres[0]

        ue_forte = (
            await client.post(
                "/api/v1/structure/ues",
                json={
                    "nom": "UE Fondamentale", "code": "UEF", "credits": 4,
                    "coefficient": 2, "heures": 60, "filiere_id": filiere["id"],
                    "niveau": "L1", "semestre": "S1", "semestre_id": semestre["id"],
                },
                headers=admin,
            )
        ).json()
        matiere_forte = (
            await client.post(
                "/api/v1/structure/matieres",
                json={
                    "nom": "Algorithmes", "code": "ALG", "credits": 3,
                    "coefficient": 1, "heures_cm": 20, "heures_td": 10,
                    "heures_tp": 5, "ue_id": ue_forte["id"],
                },
                headers=admin,
            )
        ).json()

        async def _etudiant(prenom: str, nom: str, note: float) -> dict:
            etudiant = (
                await client.post(
                    "/api/v1/etudiants/",
                    json={
                        "nom": nom, "prenom": prenom, "sexe": "M",
                        "date_naissance": "2004-01-15",
                        "filiere": filiere["nom"], "niveau": "L1",
                        "classe_id": classe["id"], "session_id": session["id"],
                    },
                    headers=admin,
                )
            ).json()
            note_creee = await client.post(
                "/api/v1/pedagogie/notes",
                json={
                    "etudiant_id": etudiant["id"], "matiere_id": matiere_forte["id"],
                    "valeur": note, "coefficient": 1, "session_id": session["id"],
                },
                headers=admin,
            )
            assert note_creee.status_code in (200, 201), note_creee.text
            return etudiant

        amine = await _etudiant("Amine", "Ba", 15.0)
        zoe = await _etudiant("Zoe", "Diallo", 11.5)
        print("  [OK] Mise en place : classe, UE rattachée, deux étudiants notés.")

        # ------------------------------------------------------------------
        # 2. La route litterale existe, et le PDF individuel marche toujours
        # ------------------------------------------------------------------
        # ``/bulletins/classe/{c}/{s}/archive`` doit etre routee litteralement
        # et non captee par ``/bulletins/{etudiant_id}/{semestre_id}`` : un
        # lot qui rendrait « le bulletin d'un etudiant nomme 'classe' » est un
        # bug de routage, pas une fonctionnalite.
        individuel = await client.get(
            f"/api/v1/pedagogie/bulletins/{amine['id']}/{semestre['id']}/pdf",
            headers=admin,
        )
        assert individuel.status_code == 200, individuel.text
        assert individuel.content[:4] == b"%PDF", individuel.content[:10]
        print("  [OK] Le PDF individuel continue de sortir du meme calcul.")

        # ------------------------------------------------------------------
        # 3. Le lot produit un PDF par etudiant inscrit
        # ------------------------------------------------------------------
        lot = await client.get(
            f"/api/v1/pedagogie/bulletins/classe/{classe['id']}/{semestre['id']}/archive",
            headers=admin,
        )
        assert lot.status_code == 200, lot.text
        assert lot.headers["content-type"] == "application/zip", lot.headers
        with zipfile.ZipFile(io.BytesIO(lot.content)) as archive:
            noms = archive.namelist()
            pdfs = [nom for nom in noms if nom.lower().endswith(".pdf")]
            assert len(pdfs) == 2, f"Deux etudiants, deux PDF : {noms}"
            assert len(set(pdfs)) == 2, f"Les noms doivent etre distincts : {pdfs}"
            matricules = {amine["matricule"].lower(), zoe["matricule"].lower()}
            retrouves = {
                m for m in matricules
                for nom in pdfs
                if m in nom.lower()
            }
            assert len(retrouves) == 2, (
                f"Chaque eleve doit retrouver son PDF : {pdfs} vs {matricules}"
            )
            for nom in pdfs:
                contenu = archive.read(nom)
                assert contenu[:4] == b"%PDF", (
                    f"{nom} n'est pas un PDF (debut : {contenu[:10]!r})"
                )
        assert "attachment" in lot.headers.get("content-disposition", "")
        assert lot.headers["content-disposition"].endswith('.zip"'), (
            lot.headers.get("content-disposition")
        )
        print(f"  [OK] ZIP de la classe : {len(pdfs)} PDF, un par etudiant inscrit.")

        # ------------------------------------------------------------------
        # 4. Classe inconnue : 404 nomme
        # ------------------------------------------------------------------
        inconnue = await client.get(
            f"/api/v1/pedagogie/bulletins/classe/inconnu/{semestre['id']}/archive",
            headers=admin,
        )
        assert inconnue.status_code == 404, inconnue.text
        assert "classe" in inconnue.json()["detail"].lower(), inconnue.json()
        print("  [OK] Classe inconnue : 404 nommé, pas un ZIP vide.")

        # ------------------------------------------------------------------
        # 5. Classe sans etudiant : refusee, avec la raison
        # ------------------------------------------------------------------
        # Une classe est unique par (filiere, niveau) : la classe vide prend
        # donc un second niveau, sur la meme filiere.
        niveau_l2 = (
            await client.post(
                "/api/v1/academic/niveaux",
                json={"code": "L2", "nom": "Licence 2", "cycle_id": cycle["id"]},
                headers=admin,
            )
        ).json()
        classe_vide_reponse = await client.post(
            "/api/v1/academic/classes",
            json={
                "nom": "Genie Logiciel L2",
                "filiere_id": filiere["id"], "niveau_id": niveau_l2["id"],
            },
            headers=admin,
        )
        assert classe_vide_reponse.status_code in (200, 201), (
            classe_vide_reponse.text
        )
        classe_vide = classe_vide_reponse.json()
        vide = await client.get(
            f"/api/v1/pedagogie/bulletins/classe/{classe_vide['id']}/{semestre['id']}/archive",
            headers=admin,
        )
        assert vide.status_code == 422, vide.text
        assert "aucun" in vide.json()["detail"].lower(), vide.json()
        print("  [OK] Classe sans etudiant : refus explicite, pas d'archive vide.")

        # ------------------------------------------------------------------
        # 6. Un etudiant en erreur n'interrompt pas le lot
        # ------------------------------------------------------------------
        # Le lot doit tolerer l'echec du bulletin d'un eleve sans priver la
        # classe des autres : ni 500 pour toute la promotion, ni l'eleve
        # avale en silence. La panne est simulee au point de rendu (retraite
        # apres le bloc) : c'est precisement le comportement d'isolation de
        # l'endpoint que le test verrouille, indépendamment de la forme que
        # prend la donnee corrompue en production.
        semestre_courant = semestre["id"]
        import app.api.v1.endpoints.bulletins as endpoint_bulletins
        from app.services.bulletin_pdf import (
            rendre_bulletin_pour as rendre_bulletin_pour_reel,
        )

        async def _rendre_avec_panne(db, **kwargs):
            if kwargs["etudiant"].id == zoe["id"]:
                raise RuntimeError(
                    "Panne simulee : donnees illegibles pour cet etudiant."
                )
            return await rendre_bulletin_pour_reel(db, **kwargs)

        endpoint_bulletins.rendre_bulletin_pour = _rendre_avec_panne
        try:
            lot_partiel = await client.get(
                f"/api/v1/pedagogie/bulletins/classe/{classe['id']}/{semestre_courant}/archive",
                headers=admin,
            )
        finally:
            endpoint_bulletins.rendre_bulletin_pour = rendre_bulletin_pour_reel
        assert lot_partiel.status_code == 200, lot_partiel.text
        with zipfile.ZipFile(io.BytesIO(lot_partiel.content)) as archive:
            noms = archive.namelist()
            pdfs = [nom for nom in noms if nom.lower().endswith(".pdf")]
            rapports = [n for n in noms if n == "_bulletins-non-produits.txt"]
            assert len(pdfs) == 1, (
                f"Le bulletin d'Amine doit sortir malgre l'echec de Zoe : {noms}"
            )
            assert amine["matricule"].lower() in pdfs[0].lower(), pdfs
            assert rapports, f"Le rapport d'echecs doit etre joint : {noms}"
            rapport = archive.read(rapports[0]).decode("utf-8")
            assert zoe["matricule"] in rapport, rapport
            assert "Diallo" in rapport, rapport
        print("  [OK] Etudiant en erreur : les autres PDF sortent, rapport joint.")

        # ------------------------------------------------------------------
        # 7. Le lot est protege comme le bulletin individuel
        # ------------------------------------------------------------------
        refuse = await client.get(
            f"/api/v1/pedagogie/bulletins/classe/{classe['id']}/{semestre_courant}/archive",
            headers=compta,
        )
        assert refuse.status_code == 403, refuse.text
        print("  [OK] Sans pedagogy.read : 403, comme le bulletin individuel.")

    print("E2E bulletins par lot : OK")


if __name__ == "__main__":
    asyncio.run(_cleanup())
    shutil.rmtree(TEST_DIR, ignore_errors=True)
    try:
        _migrate()
        asyncio.run(_run())
    finally:
        asyncio.run(_cleanup())
        shutil.rmtree(TEST_DIR, ignore_errors=True)
