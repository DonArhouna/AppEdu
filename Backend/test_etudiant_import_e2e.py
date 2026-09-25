"""E2E de l'import massif d'etudiants (SQLite isole).

Executable sans pytest :
    .\\venv\\Scripts\\python.exe test_etudiant_import_e2e.py

La base est un fichier temporaire sous %TEMP% : aucune instance locale n'est
touchee, aucun reset n'est effectue.

Le scenario verifie la chaine complete :

1. cycle Alembic jusqu'a 0014 ;
2. contrat du fichier (modele) : en-tetes seuls, aucune donnee fictive ;
3. **analyse sans ecriture metier** : un dry-run ne cree aucun etudiant ;
4. diagnostic ligne a ligne : champs manquants, filiere/session/classe
   inconnues, date illisible, email invalide, doublons internes ;
5. validation : seules les lignes valides sont creees, matricules generes ;
6. mode ``mise_a_jour`` : un matricule existant met a jour au lieu de dupliquer ;
7. idempotence : revalider un lot ne cree rien de plus ;
8. annulation d'un lot analyse ;
9. guards : lecture pour le secretariat, refus pour l'enseignant.
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


TEST_DIR = Path(tempfile.gettempdir()) / "appedu-import-e2e"
TEST_DB_PATH = TEST_DIR / "import.db"
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

ADMIN_EMAIL = "admin.import@ecole-ci.org"
ADMIN_PASSWORD = "Import-Admin-2026!"
SECRETARY_EMAIL = "secretariat.import@ecole-ci.org"
SECRETARY_PASSWORD = "Import-Secretary-2026!"
TEACHER_EMAIL = "enseignant.import@ecole-ci.org"
TEACHER_PASSWORD = "Import-Teacher-2026!"

#: Referentiel cree par le scenario. Les libelles sont arbitraires mais
#: utilises par le test comme donnees d'entree, jamais exposes a l'utilisateur.
FILIERE_NOM = "Genie Logiciel Test"
FILIERE_CODE = "GLT"
NIVEAU_CODE = "L1"


def _csv(rows: list[list[str]]) -> bytes:
    """Construit un CSV separe par des points-virgules, comme Excel FR."""

    lines = [";".join(cell for cell in row) for row in rows]
    return ("\n".join(lines) + "\n").encode("utf-8")


#: Fichier de reference : 2 lignes valides + une ligne en erreur metier.
ENTETES = [
    "Nom",
    "Prénom",
    "Matricule",
    "Sexe",
    "Date de naissance",
    "Email",
    "Téléphone",
    "Filière",
    "Niveau",
    "Statut",
]


async def _cleanup() -> None:
    """Libere les handles SQLite temporaires (Windows refuse la suppression)."""

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
        try:
            TEST_DB_PATH.unlink()
        except OSError:
            pass
        await asyncio.sleep(0.2)


def _migrate() -> None:
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    config = Config(str(Path(__file__).resolve().parent / "alembic.ini"))
    command.upgrade(config, "0013_rbac_dynamic")
    command.upgrade(config, "head")
    command.downgrade(config, "0013_rbac_dynamic")
    command.upgrade(config, "head")


async def _login(client: AsyncClient, email: str, password: str) -> dict:
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _count_etudiants(db_path: Path) -> int:
    """Compte les etudiants en base, hors API, pour prouver le dry-run."""

    import sqlalchemy as sa
    from sqlalchemy import create_engine

    # Forme attendue par SQLAlchemy : sqlite:///C:/chemin/vers/fichier.db
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", future=True)
    try:
        with engine.connect() as connection:
            return int(connection.execute(sa.text("SELECT COUNT(*) FROM etudiants")).scalar() or 0)
    finally:
        engine.dispose()


async def _run() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://import-test"
    ) as client:
        # ------------------------------------------------------------------
        # 1. Mise en place : comptes et referentiel minimal
        # ------------------------------------------------------------------
        setup = await client.post(
            "/api/v1/setup/initialize",
            json={
                "etablissement": {
                    "nom": "Institut Import E2E",
                    "code": "IMP-E2E",
                    "adresse": "",
                    "telephone": "",
                    "email": "contact@import-e2e.org",
                    "devise": "XOF",
                },
                "admin": {
                    "email": ADMIN_EMAIL,
                    "nom": "Admin",
                    "prenom": "Import",
                    "password": ADMIN_PASSWORD,
                },
            },
        )
        assert setup.status_code in (200, 201), f"Setup: {setup.status_code} {setup.text}"
        admin_headers = await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)

        for email, password, role in (
            (SECRETARY_EMAIL, SECRETARY_PASSWORD, "SECRETARIAT"),
            (TEACHER_EMAIL, TEACHER_PASSWORD, "ENSEIGNANT"),
        ):
            created = await client.post(
                "/api/v1/users/",
                json={
                    "email": email,
                    "nom": role.capitalize(),
                    "prenom": "Import",
                    "role": role,
                    "password": password,
                },
                headers=admin_headers,
            )
            assert created.status_code == 201, created.text

        filiere = await client.post(
            "/api/v1/structure/filieres",
            json={
                "nom": FILIERE_NOM,
                "code": FILIERE_CODE,
                "duree": 3,
                "diplome": "Licence E2E",
                "niveau": NIVEAU_CODE,
            },
            headers=admin_headers,
        )
        assert filiere.status_code in (200, 201), filiere.text

        session_cree = await client.post(
            "/api/v1/sessions/",
            json={
                "nom": "Session E2E",
                "code": "SES-E2E",
                "annee_academique": "2026-2027",
                "date_debut": "2026-10-01",
                "date_fin": "2027-07-31",
                "statut": "active",
            },
            headers=admin_headers,
        )
        assert session_cree.status_code in (200, 201), (
            f"Session: {session_cree.status_code} {session_cree.text}"
        )

        # ------------------------------------------------------------------
        # 2. Contrat du fichier : en-tetes seuls, aucune donnee fictive
        # ------------------------------------------------------------------
        modele = await client.get(
            "/api/v1/etudiants/import/modele", headers=admin_headers
        )
        assert modele.status_code == 200, modele.text
        colonnes = {col["colonne"] for col in modele.json()["colonnes"]}
        assert {"nom", "prenom", "filiere", "session"} <= colonnes, colonnes

        modele_csv = await client.get(
            "/api/v1/etudiants/import/modele.csv", headers=admin_headers
        )
        assert modele_csv.status_code == 200
        lignes_csv = [l for l in modele_csv.text.strip().splitlines() if l.strip()]
        assert len(lignes_csv) == 1, "Le modele ne doit contenir que les en-tetes."
        print("  [OK] Modele : en-tetes documentes, aucune ligne d'exemple fictive.")

        # ------------------------------------------------------------------
        # 3-4. Analyse : rapport ligne a ligne, aucune ecriture metier
        # ------------------------------------------------------------------
        avant = await _count_etudiants(TEST_DB_PATH)
        # Reference : 2 lignes valides, puis une ligne en erreur par cas.
        fichier = _csv(
            [
                ENTETES + ["Session"],
                ["KOUASSI", "Adjoa", "", "F", "14/07/2004", "adjoa.k@exemple.org", "0707070707", FILIERE_NOM, NIVEAU_CODE, "Inscrit", "SES-E2E"],
                ["TANOH", "Aya", "", "FEMME", "2005-02-18", "", "0505050505", FILIERE_NOM, "L2", "", ""],
                ["", "SansNom", "", "", "", "", "", FILIERE_NOM, "L1", "", ""],
                ["ERREUR", "Filière", "", "", "", "", "", "Filiere Inexistante", "L1", "", ""],
                ["ERREUR", "Date", "", "", "32/13/2004", "", "", FILIERE_NOM, "L1", "", ""],
                ["ERREUR", "Email", "", "", "", "pas-un-email", "", FILIERE_NOM, "L1", "", ""],
                ["DOUBLON", "Interne", "", "", "", "", "", FILIERE_NOM, "L1", "", ""],
                ["DOUBLON", "Interne", "", "", "", "", "", FILIERE_NOM, "L1", "", ""],
                ["ERREUR", "Session", "", "", "", "", "", FILIERE_NOM, "L1", "", "SESSION-ABSENTE"],
            ]
        )

        analyse = await client.post(
            "/api/v1/etudiants/import/analyse",
            files={"fichier": ("etudiants.csv", fichier, "text/csv")},
            data={"mode": "creation"},
            headers=admin_headers,
        )
        assert analyse.status_code == 200, analyse.text
        rapport = analyse.json()

        assert rapport["nb_lignes"] == 9, rapport
        # 3 lignes importables (dont la 1re des deux lignes "doublon" : le
        # conflit n'est signale que sur la 2e), 6 lignes en erreur.
        assert rapport["nb_creer"] == 3, rapport
        assert rapport["nb_erreurs"] == 6, rapport
        colonnes_reconnues = {c["cible"] for c in rapport["colonnes_reconnues"]}
        assert {"nom", "prenom", "filiere", "session"} <= colonnes_reconnues

        par_ligne = {l["ligne"]: l for l in rapport["lignes"]}
        assert par_ligne[1]["statut"] == "valide", par_ligne[1]
        assert par_ligne[1]["action"] == "creer", par_ligne[1]
        # La 1re occurrence d'un doublon interne reste importable.
        assert par_ligne[7]["statut"] == "valide", par_ligne[7]
        assert par_ligne[2]["statut"] == "valide", par_ligne[2]
        # "FEMME" est normalise sans erreur : avertissement non bloquant.
        assert par_ligne[1]["email"] == "adjoa.k@exemple.org"
        assert "obligatoire" in " ".join(par_ligne[3]["erreurs"]).lower()
        assert any("Filière inconnue" in e for e in par_ligne[4]["erreurs"])
        assert any("illisible" in e for e in par_ligne[5]["erreurs"])
        assert any("email invalide" in e.lower() for e in par_ligne[6]["erreurs"])
        assert any("Doublon dans le fichier" in e for e in par_ligne[8]["erreurs"])
        assert any("Session inconnue" in e for e in par_ligne[9]["erreurs"])

        # Preuve du dry-run : zero etudiant cree par l'analyse.
        apres_analyse = await _count_etudiants(TEST_DB_PATH)
        assert apres_analyse == avant, (avant, apres_analyse)
        print(f"  [OK] Analyse : {rapport['nb_creer']} creations prevues, "
              f"{rapport['nb_erreurs']} erreurs, 0 ecriture metier (dry-run).")

        # ------------------------------------------------------------------
        # 5. Validation : seules les lignes valides sont creees
        # ------------------------------------------------------------------
        validation = await client.post(
            f"/api/v1/etudiants/import/{rapport['batch_id']}/valider",
            headers=admin_headers,
        )
        if validation.status_code != 200:
            # Le detail reste genere ; le message technique est conserve dans le
            # lot, consultable par l'administrateur dans l'historique.
            detail = await client.get(
                f"/api/v1/etudiants/import/{rapport['batch_id']}",
                headers=admin_headers,
            )
            raise AssertionError(
                f"Validation {validation.status_code} {validation.text} | "
                f"message du lot : {detail.json().get('message')}"
            )
        bilan = validation.json()
        assert bilan["nb_importes"] == 3, bilan

        listing = await client.get(
            "/api/v1/etudiants/", headers=admin_headers
        )
        assert listing.status_code == 200, listing.text
        etudiants = listing.json()
        assert len(etudiants) == 3, etudiants
        # Matricules generes automatiquement, format ANNEE-CODE-SEQ
        for etudiant in etudiants:
            assert etudiant["matricule"].startswith(f"{FILIERE_CODE}") or "-" in etudiant["matricule"]
            assert etudiant["filiere"] == FILIERE_NOM
        matricules = sorted(e["matricule"] for e in etudiants)
        assert len(set(matricules)) == 3, matricules
        print(f"  [OK] Validation : 3 etudiants crees, matricules {matricules}.")

        # ------------------------------------------------------------------
        # 7. Idempotence : revalider le lot ne cree rien de plus
        # ------------------------------------------------------------------
        revalidation = await client.post(
            f"/api/v1/etudiants/import/{rapport['batch_id']}/valider",
            headers=admin_headers,
        )
        assert revalidation.status_code == 200, revalidation.text
        # Le lot rejoue renvoie son bilan historique et n'ecrit rien de neuf.
        assert revalidation.json()["lignes"] == []
        # « deja valide » sans accent : le message serveur est accentue.
        assert "valid" in (revalidation.json()["message"] or "").lower()
        listing2 = await client.get("/api/v1/etudiants/", headers=admin_headers)
        assert len(listing2.json()) == 3, listing2.json()
        print("  [OK] Idempotence : revalider un lot ne duplique rien.")

        # ------------------------------------------------------------------
        # 6. Mode mise a jour : le matricule existant met a jour
        # ------------------------------------------------------------------
        maj_fichier = _csv(
            [
                ENTETES + ["Session"],
                [etudiants[0]["nom"], "NouveauPrenom", etudiants[0]["matricule"], "", "", "", "", FILIERE_NOM, NIVEAU_CODE, "Inscrit", "SES-E2E"],
            ]
        )
        analyse_maj = await client.post(
            "/api/v1/etudiants/import/analyse",
            files={"fichier": ("maj.csv", maj_fichier, "text/csv")},
            data={"mode": "mise_a_jour"},
            headers=admin_headers,
        )
        assert analyse_maj.status_code == 200, analyse_maj.text
        rapport_maj = analyse_maj.json()
        assert rapport_maj["nb_mettre_a_jour"] == 1, rapport_maj
        assert rapport_maj["nb_creer"] == 0, rapport_maj

        val_maj = await client.post(
            f"/api/v1/etudiants/import/{rapport_maj['batch_id']}/valider",
            headers=admin_headers,
        )
        assert val_maj.status_code == 200, val_maj.text
        assert val_maj.json()["nb_mises_a_jour"] == 1, val_maj.json()
        listing3 = await client.get("/api/v1/etudiants/", headers=admin_headers)
        assert len(listing3.json()) == 3, "La mise a jour ne doit pas creer de dossier."
        modifie = next(
            e for e in listing3.json() if e["id"] == etudiants[0]["id"]
        )
        assert modifie["prenom"] == "NouveauPrenom", modifie
        print("  [OK] Mise a jour : matricule existant mis a jour, aucun doublon.")

        # ------------------------------------------------------------------
        # 8. Annulation d'un lot analyse
        # ------------------------------------------------------------------
        a_annuler = await client.post(
            "/api/v1/etudiants/import/analyse",
            files={
                "fichier": (
                    "annulable.csv",
                    _csv([ENTETES, ["ZZZ", "Annule", "", "", "", "", "", FILIERE_NOM, "L1", ""]]),
                    "text/csv",
                )
            },
            data={"mode": "creation"},
            headers=admin_headers,
        )
        annulation = await client.post(
            f"/api/v1/etudiants/import/{a_annuler.json()['batch_id']}/annuler",
            headers=admin_headers,
        )
        assert annulation.status_code == 200, annulation.text
        assert annulation.json()["statut"] == "annule"
        refus = await client.post(
            f"/api/v1/etudiants/import/{a_annuler.json()['batch_id']}/valider",
            headers=admin_headers,
        )
        assert refus.status_code == 409, refus.text
        print("  [OK] Annulation : un lot annule ne peut plus etre valide.")

        # ------------------------------------------------------------------
        # 9. Guards : le secretariat ecrit, l'enseignant est refuse
        # ------------------------------------------------------------------
        secretary_headers = await _login(client, SECRETARY_EMAIL, SECRETARY_PASSWORD)
        teacher_headers = await _login(client, TEACHER_EMAIL, TEACHER_PASSWORD)

        assert (
            await client.get(
                "/api/v1/etudiants/import/", headers=secretary_headers
            )
        ).status_code == 200
        refuse = await client.post(
            "/api/v1/etudiants/import/analyse",
            files={
                "fichier": (
                    "x.csv",
                    _csv([ENTETES, ["TEST", "Enseignant", "", "", "", "", "", FILIERE_NOM, "L1", ""]]),
                    "text/csv",
                )
            },
            data={"mode": "creation"},
            headers=teacher_headers,
        )
        assert refuse.status_code == 403, refuse.text
        assert (
            await client.get("/api/v1/etudiants/import/", headers=teacher_headers)
        ).status_code == 403
        print("  [OK] Guards : students.write requis, l'enseignant est refuse.")

        # ------------------------------------------------------------------
        # 10. Fichier non exploitable : message explicite
        # ------------------------------------------------------------------
        vide = await client.post(
            "/api/v1/etudiants/import/analyse",
            files={"fichier": ("vide.csv", b"", "text/csv")},
            data={"mode": "creation"},
            headers=admin_headers,
        )
        assert vide.status_code == 422, vide.text
        sans_colonnes = await client.post(
            "/api/v1/etudiants/import/analyse",
            files={
                "fichier": (
                    "autre.csv",
                    _csv([["colonne1", "colonne2"], ["a", "b"]]),
                    "text/csv",
                )
            },
            data={"mode": "creation"},
            headers=admin_headers,
        )
        assert sans_colonnes.status_code == 422, sans_colonnes.text
        assert "nom" in sans_colonnes.json()["detail"].lower()
        print("  [OK] Robustesse : fichier vide ou sans colonne reconnue -> 422 explicite.")

    print("E2E import massif d'etudiants : OK")


if __name__ == "__main__":
    asyncio.run(_cleanup())
    shutil.rmtree(TEST_DIR, ignore_errors=True)
    try:
        _migrate()
        asyncio.run(_run())
    finally:
        asyncio.run(_cleanup())
        shutil.rmtree(TEST_DIR, ignore_errors=True)
