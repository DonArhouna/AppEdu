"""Salles physiques et conflits d'emploi du temps (lot 3).

Executable sans pytest :
    .\\\\venv\\\\Scripts\\\\python.exe test_salles_conflits_e2e.py

Ce que ce test verrouille :

1. **La salle existe.**  Une salle se cree avec un nom et un code uniques
   (casse ignoree) : la detection de conflits repose sur la correspondance
   entre ``cours.salle`` et ce nom, deux salles homonymes la rendraient
   ambigue.
2. **Le guard mord.**  Creer ou modifier un cours qui prend un creneau deja
   occupe — dans la meme salle, ou devant le meme enseignant — est refuse
   en 409 motive, avec le detail des seances en cause. Deux cours
   **consecutifs** (8h-10h puis 10h-12h) restent legaux : 10h n'est pas un
   chevauchement.
3. **L'audit regarde en arriere.**  Les conflits crees avant le guard
   restent en base ; ``GET /pedagogie/cours/conflits`` les liste. Le test
   fabrique un conflit en ecrivant directement en base, comme le ferait un
   emploi du temps pose avant l'activation du guard.
4. **Rien ne se perd.**  ``cours.salle`` reste un texte libre : une salle
   non inventoriee reste planifiable, et une salle encore citee par un
   cours ne se supprime pas (409) — elle se marque indisponible.
"""

import asyncio
import gc
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient

TEST_DIR = Path(tempfile.gettempdir()) / "appedu-salles-e2e"
TEST_DB_PATH = TEST_DIR / "salles.db"
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

ADMIN_EMAIL = "admin.salles@ecole-ci.org"
ADMIN_PASSWORD = "Salles-Admin-2026!"


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


def _details_conflits(detail: str):
    """Parse la liste JSON jointe au detail d'un 409 de conflit."""
    marqueur = "conflits="
    assert marqueur in detail, f"le detail ne porte pas la liste des conflits : {detail!r}"
    return json.loads(detail.split(marqueur, 1)[1])


async def _run() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://salles-test"
    ) as client:
        # -- Mise en place -------------------------------------------------
        setup = await client.post(
            "/api/v1/setup/initialize",
            json={
                "etablissement": {
                    "nom": "Institut Salles E2E", "code": "SAL-E2E",
                    "adresse": "", "telephone": "", "email": "c@salles-e2e.org",
                    "pays": "Sénégal", "devise": "XOF",
                },
                "admin": {
                    "email": ADMIN_EMAIL, "nom": "Admin", "prenom": "Salles",
                    "password": ADMIN_PASSWORD,
                },
            },
        )
        assert setup.status_code in (200, 201), f"{setup.status_code} {setup.text}"
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        assert login.status_code == 200, login.text
        admin_id = login.json()["user"]["id"]
        admin = {"Authorization": f"Bearer {login.json()['access_token']}"}

        filiere = (
            await client.post(
                "/api/v1/structure/filieres",
                json={
                    "nom": "Genie Salles", "code": "GSAL", "duree": 3,
                    "diplome": "Licence",
                },
                headers=admin,
            )
        ).json()
        ue = (
            await client.post(
                "/api/v1/structure/ues",
                json={
                    "nom": "UE Salles", "code": "UE-SAL", "filiere_id": filiere["id"],
                    "credits": 6, "coefficient": 2, "heures": 30,
                    "semestre": "S1", "niveau": "Licence 1",
                },
                headers=admin,
            )
        ).json()
        assert ue.get("id"), ue
        matiere = (
            await client.post(
                "/api/v1/structure/matieres",
                json={
                    "nom": "Algorithmique Salles", "code": "MAT-SAL", "ue_id": ue["id"],
                    "credits": 3, "coefficient": 1,
                    "heures_cm": 10, "heures_td": 5, "heures_tp": 5,
                },
                headers=admin,
            )
        ).json()
        assert matiere.get("id"), matiere

        # -- 1. La salle existe : CRUD, unicite casse ignoree --------------
        amphi = await client.post(
            "/api/v1/structure/salles",
            json={"nom": "Amphi A", "code": "AMPHI-A", "capacite": 150, "type_salle": "Amphithéâtre"},
            headers=admin,
        )
        assert amphi.status_code == 201, amphi.text
        amphi_id = amphi.json()["id"]

        doublon_nom = await client.post(
            "/api/v1/structure/salles",
            json={"nom": "amphi a", "code": "AMPHI-B"},
            headers=admin,
        )
        assert doublon_nom.status_code == 409, (
            f"Un doublon de nom (casse ignoree) doit etre refuse : "
            f"{doublon_nom.status_code} {doublon_nom.text}"
        )
        doublon_code = await client.post(
            "/api/v1/structure/salles",
            json={"nom": "Amphi C", "code": "amphi-a"},
            headers=admin,
        )
        assert doublon_code.status_code == 409, (
            f"Un doublon de code doit etre refuse : {doublon_code.status_code} {doublon_code.text}"
        )

        liste = await client.get("/api/v1/structure/salles", headers=admin)
        assert liste.status_code == 200, liste.text
        assert any(s["nom"] == "Amphi A" for s in liste.json()), liste.text

        anonyme = await client.get("/api/v1/structure/salles")
        assert anonyme.status_code == 401, (
            f"La liste des salles exige un jeton : {anonyme.status_code}"
        )

        # -- 2. Le guard mord : meme salle, meme creneau -------------------
        cours1 = await client.post(
            "/api/v1/pedagogie/cours",
            json={
                "matiere_id": matiere["id"], "enseignant_id": admin_id,
                "enseignant_nom": "Admin Salles", "salle": "Amphi A",
                "jour_semaine": "Lundi", "heure_debut": "08:00", "heure_fin": "10:00",
                "type_cours": "CM",
            },
            headers=admin,
        )
        assert cours1.status_code == 201, cours1.text
        cours1_id = cours1.json()["id"]

        conflit_salle = await client.post(
            "/api/v1/pedagogie/cours",
            json={
                "matiere_id": matiere["id"], "salle": "amphi a",
                "jour_semaine": "Lundi", "heure_debut": "09:00", "heure_fin": "11:00",
                "type_cours": "TD",
            },
            headers=admin,
        )
        assert conflit_salle.status_code == 409, (
            f"Deux cours dans la meme salle au meme moment doivent etre refuses : "
            f"{conflit_salle.status_code} {conflit_salle.text}"
        )
        conflits = _details_conflits(conflit_salle.json()["detail"])
        assert conflits and conflits[0]["type"] == "salle", conflits
        assert conflits[0]["cours_id"] == cours1_id, conflits

        # Consecutif, pas chevauchant : 10h == 10h n'est pas un conflit.
        consecutif = await client.post(
            "/api/v1/pedagogie/cours",
            json={
                "matiere_id": matiere["id"], "enseignant_id": admin_id,
                "salle": "Amphi A", "jour_semaine": "Lundi",
                "heure_debut": "10:00", "heure_fin": "12:00", "type_cours": "TD",
            },
            headers=admin,
        )
        assert consecutif.status_code == 201, (
            f"Deux cours consecutifs dans une meme salle sont legaux : "
            f"{consecutif.status_code} {consecutif.text}"
        )
        cours2_id = consecutif.json()["id"]

        autre_jour = await client.post(
            "/api/v1/pedagogie/cours",
            json={
                "matiere_id": matiere["id"], "salle": "Amphi A",
                "jour_semaine": "Mardi", "heure_debut": "08:00", "heure_fin": "10:00",
                "type_cours": "CM",
            },
            headers=admin,
        )
        assert autre_jour.status_code == 201, autre_jour.text

        # -- 3. Meme enseignant, autre salle -------------------------------
        conflit_ens = await client.post(
            "/api/v1/pedagogie/cours",
            json={
                "matiere_id": matiere["id"], "enseignant_id": admin_id,
                "enseignant_nom": "Admin Salles", "salle": "B103",
                "jour_semaine": "Lundi", "heure_debut": "10:30", "heure_fin": "12:30",
                "type_cours": "TD",
            },
            headers=admin,
        )
        assert conflit_ens.status_code == 409, (
            f"Un enseignant ne peut pas etre a deux endroits a la fois : "
            f"{conflit_ens.status_code} {conflit_ens.text}"
        )
        conflits = _details_conflits(conflit_ens.json()["detail"])
        assert conflits and conflits[0]["type"] == "enseignant", conflits

        # Sans enseignant, la meme salle libre reste planifiable.
        sans_ens = await client.post(
            "/api/v1/pedagogie/cours",
            json={
                "matiere_id": matiere["id"], "salle": "B103",
                "jour_semaine": "Lundi", "heure_debut": "10:30", "heure_fin": "12:30",
                "type_cours": "TD",
            },
            headers=admin,
        )
        assert sans_ens.status_code == 201, sans_ens.text

        # -- 4. Saisies non conformes : 422 nomme --------------------------
        jour_inconnu = await client.post(
            "/api/v1/pedagogie/cours",
            json={
                "matiere_id": matiere["id"], "salle": "B103",
                "jour_semaine": "Dimanche", "heure_debut": "08:00", "heure_fin": "10:00",
                "type_cours": "TD",
            },
            headers=admin,
        )
        assert jour_inconnu.status_code == 422, (
            f"« Dimanche » n'est pas un jour ouvrable : {jour_inconnu.status_code}"
        )
        horaires_faux = await client.post(
            "/api/v1/pedagogie/cours",
            json={
                "matiere_id": matiere["id"], "salle": "B103",
                "jour_semaine": "Lundi", "heure_debut": "10:00", "heure_fin": "08:00",
                "type_cours": "TD",
            },
            headers=admin,
        )
        assert horaires_faux.status_code == 422, (
            f"Une fin avant le debut doit etre refusee : {horaires_faux.status_code}"
        )

        # -- 5. Modification : l'etat resultant se verifie -----------------
        modification_conflit = await client.put(
            f"/api/v1/pedagogie/cours/{cours2_id}",
            json={"heure_debut": "09:00", "heure_fin": "11:00"},
            headers=admin,
        )
        assert modification_conflit.status_code == 409, (
            f"Deplacer un cours sur un creneau occupe doit etre refuse : "
            f"{modification_conflit.status_code} {modification_conflit.text}"
        )
        identique = await client.put(
            f"/api/v1/pedagogie/cours/{cours2_id}",
            json={"heure_debut": "10:00", "heure_fin": "12:00", "salle": "Amphi A"},
            headers=admin,
        )
        assert identique.status_code == 200, (
            f"Remettre un cours a l'identique doit reussir : "
            f"{identique.status_code} {identique.text}"
        )
        deplace = await client.put(
            f"/api/v1/pedagogie/cours/{cours2_id}",
            json={"heure_debut": "12:00", "heure_fin": "14:00"},
            headers=admin,
        )
        assert deplace.status_code == 200, deplace.text

        # -- 6. Salle indisponible : refusee a la planification ------------
        labo = await client.post(
            "/api/v1/structure/salles",
            json={"nom": "Labo Info", "code": "LABO-1", "disponible": True},
            headers=admin,
        )
        assert labo.status_code == 201, labo.text
        labo_id = labo.json()["id"]
        bascule = await client.put(
            f"/api/v1/structure/salles/{labo_id}",
            json={"disponible": False},
            headers=admin,
        )
        assert bascule.status_code == 200, bascule.text
        dans_labo = await client.post(
            "/api/v1/pedagogie/cours",
            json={
                "matiere_id": matiere["id"], "salle": "Labo Info",
                "jour_semaine": "Vendredi", "heure_debut": "08:00", "heure_fin": "10:00",
                "type_cours": "TP",
            },
            headers=admin,
        )
        assert dans_labo.status_code == 422, (
            f"Une salle indisponible refuse une nouvelle seance : "
            f"{dans_labo.status_code} {dans_labo.text}"
        )

        # Une salle non inventoriee reste planifiable : on ne bloque pas
        # un institut dont la salle n'est pas encore saisie.
        fantome = await client.post(
            "/api/v1/pedagogie/cours",
            json={
                "matiere_id": matiere["id"], "salle": "Salle Fantome",
                "jour_semaine": "Lundi", "heure_debut": "09:00", "heure_fin": "11:00",
                "type_cours": "TD",
            },
            headers=admin,
        )
        assert fantome.status_code == 201, (
            f"Une salle hors inventaire reste planifiable : "
            f"{fantome.status_code} {fantome.text}"
        )

        # -- 7. L'audit regarde en arriere --------------------------------
        propre = await client.get("/api/v1/pedagogie/cours/conflits", headers=admin)
        assert propre.status_code == 200, propre.text
        assert propre.json() == [], (
            f"Aucun conflit n'a passe le guard : {propre.json()}"
        )

        # Un conflit pose **avant** le guard (ecriture directe en base,
        # comme un emploi du temps historique) doit apparaitre.
        from sqlalchemy import update

        from app.models.pedagogie import Cours

        fantome_id = fantome.json()["id"]
        async with database.async_session_factory() as session:
            await session.execute(
                update(Cours).where(Cours.id == fantome_id).values(salle="Amphi A")
            )
            await session.commit()

        audit = await client.get("/api/v1/pedagogie/cours/conflits", headers=admin)
        assert audit.status_code == 200, audit.text
        conflits_audit = audit.json()
        assert len(conflits_audit) == 1, (
            f"Un seul conflit a ete fabrique : {conflits_audit}"
        )
        assert conflits_audit[0]["type"] == "salle", conflits_audit
        assert conflits_audit[0]["salle"].lower() == "amphi a", conflits_audit
        # L'audit rapporte la paire ; a la seconde pres (precision des
        # horodatages), l'attribution au « plus recent » n'est pas tranchable.
        assert conflits_audit[0]["cours_id"] in {fantome_id, cours1_id}, conflits_audit

        # -- 8. Une salle employee ne se supprime pas ----------------------
        suppression = await client.delete(
            f"/api/v1/structure/salles/{amphi_id}", headers=admin
        )
        assert suppression.status_code == 409, (
            f"Une salle citee par des cours ne se supprime pas : "
            f"{suppression.status_code} {suppression.text}"
        )
        labo_vide = await client.delete(
            f"/api/v1/structure/salles/{labo_id}", headers=admin
        )
        assert labo_vide.status_code == 204, (
            f"Une salle non employee se supprime : "
            f"{labo_vide.status_code} {labo_vide.text}"
        )

    print("  [OK] CRUD salles : unicite de nom (casse ignoree) et de code, 401 sans jeton.")
    print("  [OK] Conflit de salle refuse en 409 motive ; cours consecutifs legaux.")
    print("  [OK] Conflit d'enseignant refuse ; jour/horaires invalides en 422.")
    print("  [OK] Modification : etat resultant verifie, remise a l'identique acceptee.")
    print("  [OK] Salle indisponible refusee a la planification ; salle inconnue toleree.")
    print("  [OK] Audit des conflits historiques via /pedagogie/cours/conflits.")
    print("  [OK] Suppression : salle employee refusee, salle libre acceptee.")
    print("E2E salles & conflits EDT : OK")


if __name__ == "__main__":
    asyncio.run(_cleanup())
    shutil.rmtree(TEST_DIR, ignore_errors=True)
    try:
        _migrate()
        asyncio.run(_run())
    finally:
        asyncio.run(_cleanup())
        shutil.rmtree(TEST_DIR, ignore_errors=True)
