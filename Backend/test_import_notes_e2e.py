"""E2E de l'import de notes (SQLite isole).

Executable sans pytest :
    .\\\\venv\\\\Scripts\\\\python.exe test_import_notes_e2e.py

Ce qui est verrouche :

1. **l'analyse n'ecrit rien** — un dry-run qui enregistre une note est un
   import qui ne demande pas confirmation ;
2. **une cellule vide n'est pas un zero** — elle signifie « non evalue ». Zero
   et vide donnent des moyennes opposees ;
3. **la virgule decimale est lue** : « 12,5 » vaut 12,5, pas 125 ;
4. **les colonnes sont des evaluations** : chaque en-tete hors identite cree
   une evaluation, avec le type et le coefficient demandes ;
5. **un coefficient d'en-tete prime** : « Examen:2 » ne vaut pas 1 ;
6. **une note hors borne est une erreur de ligne, pas un blocage** — les
   bonnes lignes sont importees malgre elle ;
7. **un etudiant inconnu est signale, pas devine** — on ne redistribue pas des
   notes vers un homonyme ;
8. **l'import est idempotent** — reimporter le meme fichier **met a jour** au
   lieu de doubler les notes. Doubler fausserait toute moyenne ;
9. **le rapport se lit avant l'ecriture** : ce que l'agent a valide est ce qui
   est ecrit ;
10. **l'ecran ne peut pas promettre plus que l'API** : sans etudiant dans la
    classe, l'import est refuse, pas vide.
"""

import asyncio
import gc
import io
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient

TEST_DIR = Path(tempfile.gettempdir()) / "appedu-import-notes-e2e"
TEST_DB_PATH = TEST_DIR / "notes.db"
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

ADMIN_EMAIL = "admin.notes@ecole-ci.org"
ADMIN_PASSWORD = "Notes-Admin-2026!"
DEVISE = "XOF"


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


def xlsx(entetes, lignes) -> bytes:
    """Classeur minimal, par un vrai encodeur."""

    from openpyxl import Workbook

    classeur = Workbook()
    feuille = classeur.active
    feuille.append(entetes)
    for ligne in lignes:
        feuille.append(ligne)
    tampon = io.BytesIO()
    classeur.save(tampon)
    return tampon.getvalue()


async def _login(client: AsyncClient, email: str, password: str) -> dict:
    reponse = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert reponse.status_code == 200, reponse.text
    return {"Authorization": f"Bearer {reponse.json()['access_token']}"}


async def _run() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://notes-test"
    ) as client:
        # ------------------------------------------------------------------
        # 1. Mise en place
        # ------------------------------------------------------------------
        setup = await client.post(
            "/api/v1/setup/initialize",
            json={
                "etablissement": {
                    "nom": "Institut Notes E2E", "code": "NOT-E2E",
                    "adresse": "", "telephone": "", "email": "c@notes-e2e.org",
                    "pays": "Sénégal", "devise": DEVISE,
                },
                "admin": {
                    "email": ADMIN_EMAIL, "nom": "Admin", "prenom": "Notes",
                    "password": ADMIN_PASSWORD,
                },
            },
        )
        assert setup.status_code in (200, 201), f"{setup.status_code} {setup.text}"
        admin = await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)

        filiere = (
            await client.post(
                "/api/v1/structure/filieres",
                json={
                    "nom": "Genie Logiciel Notes", "code": "GLO",
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
                    "nom": "Session Notes", "code": "SES-NOT",
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
                    "code": "NOT-L1", "nom": "GL Notes L1",
                    "filiere_id": filiere["id"], "niveau_id": niveau["id"],
                },
                headers=admin,
            )
        ).json()
        ue = (
            await client.post(
                "/api/v1/structure/ues",
                json={
                    "nom": "Algorithmique", "code": "ALGO",
                    "credits": 4, "coefficient": 2,
                    "filiere_id": filiere["id"], "niveau": "L1",
                    "semestre": "S1", "heures": 60,
                },
                headers=admin,
            )
        ).json()
        matiere = (
            await client.post(
                "/api/v1/structure/matieres",
                json={
                    "nom": "Recurrence", "code": "REC",
                                        # Le poids de la matiere : 3. L'import ne le demande
                    # plus, il le prend ici.
                    "credits": 6, "coefficient": 3.0,
                    "heures_cm": 20, "heures_td": 10, "heures_tp": 8,
                    "ue_id": ue["id"],
                },
                headers=admin,
            )
        ).json()

        async def _etudiant(prenom: str, nom: str) -> dict:
            return (
                await client.post(
                    "/api/v1/etudiants/",
                    json={
                        "nom": nom, "prenom": prenom, "sexe": "M",
                        "date_naissance": "2004-01-15",
                        "filiere": filiere["nom"], "niveau": niveau["nom"],
                        "classe_id": classe["id"], "session_id": session["id"],
                    },
                    headers=admin,
                )
            ).json()

        amine = await _etudiant("Amine", "Ba")
        zoe = await _etudiant("Zoe", "Diallo")
        print("  [OK] Mise en place : classe, matiere, deux etudiants.")

        async def _analyser(contenu: bytes, **kwargs) -> dict:
            reponse = await client.post(
                "/api/v1/pedagogie/import/analyse",
                files={"fichier": ("notes.xlsx", contenu, "application/octet-stream")},
                data={
                    "classe_id": classe["id"],
                    "matiere_id": matiere["id"],
                    "session_id": session["id"],
                    **kwargs,
                },
                headers=admin,
            )
            return reponse

        async def _valider(rapport: dict):
            return await client.post(
                "/api/v1/pedagogie/import/valider", json=rapport, headers=admin
            )

        async def _notes() -> list:
            listing = await client.get(
                "/api/v1/pedagogie/notes",
                params={"matiere_id": matiere["id"], "session_id": session["id"]},
                headers=admin,
            )
            assert listing.status_code == 200, listing.text
            return listing.json()

        # ------------------------------------------------------------------
        # 2. L'analyse n'ecrit rien
        # ------------------------------------------------------------------
        fichier = xlsx(
            ["Matricule", "Nom", "Prénom", "Devoir 1", "Examen:2"],
            [
                [amine["matricule"], "Ba", "Amine", "14,5", "12"],
                [zoe["matricule"], "Diallo", "Zoe", "", "16"],
            ],
        )
        analyse = await _analyser(fichier)
        assert analyse.status_code == 200, analyse.text
        rapport = analyse.json()

        assert await _notes() == [], (
            "L'analyse a ecrit des notes : un dry-run qui enregistre est un "
            "import qui ne demande pas confirmation."
        )
        assert rapport["importable"] is True, rapport
        assert rapport["resume"]["total_notes"] == 3, rapport["resume"]
        # Le rapport porte le contexte. C'est lui qui rend la validation
        # incapable de faire autre chose que ce que l'agent a vu : sans
        # semestre dans le rapport, la validation ecrirait des notes sans
        # semestre en paraissant avoir suivi l'analyse.
        assert rapport["contexte"] == {"semestre_id": None, "rattrapage": False}, (
            rapport["contexte"]
        )
        print("  [OK] L'analyse n'ecrit aucune note, et porte le contexte de l'import.")

        # ------------------------------------------------------------------
        # 2 bis. Le rattrapage declare, refuse sans semestre
        # ------------------------------------------------------------------
        # Un rattrapage remplace la premiere tentative. Sans semestre, on ne
        # saurait pas laquelle remplacer — donc c'est refuse, pas devine.
        sans_semestre = await _analyser(fichier, rattrapage="true")
        assert sans_semestre.status_code == 422, sans_semestre.text
        assert "semestre" in sans_semestre.json()["detail"].lower(), (
            sans_semestre.json()
        )

        # Avec un semestre, l'analyse accepte et **renvoie** le contexte : c'est
        # lui que la validation relira.
        semestres = (
            await client.get(
                "/api/v1/academic/semestres/repartition",
                params={"session_id": session["id"]},
                headers=admin,
            )
        ).json()["semestres"]
        assert semestres, "La session doit porter des semestres."
        s1 = semestres[0]

        avec_semestre = await _analyser(
            fichier, semestre_id=s1["id"], rattrapage="true"
        )
        assert avec_semestre.status_code == 200, avec_semestre.text
        rapport_rat = avec_semestre.json()
        assert rapport_rat["contexte"] == {
            "semestre_id": s1["id"],
            "rattrapage": True,
        }, rapport_rat["contexte"]
        print("  [OK] Rattrapage : refuse sans semestre, renvoie le contexte quand il y en a un.")

        # ------------------------------------------------------------------
        # 3. Les colonnes deviennent des evaluations
        # ------------------------------------------------------------------
        par_nom = {e["nom"]: e for e in rapport["evaluations"]}
        assert set(par_nom) == {"Devoir 1", "Examen"}, list(par_nom)
        assert par_nom["Devoir 1"]["type"] == "CC", par_nom
        assert par_nom["Examen"]["type"] == "Examen Final", par_nom
        # Le coefficient d'en-tete prime sur celui de la matiere.
        assert par_nom["Examen"]["coefficient"] == 2.0, par_nom
        # Sans coefficient d'en-tete, c'est **celui de la matiere** qui s'applique.
        # Le demander dans le formulaire ouvrait deux poids concurrents pour la
        # meme matiere, et la moyenne aurait obei a l'agent.
        assert par_nom["Devoir 1"]["coefficient"] == 3.0, (
            f"Le coefficient par defaut n'est pas celui de la matiere : "
            f"{par_nom['Devoir 1']['coefficient']} au lieu de 3.0."
        )
        assert par_nom["Devoir 1"]["nouvelle"] is True, par_nom
        print("  [OK] Colonnes -> evaluations, avec type et coefficient.")

        # ------------------------------------------------------------------
        # 4. La virgule decimale, et vide != zero
        # ------------------------------------------------------------------
        lignes = {ligne["matricule"]: ligne for ligne in rapport["lignes"]}
        amine_l = lignes[amine["matricule"]]
        zoe_l = lignes[zoe["matricule"]]
        notes_amine = amine_l["notes"]
        notes_zoe = zoe_l["notes"]

        assert "devoir_1" in notes_amine, (
            f"Cle d'evaluation inattendue : {list(notes_amine)}. Deux "
            "normalisations differentes entre l'analyse et la validation "
            "feraient disparaitre silencieusement « Devoir 1 »."
        )
        assert notes_amine["devoir_1"] == 14.5, (
            f"La virgule decimale n'a pas ete lue : {notes_amine['devoir_1']!r} "
            "au lieu de 14.5."
        )
        # La cellule vide de Zoe donne None, pas 0.
        assert notes_zoe.get("devoir_1") is None, (
            f"Une cellule vide a ete lue comme un zero : {notes_zoe!r}. Zero et "
            "non evalue donnent des moyennes opposees."
        )
        assert amine_l["a_creer"] == 2, amine_l
        assert zoe_l["a_creer"] == 1, (
            f"Zoe n'a qu'une note, elle ne doit en creer qu'une : {zoe_l}"
        )
        assert not amine_l["erreurs"] and not zoe_l["erreurs"], rapport
        print("  [OK] Virgule decimale lue ; cellule vide = non evalue, pas zero.")

        # ------------------------------------------------------------------
        # 5. L'import ecrit ce que le rapport annoncait
        # ------------------------------------------------------------------
        validation = await _valider(rapport)
        assert validation.status_code == 201, validation.text
        bilan = validation.json()
        assert bilan["creees"] == 3, bilan
        assert bilan["modifiees"] == 0, bilan

        ecrites = await _notes()
        assert len(ecrites) == 3, f"3 notes attendues, {len(ecrites)} ecrites"
        valeurs = sorted(note["valeur"] for note in ecrites)
        assert valeurs == [12.0, 14.5, 16.0], valeurs
        print("  [OK] Ecriture conforme au rapport annonce.")

        # ------------------------------------------------------------------
        # 6. L'import est idempotent
        # ------------------------------------------------------------------
        # Le point le plus important pour une moyenne : reimporter le meme
        # fichier ne doit pas doubler les notes.
        seconde = await _analyser(fichier)
        rapport2 = seconde.json()
        for ligne in rapport2["lignes"]:
            if not ligne["ignoree"] and not ligne["erreurs"]:
                assert ligne["a_creer"] == 0, ligne
                assert ligne["a_modifier"] > 0, ligne
        assert all(not e["nouvelle"] for e in rapport2["evaluations"]), rapport2

        validation2 = await _valider(rapport2)
        assert validation2.status_code == 201, validation2.text
        bilan2 = validation2.json()
        assert bilan2["creees"] == 0, bilan2
        assert bilan2["modifiees"] == 3, bilan2
        assert len(await _notes()) == 3, (
            "Le reimport a double des notes : la moyenne serait fausse."
        )
        print("  [OK] Reimport : mise a jour, aucun doublon.")

        # Une valeur corrigee remplace l'ancienne, elle ne s'ajoute pas.
        corrige = xlsx(
            ["Matricule", "Nom", "Prénom", "Devoir 1", "Examen:2"],
            [[amine["matricule"], "Ba", "Amine", "09,5", "12"]],
        )
        rapport3 = (await _analyser(corrige)).json()
        await _valider(rapport3)
        valeurs_amine = sorted(
            note["valeur"]
            for note in await _notes()
            if note["etudiant_id"] == amine["id"]
        )
        assert valeurs_amine == [9.5, 12.0], valeurs_amine
        print("  [OK] Une note corrigee remplace l'ancienne.")

        # ------------------------------------------------------------------
        # 7. Une ligne en erreur n'en bloque pas les autres
        # ------------------------------------------------------------------
        melee = xlsx(
            ["Matricule", "Nom", "Prénom", "Devoir 1", "Examen:2"],
            [
                [amine["matricule"], "Ba", "Amine", "18", "12"],
                # Note hors borne.
                [zoe["matricule"], "Diallo", "Zoe", "25", "16"],
                # Matricule inconnu : on ne le redistribue pas.
                ["MATRICULE-QUI-EXISTE-PAS", "Fantasme", "Sans", "10", "10"],
            ],
        )
        rapport4 = (await _analyser(melee)).json()
        par_mat = {ligne["matricule"]: ligne for ligne in rapport4["lignes"]}
        assert par_mat[amine["matricule"]]["erreurs"] == [], par_mat[amine["matricule"]]
        assert par_mat[zoe["matricule"]]["erreurs"], (
            "Une note a 25 n'a pas ete signalee."
        )
        assert "dépasse" in par_mat[zoe["matricule"]]["erreurs"][0], par_mat[zoe["matricule"]]
        assert par_mat["MATRICULE-QUI-EXISTE-PAS"]["erreurs"], rapport4
        assert "Aucun étudiant" in par_mat["MATRICULE-QUI-EXISTE-PAS"]["erreurs"][0], rapport4
        assert rapport4["resume"]["lignes_en_erreur"] == 2, rapport4["resume"]
        # La ligne en erreur est explicitement non importable.
        for invalide in (zoe["matricule"], "MATRICULE-QUI-EXISTE-PAS"):
            ligne = par_mat[invalide]
            assert ligne["a_creer"] == 0 and ligne["a_modifier"] == 0, ligne

        bilan4 = (await _valider(rapport4)).json()
        # Les deux notes d'Amine existent deja : ce sont des **modifications**.
        # Aucune creation, parce que les deux lignes fautives n'ont produit
        # aucune note. C'est la preuve qu'une ligne rejetee n'ecrit rien.
        assert bilan4["creees"] == 0, bilan4
        assert bilan4["modifiees"] == 2, bilan4
        assert bilan4["lignes_ignorees"] == 2, bilan4
        # La bonne note est passee, les deux mauvaises n'ont rien ecrit.
        valeurs_amine = sorted(
            note["valeur"]
            for note in await _notes()
            if note["etudiant_id"] == amine["id"]
        )
        assert valeurs_amine == [12.0, 18.0], valeurs_amine
        assert len(await _notes()) == 3, (
            "Une ligne rejetee a quand meme ecrit une note."
        )
        print("  [OK] Une ligne fautive n'en bloque pas les autres.")

        # ------------------------------------------------------------------
        # 8. Les fichiers mal formes sont refuses avec une raison
        # ------------------------------------------------------------------
        sans_note = xlsx(["Matricule", "Nom", "Prénom"], [[amine["matricule"], "Ba", "Amine"]])
        refuse = await _analyser(sans_note)
        assert refuse.status_code == 422, refuse.text
        assert "évaluation" in refuse.json()["detail"], refuse.json()

        sans_identite = xlsx(["Devoir 1"], [[12]])
        refuse2 = await _analyser(sans_identite)
        assert refuse2.status_code == 422, refuse2.text
        assert "identifier" in refuse2.json()["detail"], refuse2.json()

        coefficient_abo = xlsx(["Matricule", "Examen:abc"], [[amine["matricule"], 12]])
        refuse3 = await _analyser(coefficient_abo)
        assert refuse3.status_code == 422, refuse3.text
        assert "coefficient" in refuse3.json()["detail"].lower(), refuse3.json()
        print("  [OK] Fichiers mal formes refuses, avec la cause.")

        # ------------------------------------------------------------------
        # 9. Une classe vide est refusee, pas importee vide
        # ------------------------------------------------------------------
        cycle2 = (
            await client.post(
                "/api/v1/academic/cycles",
                json={"nom": "Master", "code": "MAS"}, headers=admin,
            )
        ).json()
        niveau2 = (
            await client.post(
                "/api/v1/academic/niveaux",
                json={"code": "M1", "nom": "Master 1", "cycle_id": cycle2["id"]},
                headers=admin,
            )
        ).json()
        classe_vide = (
            await client.post(
                "/api/v1/academic/classes",
                json={
                    "code": "NOT-M1", "nom": "GL Notes M1",
                    "filiere_id": filiere["id"], "niveau_id": niveau2["id"],
                },
                headers=admin,
            )
        ).json()
        vide = await client.post(
            "/api/v1/pedagogie/import/analyse",
            files={"fichier": ("notes.xlsx", fichier, "application/octet-stream")},
            data={
                "classe_id": classe_vide["id"],
                "matiere_id": matiere["id"],
                "session_id": session["id"],
            },
            headers=admin,
        )
        assert vide.status_code == 422, vide.text
        assert "aucun" in vide.json()["detail"].lower(), vide.json()
        print("  [OK] Classe sans etudiant : refus explicite, pas d'import vide.")


        # ------------------------------------------------------------------
        # 10. Une matiere sans coefficient ne peut pas etre importee
        # ------------------------------------------------------------------
        # Le poids vient de la matiere : sans lui, la moyenne n'aurait aucun sens,
        # et l'import doit le dire plutot que d'inventer un coefficient de 1.
        async with database.get_sessionmaker_for_tenant()() as session_db:
            from sqlalchemy import select

            from app.models.structure import Matiere as _Matiere

            objet = (
                await session_db.execute(
                    select(_Matiere).where(_Matiere.id == matiere["id"])
                )
            ).scalars().first()
            objet.coefficient = 0
            await session_db.commit()

        sans_poids = await _analyser(fichier)
        assert sans_poids.status_code == 422, sans_poids.text
        detail = sans_poids.json()["detail"]
        assert "coefficient" in detail.lower(), detail

        async with database.get_sessionmaker_for_tenant()() as session_db:
            from sqlalchemy import select

            from app.models.structure import Matiere as _Matiere

            objet = (
                await session_db.execute(
                    select(_Matiere).where(_Matiere.id == matiere["id"])
                )
            ).scalars().first()
            objet.coefficient = 3.0
            await session_db.commit()
        print("  [OK] Matiere sans coefficient : import refuse, avec la raison.")
    print("E2E import de notes : OK")


if __name__ == "__main__":
    asyncio.run(_cleanup())
    shutil.rmtree(TEST_DIR, ignore_errors=True)
    try:
        _migrate()
        asyncio.run(_run())
    finally:
        asyncio.run(_cleanup())
        shutil.rmtree(TEST_DIR, ignore_errors=True)
