"""E2E des relances de facturation (SQLite isole).

Executable sans pytest :
    .\\venv\\Scripts\\python.exe test_relances_e2e.py

La base est un fichier temporaire sous %TEMP% : aucune instance locale n'est
touchee, aucun reset n'est effectue.

Le scenario verifie ce qui compte dans un module de recouvrement :

1. une facture **non echue** n'est pas une creance a relancer ;
2. une facture echue non soldee l'est, avec son anciennete ;
3. les paliers concordent avec la balance agee — deux vues du meme fait ne
   peuvent pas diverger ;
4. enregistrer une relance **fige** le montant et le detail des factures ;
5. le **niveau** progresse a partir des relances reellement enregistrees ;
6. relancer apres encaissement est **refuse** : relancer a tort decrédibilise
   l'etablissement ;
7. un moyen hors liste fermee est refuse ;
8. une relance datee dans le futur est refusee ;
9. le solde apres relance se renseigne par un appel distinct, et **ne bouge
   plus** ensuite : un paiement de mai ne doit pas retroagir sur une relance
   de janvier ;
10. permissions : la comptabilite relance, l'enseignant est refuse.

Le point 6 est le plus important : un module de relance qui laisse relancer
un etudiant deja solde produit un recouvrement absurde.
"""

import asyncio
import gc
import os
import re
import shutil
import sqlite3
import tempfile
from datetime import date, timedelta
from pathlib import Path

from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient

TEST_DIR = Path(tempfile.gettempdir()) / "appedu-relances-e2e"
TEST_DB_PATH = TEST_DIR / "relances.db"
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

ADMIN_EMAIL = "admin.relances@ecole-ci.org"
ADMIN_PASSWORD = "Relances-Admin-2026!"
COMPTABLE_EMAIL = "comptable.relances@ecole-ci.org"
COMPTABLE_PASSWORD = "Relances-Comptable-2026!"
TEACHER_EMAIL = "enseignant.relances@ecole-ci.org"
TEACHER_PASSWORD = "Relances-Teacher-2026!"

JOUR = 90
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
    command.upgrade(config, "0017_deliberation_pv")
    command.upgrade(config, "head")
    command.downgrade(config, "0017_deliberation_pv")
    command.upgrade(config, "head")


def _texte_compose(elements) -> str:
    """Texte du contenu compose, extrait des flowables.

    On lit ce que la lettre **dit**, pas ses glyphes. La mise en page reste
    verifiee ailleurs : PDF valide, en-tete de telechargement, nom de fichier.
    Ce qui compte ici est la decision — quel montant, quel niveau, quelles
    relances citees.
    """

    morceaux = []
    for element in elements:
        texte = getattr(element, "text", None)
        if isinstance(texte, str):
            morceaux.append(texte)
        cellules = getattr(element, "_cellvalues", None)
        if not cellules:
            continue
        for ligne in cellules:
            for cellule in ligne:
                if isinstance(cellule, list):
                    morceaux.append(_texte_compose(cellule))
                else:
                    sous = getattr(cellule, "text", None)
                    if isinstance(sous, str):
                        morceaux.append(sous)
    return " ".join(morceaux)


async def _charger(db, relance_id: str):
    from sqlalchemy import select

    from app.models.relance import Relance

    return (
        await db.execute(select(Relance).where(Relance.id == relance_id))
    ).scalars().first()


async def _infos_etablissement(db) -> dict:
    from sqlalchemy import select

    from app.models.etablissement import Etablissement
    from app.services.document_service import infos_etablissement

    etablissement = (await db.execute(select(Etablissement).limit(1))).scalars().first()
    return infos_etablissement(etablissement) if etablissement is not None else {}


async def _login(client: AsyncClient, email: str, password: str) -> dict:
    reponse = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert reponse.status_code == 200, reponse.text
    return {"Authorization": f"Bearer {reponse.json()['access_token']}"}


async def _run() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://relances-test"
    ) as client:
        # ------------------------------------------------------------------
        # 1. Mise en place
        # ------------------------------------------------------------------
        setup = await client.post(
            "/api/v1/setup/initialize",
            json={
                "etablissement": {
                    "nom": "Institut Relances E2E", "code": "REL-E2E",
                    "adresse": "", "telephone": "", "email": "c@relances-e2e.org",
                    "devise": DEVISE,
                },
                "admin": {
                    "email": ADMIN_EMAIL, "nom": "Admin", "prenom": "Relances",
                    "password": ADMIN_PASSWORD,
                },
            },
        )
        assert setup.status_code in (200, 201), f"{setup.status_code} {setup.text}"
        admin = await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)

        for email, password, role in (
            (COMPTABLE_EMAIL, COMPTABLE_PASSWORD, "COMPTABILITE"),
            (TEACHER_EMAIL, TEACHER_PASSWORD, "ENSEIGNANT"),
        ):
            cree = await client.post(
                "/api/v1/users/",
                json={
                    "email": email, "nom": role.capitalize(), "prenom": "Relances",
                    "role": role, "password": password,
                },
                headers=admin,
            )
            assert cree.status_code == 201, cree.text

        # Grille tarifaire : sans elle, aucune facture ne peut etre emise.
        filiere = (
            await client.post(
                "/api/v1/structure/filieres",
                json={
                    "nom": "Genie Logiciel Relances", "code": "GLR", "duree": 3,
                    "diplome": "Licence", "niveau": "L1",
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
                    "nom": "Session Relances", "code": "SES-REL",
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
                    "code": "GLR-L1", "nom": "Genie Logiciel L1",
                    "filiere_id": filiere["id"], "niveau_id": niveau["id"],
                },
                headers=admin,
            )
        ).json()

        async def _etudiant(matricule: str) -> dict:
            return (
                await client.post(
                    "/api/v1/etudiants/",
                    json={
                        "nom": "Etudiant", "prenom": matricule.split("-")[-1],
                        "matricule": matricule, "sexe": "M",
                        "date_naissance": "2004-01-15",
                        "filiere": filiere["nom"], "niveau": "L1",
                        "classe_id": classe["id"], "session_id": session["id"],
                    },
                    headers=admin,
                )
            ).json()

        async def _facture(etudiant: dict, montant: float, retard: int) -> dict:
            """Facture echue de « retard » jours (negatif = pas encore echue)."""

            creee = await client.post(
                "/api/v1/finances/factures",
                json={
                    "etudiant_id": etudiant["id"], "session_id": session["id"],
                    "montant_total": montant,
                    "date_emission": (date.today() - timedelta(days=retard + 10)).isoformat(),
                    "date_echeance": (date.today() - timedelta(days=retard)).isoformat(),
                    "description": f"Echeance de {montant:.0f} {DEVISE}",
                },
                headers=admin,
            )
            assert creee.status_code in (200, 201), creee.text
            return creee.json()

        # Trois profils de dette.
        ancien = await _etudiant("REL-0001")
        recent = await _etudiant("REL-0002")
        soldé = await _etudiant("REL-0003")
        pas_echu = await _etudiant("REL-0004")

        facture_ancienne = await _facture(ancien, 150000, JOUR)
        facture_recente = await _facture(recent, 50000, 20)
        facture_pas_echue = await _facture(pas_echu, 75000, -30)
        facture_soldee = await _facture(soldé, 30000, 60)

        # La facture du cas « soldé » est entierement reglee.
        # ``etudiant_id`` et ``session_id`` sont obligatoires : sans eux le
        # paiement est refuse en 422, et l'echec silencieux faisait croire
        # que la facture etait reglee.
        async def _regler(facture_id: str, etudiant_id: str, montant: float):
            reglement = await client.post(
                "/api/v1/finances/paiements",
                json={
                    "etudiant_id": etudiant_id, "session_id": session["id"],
                    "facture_id": facture_id, "montant": montant,
                    "mode_paiement": "Especes",
                },
                headers=admin,
            )
            assert reglement.status_code in (200, 201), (
                f"Reglement refuse ({reglement.status_code}) : {reglement.text[:200]}"
            )
            return reglement

        await _regler(facture_soldee["id"], soldé["id"], 30000)
        print("  [OK] Mise en place : dettes ancienne, recente, soldee, et facture non echue.")

        # ------------------------------------------------------------------
        # 2. Detection des creances
        # ------------------------------------------------------------------
        suivi = await client.get("/api/v1/finances/relances", headers=admin)
        assert suivi.status_code == 200, suivi.text
        vue = suivi.json()

        par_matricule = {item["matricule"]: item for item in vue["items"]}
        assert "REL-0001" in par_matricule, list(par_matricule)
        assert "REL-0002" in par_matricule, list(par_matricule)
        # Le cas soldé n'a plus de creance.
        assert "REL-0003" not in par_matricule, (
            "Une facture soldee ne doit pas apparaitre comme creance a relancer : "
            f"{par_matricule.get('REL-0003')}"
        )
        # La facture non echue non plus.
        assert "REL-0004" not in par_matricule, (
            "Une facture qui n'est pas echue n'est pas une creance : "
            f"{par_matricule.get('REL-0004')}"
        )

        ancien_item = par_matricule["REL-0001"]
        assert ancien_item["total_du"] == 150000.0, ancien_item
        assert ancien_item["retard_jours"] >= JOUR, ancien_item
        assert ancien_item["nb_creances"] == 1, ancien_item
        assert ancien_item["niveau_suivant"] == 1, ancien_item
        assert ancien_item["derniere_relance"] is None, ancien_item

        # Le plus ancien retard d'abord.
        retards = [item["retard_jours"] for item in vue["items"]]
        assert retards == sorted(retards, reverse=True), retards
        print("  [OK] Detection : creances echues seules, soldes et non echus exclus.")

        # ------------------------------------------------------------------
        # 2 bis. Les endpoints de recouvrement repondent vraiment
        # ------------------------------------------------------------------
        # Ces deux endpoints lisaient ``reste_a_payer`` comme une methode
        # alors que c'est une propriete : ils repondaient 500. Le test le
        # verifie, parce que ce calcul est au coeur du recouvrement.
        detail_facture = await client.get(
            f"/api/v1/finances/factures/{facture_ancienne['id']}", headers=admin
        )
        assert detail_facture.status_code == 200, (
            f"Detail d'une facture indisponible ({detail_facture.status_code}) : "
            f"{detail_facture.text[:200]}"
        )
        # Le schema expose ``reste_a_payer`` ; c'est la meme valeur que la
        # propriete du modele, calculee et non stockee.
        assert detail_facture.json()["reste_a_payer"] == 150000.0, detail_facture.json()

        balance_avant = await client.get("/api/v1/finances/balance-agee", headers=admin)
        assert balance_avant.status_code == 200, (
            f"Balance agee indisponible ({balance_avant.status_code}) : "
            f"{balance_avant.text[:200]}"
        )
        assert balance_avant.json()["total_creances"] > 0, balance_avant.json()
        print("  [OK] Detail de facture et balance agee repondent (calcul du reste).")

        # ------------------------------------------------------------------
        # 3. Concordance avec la balance agee
        # ------------------------------------------------------------------
        balance = (await client.get("/api/v1/finances/balance-agee", headers=admin)).json()
        # La balance agee porte les paliers **par etudiant** ; on les somme.
        total_balance = round(
            sum(
                item["retard_1_30_jours"] + item["retard_31_60_jours"]
                + item["retard_plus_60_jours"]
                for item in balance["items"]
            ),
            2,
        )
        # Cote relances, on recompute aussi depuis les items plutot que depuis
        # les totaux : cela verifie que les deux calculs concordent element par
        # element, et pas seulement en somme.
        par_matricule_balance = {item["matricule"]: item for item in balance["items"]}
        for item in vue["items"]:
            counterpart = par_matricule_balance.get(item["matricule"])
            assert counterpart is not None, (
                f"{item['matricule']} apparait a relancer mais pas dans la "
                "balance agee."
            )
            palier = counterpart["retard_1_30_jours"] + counterpart["retard_31_60_jours"] + counterpart["retard_plus_60_jours"]
            assert abs(palier - item["total_du"]) < 0.01, (
                f"Montant divergent pour {item['matricule']} : relances="
                f"{item['total_du']} balance agee={palier}"
            )

        total_relances = round(sum(item["total_du"] for item in vue["items"]), 2)
        assert abs(total_relances - total_balance) < 0.01, (
            "Les deux vues du meme fait divergent : relances="
            f"{total_relances} balance agee={total_balance}"
        )
        print("  [OK] Concordance : les paliers recoupent la balance agee au centime.")

        # ------------------------------------------------------------------
        # 4. Moyens disponibles
        # ------------------------------------------------------------------
        moyens = (await client.get("/api/v1/finances/relances/moyens", headers=admin)).json()
        assert "Courrier" in moyens, moyens
        assert "Appel telephonique" in moyens, moyens
        print(f"  [OK] Moyens declares par le serveur : {', '.join(moyens)}")

        # ------------------------------------------------------------------
        # 5. Enregistrer une relance, et figer l'instantane
        # ------------------------------------------------------------------
        premiere = await client.post(
            "/api/v1/finances/relances",
            json={
                "etudiant_id": ancien["id"], "moyen": "Courrier",
                "message": "Lettre de relance pour l'echeance non soldee.",
            },
            headers=admin,
        )
        assert premiere.status_code == 201, premiere.text
        relance = premiere.json()
        assert relance["relance"]["niveau"] == 1, relance
        assert relance["relance"]["montant_reclame"] == 150000.0, relance
        assert relance["relance"]["nb_factures"] == 1, relance
        assert relance["resume"]["montant_reclame"] == 150000.0, relance
        # Le solde apres relance n'est pas invente.
        assert relance["relance"]["solde_apres"] is None, relance
        assert relance["relance"]["resolue"] is False, relance
        # Le detail fige reprend la facture concernee.
        facture_figee = relance["relance"]["factures_concernees"][0]
        assert facture_figee["numero"] == facture_ancienne["numero_facture"], facture_figee
        assert facture_figee["reste"] == 150000.0, facture_figee
        print("  [OK] Relance consignee : montant et factures figes.")

        # L'instantane survit a l'encaissement : on solde la facture, la
        # relance doit toujours dire ce qui a ete reclame.
        await _regler(facture_ancienne["id"], ancien["id"], 150000)
        historique = (
            await client.get(
                "/api/v1/finances/relances/historique", headers=admin
            )
        ).json()
        figee = historique[0]
        assert figee["montant_reclame"] == 150000.0, (
            "L'instantane ne doit pas etre reecrit par l'encaissement : "
            f"{figee}"
        )
        assert figee["resolue"] is False, (
            "Une relance sans solde constate n'est pas resolue : le solde doit "
            "etre renseigne par un appel distinct."
        )
        print("  [OK] Instantane fige : l'encaissement ne reecrit pas le passe.")

        # ------------------------------------------------------------------
        # 6. Le solde apres relance se renseigne, puis ne bouge plus
        # ------------------------------------------------------------------
        solde = await client.post(
            "/api/v1/finances/relances/solde",
            params={"etudiant_id": ancien["id"], "niveau": 1},
            headers=admin,
        )
        assert solde.status_code == 200, solde.text
        assert solde.json()["solde_apres"] == 0.0, solde.json()

        historique = (
            await client.get(
                "/api/v1/finances/relances/historique", headers=admin
            )
        ).json()
        assert historique[0]["resolue"] is True, historique[0]
        assert historique[0]["solde_apres"] == 0.0, historique[0]

        # Une autre dette ne doit pas retroagir sur ce solde constate.
        await _facture(ancien, 70000, 10)
        historique = (
            await client.get(
                "/api/v1/finances/relances/historique", headers=admin
            )
        ).json()
        assert historique[0]["solde_apres"] == 0.0, (
            "Un paiement posterieur ne doit pas reecrire le solde constate : "
            f"{historique[0]}"
        )
        print("  [OK] Solde constate fige au moment de la relance.")

        # ------------------------------------------------------------------
        # 7. Le niveau progresse sur les relances reellement faites
        # ------------------------------------------------------------------
        # L'etudiant a une nouvelle creance : il redevient relançable.
        suivi = (await client.get("/api/v1/finances/relances", headers=admin)).json()
        par_matricule = {item["matricule"]: item for item in suivi["items"]}
        assert "REL-0001" in par_matricule, list(par_matricule)
        assert par_matricule["REL-0001"]["niveau_suivant"] == 2, par_matricule["REL-0001"]
        assert par_matricule["REL-0001"]["nb_relances"] == 1, par_matricule["REL-0001"]
        assert par_matricule["REL-0001"]["derniere_relance"]["niveau"] == 1

        seconde = await client.post(
            "/api/v1/finances/relances",
            json={"etudiant_id": ancien["id"], "moyen": "Appel telephonique"},
            headers=admin,
        )
        assert seconde.status_code == 201, seconde.text
        assert seconde.json()["relance"]["niveau"] == 2, seconde.json()
        assert seconde.json()["relance"]["montant_reclame"] == 70000.0, seconde.json()
        print("  [OK] Niveau progresse depuis l'historique reel (1re, puis 2e).")

        # ------------------------------------------------------------------
        # 8. Relancer apres encaissement est refuse
        # ------------------------------------------------------------------
        deja_solde = await client.post(
            "/api/v1/finances/relances",
            json={"etudiant_id": soldé["id"], "moyen": "Courrier"},
            headers=admin,
        )
        assert deja_solde.status_code == 422, deja_solde.text
        assert "rien à relancer" in deja_solde.json()["detail"], deja_solde.json()
        print("  [OK] Relance d'un etudiant deja soldee refusee.")

        # ------------------------------------------------------------------
        # 9. Saisies invalides refusees
        # ------------------------------------------------------------------
        moyen_inconnu = await client.post(
            "/api/v1/finances/relances",
            json={"etudiant_id": recent["id"], "moyen": "Pigeon"},
            headers=admin,
        )
        assert moyen_inconnu.status_code == 422, moyen_inconnu.text
        assert "Moyen de relance inconnu" in moyen_inconnu.json()["detail"]

        futur = await client.post(
            "/api/v1/finances/relances",
            json={
                "etudiant_id": recent["id"], "moyen": "Courrier",
                "date_relance": (date.today() + timedelta(days=5)).isoformat(),
            },
            headers=admin,
        )
        assert futur.status_code == 422, futur.text
        assert "postérieure" in futur.json()["detail"], futur.json()

        inexistant = await client.post(
            "/api/v1/finances/relances",
            json={"etudiant_id": "matricule-inexistant", "moyen": "Courrier"},
            headers=admin,
        )
        assert inexistant.status_code in (404, 422), inexistant.text
        print("  [OK] Moyen hors liste, date future et etudiant inconnu refuses.")

        # ------------------------------------------------------------------
        # 10. Permissions
        # ------------------------------------------------------------------
        comptable = await _login(client, COMPTABLE_EMAIL, COMPTABLE_PASSWORD)
        lecture = await client.get("/api/v1/finances/relances", headers=comptable)
        assert lecture.status_code == 200, lecture.text
        ecriture = await client.post(
            "/api/v1/finances/relances",
            json={"etudiant_id": recent["id"], "moyen": "Guichet"},
            headers=comptable,
        )
        assert ecriture.status_code == 201, ecriture.text

        enseignant = await _login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
        refuse = await client.post(
            "/api/v1/finances/relances",
            json={"etudiant_id": recent["id"], "moyen": "Courrier"},
            headers=enseignant,
        )
        assert refuse.status_code == 403, refuse.text
        lecture_refusee = await client.get(
            "/api/v1/finances/relances", headers=enseignant
        )
        assert lecture_refusee.status_code == 403, lecture_refusee.text
        print("  [OK] Permissions : la comptabilite relance, l'enseignant est refuse.")

        # ------------------------------------------------------------------
        # ------------------------------------------------------------------
        # 8 bis. La lettre : ce qui a ete reclame, pas le solde du jour
        # ------------------------------------------------------------------
        # La lettre est le document que le secretariat remet. Elle doit dire ce
        # qui a ete reclame a la date de la relance, meme apres encaissement.
        premiere_id = relance["relance"]["id"]

        lettre = await client.get(
            f"/api/v1/finances/relances/{premiere_id}/lettre", headers=admin
        )
        assert lettre.status_code == 200, lettre.text
        assert lettre.headers["content-type"].startswith("application/pdf"), (
            lettre.headers.get("content-type")
        )
        assert lettre.content.startswith(b"%PDF"), "La lettre doit etre un PDF."
        assert len(lettre.content) > 1500, (
            f"Lettre de {len(lettre.content)} octets : elle est probablement vide."
        )
        # Un nom generique serait introuvable au moment d'en avoir besoin : la
        # reference doit figurer dedans.
        assert "relance_" in lettre.headers.get("content-disposition", ""), (
            lettre.headers.get("content-disposition")
        )
        print("  [OK] Lettre : PDF valide et nommee d'apres sa reference.")

        # Le contenu, lui, se lit sur ce que la lettre a compose.
        from app.core.database import get_sessionmaker_for_tenant
        from app.services.relance_pdf import composer, relances_precedentes

        fabrique = get_sessionmaker_for_tenant()
        # Pas `session` : ce nom designe la session academique du scenario, et
        # l'ecraser ici casserait les appels de factures suivants.
        async with fabrique() as session_db:
            objet = await _charger(session_db, premiere_id)
            assert objet is not None, "La relance doit exister en base."
            infos = await _infos_etablissement(session_db)
            anterieures = await relances_precedentes(session_db, objet)
            texte = _texte_compose(composer(objet, infos, anterieures))

        # La 1re relance reclamait 150 000, et la facture a ete reglee depuis.
        # La lettre doit toujours dire 150 000 : c'est l'instantane.
        assert "150 000,00 XOF" in texte, (
            "La lettre ne reprend pas le montant reclame au moment de la "
            f"relance. Contenu : {texte[:400]!r}"
        )
        # Le « 0,00 » qui figure aussi est legitime : c'est la colonne « Regle »
        # de la facture, qui n'etait pas encaissee au jour de la relance. Ce
        # qu'on refuse, c'est un **reste** nul — donc un restant du de zero.
        assert "Montant réclamé" in texte, (
            f"Le montant reclame n'est pas nomme dans la lettre : {texte[:400]!r}"
        )
        reste = objet.factures_concernees[0]["reste"]
        assert reste == 150000.0, (
            f"L'instantane porte un reste de {reste} au lieu de 150000 : "
            "la lettre ne pourrait pas dire ce qui a ete reclame."
        )
        assert "REL-0001" in texte, f"Matricule absent : {texte[:400]!r}"
        assert re.search(r"REL-\d{8}-REL-0001-N1", texte), (
            f"Reference absente ou fausse : {texte[:400]!r}"
        )
        # Elle dit ce qu'elle n'est pas : une attestation.
        assert "ne constitue pas" in texte, (
            "La lettre ne precise pas qu'elle n'est pas une attestation : "
            "un parent pourrait la prendre pour un document officiel."
        )
        print("  [OK] Lettre : montant fige malgre l'encaissement, matricule et reference.")

        # Une 3e relance, puis on relit la 2e : elle doit toujours se dire la
        # 2e, et ne citer que la 1re comme precedente.
        await _facture(ancien, 30000, 5)
        troisieme = await client.post(
            "/api/v1/finances/relances",
            json={"etudiant_id": ancien["id"], "moyen": "Courrier"},
            headers=admin,
        )
        assert troisieme.status_code == 201, troisieme.text
        assert troisieme.json()["relance"]["niveau"] == 3, troisieme.json()

        async with fabrique() as session_db:
            objet2 = await _charger(session_db, seconde.json()["relance"]["id"])
            anterieures2 = await relances_precedentes(session_db, objet2)
            niveaux_cites = [a.niveau for a in anterieures2]
            texte2 = _texte_compose(composer(objet2, infos, anterieures2))

        assert re.search(r"REL-\d{8}-REL-0001-N2", texte2), (
            "La 2e lettre ne se presente plus comme la 2e apres une 3e "
            f"relance : elle reecrit le passe. Contenu : {texte2[:400]!r}"
        )
        assert niveaux_cites == [1], (
            "La 2e lettre cite des relances qu'elle ne pouvait pas connaitre : "
            f"niveaux {niveaux_cites}"
        )
        print("  [OK] Une relance anterieure ne se reecrit pas apres une relance ulterieure.")

        # La lettre n'est pas un document officiel : le registre reste vide.
        registre = await client.get("/api/v1/documents/", headers=admin)
        assert registre.status_code == 200, registre.text
        assert registre.json() == [], (
            "Une lettre de relance a ete inscrite au registre des documents "
            f"officiels : {len(registre.json())} entree(s). Une demande de "
            "reglement n'est pas une attestation."
        )

        # Une relance inexistante ne doit pas produire de lettre.
        introuvable = await client.get(
            "/api/v1/finances/relances/relance-inexistante/lettre", headers=admin
        )
        assert introuvable.status_code == 404, introuvable.text
        assert introuvable.json()["detail"], "Le refus doit dire pourquoi."
        print("  [OK] Lettre hors du registre des documents officiels ; refus explicite.")

    print("E2E relances de facturation : OK")


if __name__ == "__main__":
    asyncio.run(_cleanup())
    shutil.rmtree(TEST_DIR, ignore_errors=True)
    try:
        _migrate()
        asyncio.run(_run())
    finally:
        asyncio.run(_cleanup())
        shutil.rmtree(TEST_DIR, ignore_errors=True)
