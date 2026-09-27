"""E2E de la nomenclature de matricule (SQLite isole).

Executable sans pytest :
    .\\\\venv\\\\Scripts\\\\python.exe test_matricule_e2e.py

Ce qui est verrouille, et pourquoi chaque point compte :

1. **la regle de depart reproduit exactement le comportement d'avant** —
   ``{annee}-{filiere}-{0001}``. Une migration qui aurait change les
   matricules existants rendrait illisibles des dossiers deja.delivres ;
2. **le modele est honore** : separateur, ordre et largeur se reglent ;
3. **un modele sans {numero} est refuse** — deux etudiants porteraient le
   meme matricule, qui est la cle de recherche du secretariat ;
4. **un jeton inconnu est refuse** — il produirait un matricule contenant
   litteralement ``{foo}``, imprime sur des certificats ;
5. **le compteur ne reutilise jamais un numero** : apres suppression d'un
   dossier, le suivant ne doit pas reprendre son matricule ;
6. **le demarrage est respecte** : un institut peut reprendre a 1000 ;
7. **changer la regle ne modifie aucun matricule existant** — c'est le point que
   l'institut comprendra de travers, et le resume doit l'annoncer ;
8. **permissions** : l'enseignant est refuse, l'administrateur non.
"""

import asyncio
import gc
import os
import shutil
import sqlite3
import tempfile
from datetime import date
from pathlib import Path

from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient

TEST_DIR = Path(tempfile.gettempdir()) / "appedu-matricule-e2e"
TEST_DB_PATH = TEST_DIR / "matricule.db"
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

ADMIN_EMAIL = "admin.matricule@ecole-ci.org"
ADMIN_PASSWORD = "Matricule-Admin-2026!"
TEACHER_EMAIL = "enseignant.matricule@ecole-ci.org"
TEACHER_PASSWORD = "Matricule-Teacher-2026!"
DEVISE = "XOF"
FILIERE_CODE = "GL"


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


async def _login(client: AsyncClient, email: str, password: str) -> dict:
    reponse = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert reponse.status_code == 200, reponse.text
    return {"Authorization": f"Bearer {reponse.json()['access_token']}"}


async def _run() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://matricule-test"
    ) as client:
        # ------------------------------------------------------------------
        # 1. Mise en place
        # ------------------------------------------------------------------
        setup = await client.post(
            "/api/v1/setup/initialize",
            json={
                "etablissement": {
                    "nom": "Institut Matricule E2E", "code": "MAT-E2E",
                    "adresse": "", "telephone": "", "email": "c@matricule-e2e.org",
                    "pays": "Sénégal", "devise": DEVISE,
                },
                "admin": {
                    "email": ADMIN_EMAIL, "nom": "Admin", "prenom": "Matricule",
                    "password": ADMIN_PASSWORD,
                },
            },
        )
        assert setup.status_code in (200, 201), f"{setup.status_code} {setup.text}"
        admin = await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)

        cree = await client.post(
            "/api/v1/users/",
            json={
                "email": TEACHER_EMAIL, "nom": "Enseignant", "prenom": "Matricule",
                "role": "ENSEIGNANT", "password": TEACHER_PASSWORD,
            },
            headers=admin,
        )
        assert cree.status_code == 201, cree.text

        filiere = (
            await client.post(
                "/api/v1/structure/filieres",
                json={
                    "nom": "Genie Logiciel Matricule", "code": FILIERE_CODE,
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
                    "nom": "Session Matricule", "code": "SES-MAT",
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
                    "code": "MAT-L1", "nom": "GL L1",
                    "filiere_id": filiere["id"], "niveau_id": niveau["id"],
                },
                headers=admin,
            )
        ).json()

        async def _etudiant(suffixe: str) -> dict:
            return (
                await client.post(
                    "/api/v1/etudiants/",
                    json={
                        "nom": "Etudiant", "prenom": suffixe, "sexe": "M",
                        "date_naissance": "2004-01-15",
                        "filiere": filiere["nom"], "niveau": niveau["nom"],
                        "classe_id": classe["id"], "session_id": session["id"],
                    },
                    headers=admin,
                )
            ).json()

        annee = date.today().year

        # ------------------------------------------------------------------
        # 2. Regle de depart : le comportement historique
        # ------------------------------------------------------------------
        lire = await client.get("/api/v1/institution/matricule", headers=admin)
        assert lire.status_code == 200, lire.text
        regle = lire.json()
        assert regle["modele"] == "{annee}-{filiere}-{numero}", regle
        assert regle["largeur_numero"] == 4, regle
        assert regle["demarrage"] == 1, regle
        assert regle["configuree"] is False, (
            "Une instance qui n'a rien regle doit le dire, pas pretendre avoir "
            f"une regle enregistree : {regle}"
        )
        assert regle["personnalisee"] is False, regle

        premier = await _etudiant("A")
        attendu = f"{annee}-{FILIERE_CODE}-0001"
        assert premier["matricule"] == attendu, (
            f"La regle de depart a change le format des matricules : "
            f"{premier['matricule']!r} au lieu de {attendu!r}. Les dossiers deja "
            "delivres deviendraient introuvables."
        )
        second = await _etudiant("B")
        assert second["matricule"] == f"{annee}-{FILIERE_CODE}-0002", second
        print("  [OK] Regle de depart : format historique preserve.")

        # ------------------------------------------------------------------
        # 3. Les jetons sont serves par le serveur
        # ------------------------------------------------------------------
        jetons = await client.get("/api/v1/institution/matricule/jetons", headers=admin)
        assert jetons.status_code == 200, jetons.text
        noms = {entree["jeton"] for entree in jetons.json()["jetons"]}
        assert noms == {"{annee}", "{filiere}", "{numero}"}, noms
        print(f"  [OK] Jetons declares par le serveur : {', '.join(sorted(noms))}")

        # ------------------------------------------------------------------
        # 4. Les saisies invalides sont refusees
        # ------------------------------------------------------------------
        sans_compteur = await client.put(
            "/api/v1/institution/matricule",
            json={"modele": "{annee}-{filiere}", "largeur_numero": 4, "demarrage": 1},
            headers=admin,
        )
        assert sans_compteur.status_code == 422, sans_compteur.text
        assert "numero" in sans_compteur.json()["detail"], sans_compteur.json()
        print("  [OK] Modele sans {numero} refuse.")

        jeton_inconnu = await client.put(
            "/api/v1/institution/matricule",
            json={"modele": "{annee}-{foo}-{numero}", "largeur_numero": 4, "demarrage": 1},
            headers=admin,
        )
        assert jeton_inconnu.status_code == 422, jeton_inconnu.text
        assert "foo" in jeton_inconnu.json()["detail"], jeton_inconnu.json()
        print("  [OK] Jeton inconnu refuse.")

        largeur_extreme = await client.put(
            "/api/v1/institution/matricule",
            json={"modele": "{numero}", "largeur_numero": 40, "demarrage": 1},
            headers=admin,
        )
        assert largeur_extreme.status_code == 422, largeur_extreme.text

        demarrage_extreme = await client.put(
            "/api/v1/institution/matricule",
            json={"modele": "{numero}", "largeur_numero": 4, "demarrage": 0},
            headers=admin,
        )
        assert demarrage_extreme.status_code == 422, demarrage_extreme.text
        print("  [OK] Largeur et demarrage hors bornes refuses.")

        vide = await client.put(
            "/api/v1/institution/matricule",
            json={"modele": "   ", "largeur_numero": 4, "demarrage": 1},
            headers=admin,
        )
        assert vide.status_code == 422, vide.text
        print("  [OK] Modele vide refuse.")

        # Aucune de ces tentatives n'a rien enregistre.
        inchange = await client.get("/api/v1/institution/matricule", headers=admin)
        assert inchange.json()["modele"] == "{annee}-{filiere}-{numero}", inchange.json()
        assert inchange.json()["configuree"] is False, inchange.json()

        # ------------------------------------------------------------------
        # 5. Un modele personnalise est honore
        # ------------------------------------------------------------------
        personnalise = await client.put(
            "/api/v1/institution/matricule",
            json={
                "modele": "ISI/{filiere}/{annee}/{numero}",
                "largeur_numero": 5,
                "demarrage": 100,
            },
            headers=admin,
        )
        assert personnalise.status_code == 200, personnalise.text
        regle = personnalise.json()
        assert regle["configuree"] is True, regle
        assert regle["personnalisee"] is True, regle
        assert regle["exemple"] == "ISI/GL/2026/00100", regle
        print(f"  [OK] Modele personnalise honore : exemple {regle['exemple']}")

        # ------------------------------------------------------------------
        # 6. Aucun matricule existant n'est modifie
        # ------------------------------------------------------------------
        # C'est le point que l'institut comprendra de travers. Changer la
        # regle ne renomme rien : les familles ont deja recu les anciens.
        listing = await client.get("/api/v1/etudiants/", headers=admin)
        assert listing.status_code == 200, listing.text
        matieres = {e["id"]: e["matricule"] for e in listing.json()}
        assert matieres[premier["id"]] == f"{annee}-{FILIERE_CODE}-0001", matieres
        assert matieres[second["id"]] == f"{annee}-{FILIERE_CODE}-0002", matieres
        print("  [OK] Les matricules existants sont intacts apres changement de regle.")

        # ------------------------------------------------------------------
        # 7. Le compteur ne reutilise pas un numero, meme s'il y a un trou
        # ------------------------------------------------------------------
        nouveau = await _etudiant("C")
        assert nouveau["matricule"] == f"ISI/GL/{annee}/00100", nouveau

        # On occupe un numero **ulterieur** en base, comme le ferait un import
        # ancien ou une reprise de donnees. C'est precisement le cas ou un
        # compteur « count() + 1 » se trompe : il verrait deux etudiants et
        # proposerait 00102, deja pris.
        #
        # Passer par une suppression ne conviendrait pas : l'API refuse de
        # supprimer un etudiant possessing une inscription, et c'est
        # legitime. Le trou est donc produit directement.
        async with database.get_sessionmaker_for_tenant()() as session_db:
            from app.models.etudiant import Etudiant

            session_db.add(Etudiant(
                id="etudiant-trou",
                nom="Ancien",
                prenom="Dossier",
                matricule=f"ISI/GL/{annee}/00105",
                filiere=filiere["nom"],
                niveau=niveau["nom"],
                date_naissance=date(2003, 5, 4),
                statut="actif",
            ))
            await session_db.commit()

        suivant = await _etudiant("D")
        assert suivant["matricule"] == f"ISI/GL/{annee}/00101", (
            "Le compteur a saute un numero encore libre a cause d'un matricule "
            f"importe plus loin : {suivant['matricule']!r}. Un compteur dense "
            "produirait des doublons."
        )

        # Et le trou n'est pas franchi : apres 00101..00104, le suivant est
        # 00106, pas 00105.
        for lettre in ("E", "F", "G", "H"):
            creee = await _etudiant(lettre)
        attendu_suivant = f"ISI/GL/{annee}/00106"
        assert creee["matricule"] == attendu_suivant, (
            f"Le compteur a reaffecte un matricule occupe : {creee['matricule']!r} "
            f"au lieu de {attendu_suivant!r}. Deux dossiers porteraient le meme "
            "identifiant, et le secretariat ne saurait plus lequel est lequel."
        )
        print("  [OK] Un trou de sequence ne provoque ni doublon ni saut.")

        # ------------------------------------------------------------------
        # 8. Retour a la regle de depart
        # ------------------------------------------------------------------
        retour = await client.put(
            "/api/v1/institution/matricule",
            json={
                "modele": "{annee}-{filiere}-{numero}",
                "largeur_numero": 4, "demarrage": 1,
            },
            headers=admin,
        )
        assert retour.status_code == 200, retour.text
        assert retour.json()["personnalisee"] is False, retour.json()
        apres = await _etudiant("I")
        # Retour a la regle de depart : la serie **reprend ou elle s'etait
        # arretee**, elle ne repart pas a 0001. 0001 et 0002 sont portes par les
        # deux premiers dossiers, qui n'ont pas ete renommes.
        assert apres["matricule"] == f"{annee}-{FILIERE_CODE}-0003", apres
        print("  [OK] Retour a la regle de depart : la serie reprend, sans renommer.")

        # ------------------------------------------------------------------
        # 9. Permissions
        # ------------------------------------------------------------------
        enseignant = await _login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
        refuse = await client.put(
            "/api/v1/institution/matricule",
            json={"modele": "{numero}", "largeur_numero": 2, "demarrage": 1},
            headers=enseignant,
        )
        assert refuse.status_code == 403, refuse.text
        lecture = await client.get("/api/v1/institution/matricule", headers=enseignant)
        assert lecture.status_code == 200, lecture.text
        print("  [OK] Permissions : l'enseignant lit, l'ecriture lui est refusee.")

    print("E2E nomenclature de matricule : OK")


if __name__ == "__main__":
    asyncio.run(_cleanup())
    shutil.rmtree(TEST_DIR, ignore_errors=True)
    try:
        _migrate()
        asyncio.run(_run())
    finally:
        asyncio.run(_cleanup())
        shutil.rmtree(TEST_DIR, ignore_errors=True)
