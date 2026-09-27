"""E2E de la deliberation persistee (SQLite isole).

Executable sans pytest :
    .\\venv\\Scripts\\python.exe test_deliberation_e2e.py

La base est un fichier temporaire sous %TEMP% : aucune instance locale n'est
touchee, aucun reset n'est effectue.

Le scenario verifie la chaine complete, et surtout les **garde-fous** :

1. migration jusqu'a 0017 et regles de depart **non confirmees** ;
2. confirmation du reglement par l'institut, avec trace d'audit ;
3. ouverture d'une seance de jury : president et membres sont saisis, jamais
   devines ; les regles sont figees dans la seance ;
4. refus d'une seconde seance pour la meme promotion ;
5. le moteur **propose**, il ne decide pas : la proposition est calculee a
   partir des notes reellement enregistrees ;
6. le jury **consigne** sa decision, avec la proposition conservee a cote ;
7. un ecart avec la proposition exige un motif ;
8. mention hors bareme refusee ; decision contradictoire refusee ;
9. cloture refusee tant qu'un inscrit n'a pas de decision ;
10. seance close : les decisions deviennent immuables ;
11. proces-verbal : PDF reellement produit, avec la composition du jury ;
12. **attestation de reussite** : refusee avant cloture, puis emise apres
    decision « Admis » sur seance close ; toujours refusee pour un etudiant
    non admis.

Le point 13 est la raison d'etre de tout l'increment : une moyenne favorable
ne fonde aucun droit tant que le jury n'a pas arrete son verdict.
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

TEST_DIR = Path(tempfile.gettempdir()) / "appedu-deliberation-e2e"
TEST_DB_PATH = TEST_DIR / "deliberation.db"
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

ADMIN_EMAIL = "admin.deliberation@ecole-ci.org"
ADMIN_PASSWORD = "Deliberation-Admin-2026!"
TEACHER_EMAIL = "enseignant.deliberation@ecole-ci.org"
TEACHER_PASSWORD = "Deliberation-Teacher-2026!"

DATE_SEANCE = "2026-07-15"
PRESIDENT = "Professeur Directeur Bakary Traore"
MEMBRES = [
    {"nom": "Docteur Aminata Cisse", "qualite": "Professeur de ranks"},
    {"nom": "Maitre Jean Kouassi", "qualite": "Secretaire du jury"},
]


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
    command.upgrade(config, "0016_config_institutionnelle")
    command.upgrade(config, "head")
    # Aller-retour : la migration doit etre reversible sans residue.
    command.downgrade(config, "0016_config_institutionnelle")
    command.upgrade(config, "head")


async def _login(client: AsyncClient, email: str, password: str) -> dict:
    reponse = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert reponse.status_code == 200, reponse.text
    return {"Authorization": f"Bearer {reponse.json()['access_token']}"}


async def _run() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://deliberation-test"
    ) as client:
        # ------------------------------------------------------------------
        # 1. Mise en place
        # ------------------------------------------------------------------
        setup = await client.post(
            "/api/v1/setup/initialize",
            json={
                "etablissement": {
                    "nom": "Institut Deliberation E2E",
                    "code": "DEL-E2E",
                    "adresse": "",
                    "telephone": "",
                    "email": "contact@deliberation-e2e.org",
                    "devise": "XOF",
                },
                "admin": {
                    "email": ADMIN_EMAIL, "nom": "Admin", "prenom": "Deliberation",
                    "password": ADMIN_PASSWORD,
                },
            },
        )
        assert setup.status_code in (200, 201), f"{setup.status_code} {setup.text}"
        admin = await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)

        cree = await client.post(
            "/api/v1/users/",
            json={
                "email": TEACHER_EMAIL, "nom": "Enseignant", "prenom": "Deliberation",
                "role": "ENSEIGNANT", "password": TEACHER_PASSWORD,
            },
            headers=admin,
        )
        assert cree.status_code == 201, cree.text
        enseignant = await _login(client, TEACHER_EMAIL, TEACHER_PASSWORD)

        # Socle academique : une filiere, une UE, une matiere, une classe.
        filiere = (
            await client.post(
                "/api/v1/structure/filieres",
                json={
                    "nom": "Genie Logiciel Delib", "code": "GLD", "duree": 3,
                    "diplome": "Licence", "niveau": "L1",
                },
                headers=admin,
            )
        ).json()

        session = (
            await client.post(
                "/api/v1/sessions/",
                json={
                    "nom": "Session Delib 2026", "code": "SES-DEL",
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
                    "code": "GLD-L1", "nom": "Genie Logiciel L1",
                    "filiere_id": filiere["id"], "niveau_id": niveau["id"],
                },
                headers=admin,
            )
        ).json()

        # Deux UE : une forte (4 ECTS) et une faible (2 ECTS).
        ue_forte = (
            await client.post(
                "/api/v1/structure/ues",
                json={
                    "nom": "UE Fondamentale", "code": "UEF", "credits": 4,
                    "coefficient": 2, "heures": 60, "filiere_id": filiere["id"],
                    "niveau": "L1", "semestre": "S1",
                },
                headers=admin,
            )
        ).json()
        ue_faible = (
            await client.post(
                "/api/v1/structure/ues",
                json={
                    "nom": "UE Complementaire", "code": "UEC", "credits": 2,
                    "coefficient": 1, "heures": 30, "filiere_id": filiere["id"],
                    "niveau": "L1", "semestre": "S1",
                },
                headers=admin,
            )
        ).json()
        matiere_forte = (
            await client.post(
                "/api/v1/structure/matieres",
                json={
                    "nom": "Algorithmes", "code": "ALG", "credits": 3, "coefficient": 1,
                    "heures_cm": 20, "heures_td": 10, "heures_tp": 5,
                    "ue_id": ue_forte["id"],
                },
                headers=admin,
            )
        ).json()
        matiere_faible = (
            await client.post(
                "/api/v1/structure/matieres",
                json={
                    "nom": "Communication", "code": "COM", "credits": 1, "coefficient": 1,
                    "heures_cm": 10, "heures_td": 5, "heures_tp": 0,
                    "ue_id": ue_faible["id"],
                },
                headers=admin,
            )
        ).json()

        async def _creer_etudiant(matricule: str, note_forte: float, note_faible: float) -> dict:
            etudiant = (
                await client.post(
                    "/api/v1/etudiants/",
                    json={
                        "nom": "Etudiant", "prenom": matricule.split("-")[-1],
                        "matricule": matricule, "sexe": "M",
                        "date_naissance": "2004-01-15",
                        "filiere": "Genie Logiciel Delib", "niveau": "L1",
                        "classe_id": classe["id"], "session_id": session["id"],
                    },
                    headers=admin,
                )
            ).json()
            for matiere, valeur in (
                (matiere_forte, note_forte),
                (matiere_faible, note_faible),
            ):
                note = await client.post(
                    "/api/v1/pedagogie/notes",
                    json={
                        "etudiant_id": etudiant["id"], "matiere_id": matiere["id"],
                        "valeur": valeur, "coefficient": 1, "session_id": session["id"],
                    },
                    headers=admin,
                )
                assert note.status_code in (200, 201), note.text
            return etudiant

        # Trois profils de resultat : tres bon, moyen, et eliminatoire.
        excellent = await _creer_etudiant("DEL-0001", 17.0, 15.0)
        moyen = await _creer_etudiant("DEL-0002", 11.0, 11.0)
        elimine = await _creer_etudiant("DEL-0003", 5.0, 6.0)

        # ------------------------------------------------------------------
        # 2. Regles de depart non confirmees
        # ------------------------------------------------------------------
        regles = await client.get("/api/v1/deliberation/regles", headers=admin)
        assert regles.status_code == 200, regles.text
        contenu_regles = regles.json()
        assert contenu_regles["seuil_validation_moyenne"] == 10.0, contenu_regles
        assert contenu_regles["confirmee"] is False, (
            "Les regles de depart ne doivent pas se declarer confirmees : "
            f"{contenu_regles}"
        )
        print("  [OK] Regles de depart presentes et explicitement non confirmees.")

        # ------------------------------------------------------------------
        # 3. L'institut confirme son reglement
        # ------------------------------------------------------------------
        confirme = await client.put(
            "/api/v1/deliberation/regles",
            json={
                "seuil_validation_moyenne": 10.0,
                "seuil_eliminatoire": 7.0,
                "seuil_rattrapage_minimale": 8.5,
                "seuil_passage_conditionnel_ects": 18,
                "compensation_autorisee": True,
                "bareme_mentions": [
                    {"libelle": "Très Bien", "seuil_min": 16.0},
                    {"libelle": "Bien", "seuil_min": 14.0},
                    {"libelle": "Assez Bien", "seuil_min": 12.0},
                    {"libelle": "Passable", "seuil_min": 0.0},
                ],
                "confirme": True,
            },
            headers=admin,
        )
        assert confirme.status_code == 200, confirme.text
        assert confirme.json()["confirmee"] is True, confirme.json()
        assert confirme.json()["confirme_par"] == ADMIN_EMAIL, confirme.json()

        # Un bareme incoherent est refuse, avec la raison.
        invalide = await client.put(
            "/api/v1/deliberation/regles",
            json={
                "seuil_validation_moyenne": 10.0,
                "seuil_eliminatoire": 7.0,
                "seuil_rattrapage_minimale": 12.0,  # > seuil de validation
                "seuil_passage_conditionnel_ects": 18,
                "compensation_autorisee": True,
                "bareme_mentions": [{"libelle": "Passable", "seuil_min": 0.0}],
                "confirme": True,
            },
            headers=admin,
        )
        assert invalide.status_code == 422, invalide.text
        print("  [OK] Reglement confirme par l'institut ; bareme incoherent refuse.")

        # ------------------------------------------------------------------
        # 4. Ouverture de la seance de jury
        # ------------------------------------------------------------------
        seance = await client.post(
            "/api/v1/deliberation/",
            json={
                "classe_id": classe["id"], "session_id": session["id"],
                "date_deliberation": DATE_SEANCE, "lieu": "Salle du conseil",
                "president": PRESIDENT, "membres": MEMBRES,
            },
            headers=admin,
        )
        assert seance.status_code == 201, seance.text
        seance_id = seance.json()["id"]
        corps_seance = seance.json()
        assert corps_seance["statut"] == "brouillon", corps_seance
        assert corps_seance["president"] == PRESIDENT, corps_seance
        assert len(corps_seance["membres"]) == 2, corps_seance
        # Les regles sont figees dans la seance.
        assert corps_seance["regles"]["seuil_validation_moyenne"] == 10.0, corps_seance
        assert corps_seance["regles"]["confirmee"] is True, corps_seance
        print("  [OK] Seance ouverte : jury saisi, regles figees.")

        # President obligatoire, membres obligatoires.
        sans_president = await client.post(
            "/api/v1/deliberation/",
            json={
                "classe_id": classe["id"], "session_id": session["id"],
                "date_deliberation": DATE_SEANCE, "president": "  ",
                "membres": MEMBRES,
            },
            headers=admin,
        )
        assert sans_president.status_code == 422, sans_president.text

        # Seance inverseuse refusee : deux PV contradictoires ne coexistent pas.
        doublon = await client.post(
            "/api/v1/deliberation/",
            json={
                "classe_id": classe["id"], "session_id": session["id"],
                "date_deliberation": DATE_SEANCE, "president": PRESIDENT,
                "membres": MEMBRES,
            },
            headers=admin,
        )
        assert doublon.status_code == 422, doublon.text
        assert "existe deja" in doublon.json()["detail"], doublon.json()
        print("  [OK] Seance sans president refusee ; seconde seance refusee.")

        # ------------------------------------------------------------------
        # 5. Le moteur propose, il ne decide pas
        # ------------------------------------------------------------------
        detail = await client.get(f"/api/v1/deliberation/{seance_id}", headers=admin)
        assert detail.status_code == 200, detail.text
        propositions = {p["matricule"]: p for p in detail.json()["propositions"]}
        assert len(propositions) == 3, list(propositions)

        prop_excellent = propositions["DEL-0001"]
        # 4 ECTS a 17 et 2 ECTS a 15 -> (17*4 + 15*2)/6 = 16,33
        assert prop_excellent["moyenne_generale"] == 16.33, prop_excellent
        assert prop_excellent["ects_total"] == 6, prop_excellent
        assert prop_excellent["proposition_statut"] == "Admis", prop_excellent
        assert prop_excellent["proposition_mention"] == "Très Bien", prop_excellent
        # Aucune decision consignee : le moteur n'a pas decide.
        assert prop_excellent["decision_statut"] is None, prop_excellent

        prop_elimine = propositions["DEL-0003"]
        assert prop_elimine["proposition_statut"] == "Rattrapage", prop_elimine
        assert prop_elimine["notes_eliminatoires"], prop_elimine
        print("  [OK] Propositions calculees sur les notes reelles ; aucune decision prise.")

        # ------------------------------------------------------------------
        # 6. Le jury consigne ses decisions
        # ------------------------------------------------------------------
        # 6a. Un etudiant sans aucune decision : l'attestation est refusee.
        refuse_premature = await client.post(
            f"/api/v1/documents/etudiants/{excellent['id']}",
            json={"type_document": "attestation_reussite", "session_id": session["id"]},
            headers=admin,
        )
        assert refuse_premature.status_code == 422, refuse_premature.text

        # 6b. Decision conforme a la proposition : aucun motif exige.
        admis = await client.post(
            f"/api/v1/deliberation/{seance_id}/decisions",
            params={"etudiant_id": excellent["id"]},
            json={"statut": "Admis", "mention": "Très Bien"},
            headers=admin,
        )
        assert admis.status_code == 201, admis.text
        assert admis.json()["proposition_statut"] == "Admis", admis.json()
        assert admis.json()["ecart"] is False, admis.json()
        assert admis.json()["moyenne_generale"] == 16.33, admis.json()

        rattrapage = await client.post(
            f"/api/v1/deliberation/{seance_id}/decisions",
            params={"etudiant_id": elimine["id"]},
            json={"statut": "Rattrapage", "mention": "Rattrapage"},
            headers=admin,
        )
        assert rattrapage.status_code == 201, rattrapage.text

        # ------------------------------------------------------------------
        # ------------------------------------------------------------------
        # 7. Cloture refusee tant qu'un inscrit n'a pas de decision
        # ------------------------------------------------------------------
        # Deux decisions sur trois : DEL-0002 n'a pas encore ete statue.
        # Clore maintenant laisserait cet etudiant sans verdict, et
        # l'attestation de reussite ne pourrait pas dire s'il a ete examine.
        cloture_incomplete = await client.post(
            f"/api/v1/deliberation/{seance_id}/cloturer",
            json={"confirmation": "arreter"},
            headers=admin,
        )
        assert cloture_incomplete.status_code == 422, cloture_incomplete.text
        assert "DEL-0002" in cloture_incomplete.json()["detail"], (
            f"Le refus doit nommer l'etudiant sans decision : "
            f"{cloture_incomplete.json()['detail']}"
        )
        print("  [OK] Cloture refusee tant qu'un inscrit n'a pas de decision.")

        # ------------------------------------------------------------------
        # 8. Un ecart exige un motif
        # ------------------------------------------------------------------
        sans_motif = await client.post(
            f"/api/v1/deliberation/{seance_id}/decisions",
            params={"etudiant_id": moyen["id"]},
            # Le moteur propose « Admis » (11 et 11 -> moyenne 11) ; le jury
            # decide « Rattrapage » sans dire pourquoi.
            json={"statut": "Rattrapage", "mention": "Rattrapage"},
            headers=admin,
        )
        assert sans_motif.status_code == 422, sans_motif.text
        assert "motive" in sans_motif.json()["detail"].lower(), sans_motif.json()

        avec_motif = await client.post(
            f"/api/v1/deliberation/{seance_id}/decisions",
            params={"etudiant_id": moyen["id"]},
            json={
                "statut": "Rattrapage", "mention": "Rattrapage",
                "motif_ecart": (
                    "Resultats de la seconde seance ecrits apres la tenue de "
                    "la seance ; le jury a statue sur les premieres notes."
                ),
            },
            headers=admin,
        )
        assert avec_motif.status_code == 201, avec_motif.text
        assert avec_motif.json()["ecart"] is True, avec_motif.json()
        assert avec_motif.json()["motif_ecart"], avec_motif.json()
        print("  [OK] Ecart du jury exige un motif ; motif consigne.")

        # ------------------------------------------------------------------
        # 9. Decisions incoherentes refusees
        # ------------------------------------------------------------------
        mention_hors_bareme = await client.post(
            f"/api/v1/deliberation/{seance_id}/decisions",
            params={"etudiant_id": excellent["id"]},
            json={"statut": "Admis", "mention": "Excellent"},
            headers=admin,
        )
        assert mention_hors_bareme.status_code == 422, mention_hors_bareme.text
        assert "bareme" in mention_hors_bareme.json()["detail"].lower()

        mention_incoherente = await client.post(
            f"/api/v1/deliberation/{seance_id}/decisions",
            params={"etudiant_id": excellent["id"]},
            json={"statut": "Rattrapage", "mention": "Très Bien"},
            headers=admin,
        )
        assert mention_incoherente.status_code == 422, mention_incoherente.text
        print("  [OK] Mention hors bareme et mention incoherente refusees.")

        # L'enseignant n'a pas le droit de consigner de decision.
        refuse_enseignant = await client.post(
            f"/api/v1/deliberation/{seance_id}/decisions",
            params={"etudiant_id": excellent["id"]},
            json={"statut": "Admis", "mention": "Très Bien"},
            headers=enseignant,
        )
        assert refuse_enseignant.status_code == 403, refuse_enseignant.text
        print("  [OK] Enseignant refuse de consigner une decision.")

        # ------------------------------------------------------------------
        # 10. Cloture du verdict
        # ------------------------------------------------------------------
        # Confirmation obligatoire : la cloture est irreversible.
        sans_confirmation = await client.post(
            f"/api/v1/deliberation/{seance_id}/cloturer",
            json={"confirmation": "oui"},
            headers=admin,
        )
        assert sans_confirmation.status_code == 422, sans_confirmation.text
        assert "irreversible" in sans_confirmation.json()["detail"].lower()

        cloture = await client.post(
            f"/api/v1/deliberation/{seance_id}/cloturer",
            json={"confirmation": "arreter"},
            headers=admin,
        )
        assert cloture.status_code == 200, cloture.text
        assert cloture.json()["statut"] == "close", cloture.json()
        print("  [OK] Seance close apres decision de chaque inscrit.")

        # ------------------------------------------------------------------
        # 11. Seance close : les decisions sont immuables
        # ------------------------------------------------------------------
        modification = await client.post(
            f"/api/v1/deliberation/{seance_id}/decisions",
            params={"etudiant_id": moyen["id"]},
            json={
                "statut": "Admis", "mention": "Passable",
                "motif_ecart": "Changement d'avis apres cloture.",
            },
            headers=admin,
        )
        assert modification.status_code == 422, modification.text
        assert "close" in modification.json()["detail"].lower(), modification.json()
        print("  [OK] Decision modifiable refusee apres cloture.")

        # ------------------------------------------------------------------
        # 12. Proces-verbal
        # ------------------------------------------------------------------
        pv = await client.get(
            f"/api/v1/deliberation/{seance_id}/proces-verbal", headers=admin
        )
        assert pv.status_code == 200, pv.text
        assert pv.content.startswith(b"%PDF"), "Le PV doit etre un vrai PDF."
        assert len(pv.content) > 2000, len(pv.content)
        assert "attachment" in pv.headers.get("content-disposition", ""), pv.headers
        print(f"  [OK] Proces-verbal produit ({len(pv.content)} octets).")

        # ------------------------------------------------------------------
        # 13. Attestation de reussite : le moment de verite
        # ------------------------------------------------------------------
        # L'etudiant admis, sur une seance close, obtient l'attestation.
        attestation = await client.post(
            f"/api/v1/documents/etudiants/{excellent['id']}",
            json={"type_document": "attestation_reussite", "session_id": session["id"]},
            headers=admin,
        )
        assert attestation.status_code == 201, attestation.text
        document = attestation.json()
        # L'instantane conserve la decision : c'est elle qui est attestee.
        instantane = document["donnees"]["deliberation"]
        assert instantane, document["donnees"]
        assert instantane["statut"] == "Admis", instantane
        assert instantane["mention"] == "Très Bien", instantane
        assert instantane["president"] == PRESIDENT, instantane
        assert instantane["moyenne_generale"] == 16.33, instantane

        pdf = await client.get(
            f"/api/v1/documents/{document['id']}/telecharger", headers=admin
        )
        assert pdf.status_code == 200, pdf.status_code
        assert pdf.content.startswith(b"%PDF"), "L'attestation doit etre un PDF."

        # Un etudiant non admis, meme sur seance close, reste sans attestation.
        for etudiant in (elimine, moyen):
            refuse = await client.post(
                f"/api/v1/documents/etudiants/{etudiant['id']}",
                json={
                    "type_document": "attestation_reussite",
                    "session_id": session["id"],
                },
                headers=admin,
            )
            assert refuse.status_code == 422, (
                f"Une attestation ne doit pas etre emise pour un etudiant non "
                f"admis ({etudiant['matricule']}) : {refuse.text}"
            )
        print("  [OK] Attestation emise pour l'admis, refusee pour les autres.")

    print("E2E deliberation : OK")


if __name__ == "__main__":
    asyncio.run(_cleanup())
    shutil.rmtree(TEST_DIR, ignore_errors=True)
    try:
        _migrate()
        asyncio.run(_run())
    finally:
        asyncio.run(_cleanup())
        shutil.rmtree(TEST_DIR, ignore_errors=True)
