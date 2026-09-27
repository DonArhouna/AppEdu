"""Moyennes par semestre, verifiees sur les releves reels de l'institut.

Executable sans pytest :
    .\\\\venv\\\\Scripts\\\\python.exe test_semestre_e2e.py

Ce test ne verifie pas une formule inventee : il **reconstitue le semestre 2 du
releve de l'institut** — UE1.2.1 a UE1.2.7, leurs matieres, leurs notes — et
compare chaque moyenne affichee a celle du document. Si la formule change, ce
test echoue ; et s'il est faux, ce test l'a deja montre.

Les chiffres sont ceux du releve :

    UE1.2.1  HTML/CSS 10/13  CEC 1,00  MEC 12,00
             Langage C 10/15 CEC 2,00  MEC 13,33
             Algorithmique 18/10 CEC 2,00 MEC 12,67   CUE 6  MUE 12,80
    UE1.2.2  Systeme d'Exploitation 10/14 CEC 2,00 MEC 12,67
             Architecture 7/10  CEC 2,00  MEC 9,00    CUE 4  MUE 10,83
    UE1.2.3  Bureautique 17/15 CEC 2,00 MEC 15,67
             Analyse Merise 9/10 CEC 3,00 MEC 9,67    CUE 5  MUE 12,07
    UE1.2.4  Maths Financieres 9/17 CEC 1,00 MEC 14,33
             Maths generales 10/13,5 CEC 2,00 MEC 12,33 CUE 4  MUE 13,00
    UE1.2.5  Comptabilite Generale 16,5/16,5 CEC 2,00 MEC 16,50
                                                       CUE 3  MUE 16,50
    UE1.2.6  Droit 17/7,5 CEC 1,00 MEC 10,67
             Organisation 18/6  CEC 1,00 MEC 10,00     CUE 4  MUE 10,33
    UE1.2.7  Technique d'expression 15/14 CEC 1,00 MEC 14,33
             Anglais 7/15 CEC 2,00 MEC 12,33           CUE 4  MUE 13,00

    Moyenne du semestre : 12,51   Credits : 30,00

Le releve montre aussi que le **devoir pese 1 et l'examen 2** : MEC 12,00
s'obtient par (10x1 + 13x2)/3. Le test utilise donc ces poids, via la
convention d'en-tete ``Devoir:1`` / ``Examen:2`` de l'import.
"""

import asyncio
import gc
import importlib.util
import os
import shutil
import sqlite3
import tempfile
from datetime import date
from pathlib import Path

from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient

TEST_DIR = Path(tempfile.gettempdir()) / "appedu-semestre-e2e"
TEST_DB_PATH = TEST_DIR / "semestre.db"
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

ADMIN_EMAIL = "admin.semestre@ecole-ci.org"
ADMIN_PASSWORD = "Semestre-Admin-2026!"
DEVISE = "XOF"

#: (code UE, libelle UE, CUE, [(matiere, coef UE, devoir, examen, MEC, MUE)])
#: Les moyennes sont celles **affichees** sur le releve.
RELEVE_S2 = [
    (
        "UE1.2.1", "Algorithmique et Langage", 6,
        [
            ("HTML/CSS", 1.0, 10.0, 13.0, 12.00, 12.80),
            ("Langage C", 2.0, 10.0, 15.0, 13.33, None),
            ("Algorithmique", 2.0, 18.0, 10.0, 12.67, None),
        ],
    ),
    (
        "UE1.2.2", "Architecture et systeme", 4,
        [
            ("Systeme d'Exploitation", 2.0, 10.0, 14.0, 12.67, 10.83),
            ("Architecture", 2.0, 7.0, 10.0, 9.00, None),
        ],
    ),
    (
        "UE1.2.3", "Systeme d'information et bases", 5,
        [
            ("Bureautique", 2.0, 17.0, 15.0, 15.67, 12.07),
            ("Analyse Merise", 3.0, 9.0, 10.0, 9.67, None),
        ],
    ),
    (
        "UE1.2.4", "Mathematiques appliquees", 4,
        [
            ("Mathematiques Financieres", 1.0, 9.0, 17.0, 14.33, 13.00),
            ("Mathematiques generales", 2.0, 10.0, 13.5, 12.33, None),
        ],
    ),
    (
        "UE1.2.5", "Comptabilite", 3,
        [("Comptabilite Generale", 2.0, 16.5, 16.5, 16.50, 16.50)],
    ),
    (
        "UE1.2.6", "Environnement economique et juridique", 4,
        [
            ("Droit", 1.0, 17.0, 7.5, 10.67, 10.33),
            ("Organisation d'Entreprises", 1.0, 18.0, 6.0, 10.00, None),
        ],
    ),
    (
        "UE1.2.7", "Outils de communication", 4,
        [
            ("Technique d'expression", 1.0, 15.0, 14.0, 14.33, 13.00),
            ("Anglais", 2.0, 7.0, 15.0, 12.33, None),
        ],
    ),
]

MOYENNE_S2 = 12.51
CREDITS_S2 = 30

#: Le releve du semestre 1, pour le recapitulatif annuel.
RELEVE_S1_MOYENNES = [10.73, 12.08, 11.17, 13.33, 14.83, 12.25, 11.00]
CREDITS_S1 = 30
MOYENNE_S1 = 11.77
MOYENNE_GENERALE = 12.14


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
    command.downgrade(config, "0020_semestres")
    command.upgrade(config, "head")


async def _run() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://semestre-test"
    ) as client:
        setup = await client.post(
            "/api/v1/setup/initialize",
            json={
                "etablissement": {
                    "nom": "Institut Semestre E2E", "code": "SEM-E2E",
                    "adresse": "", "telephone": "", "email": "c@semestre-e2e.org",
                    "pays": "Sénégal", "devise": DEVISE,
                },
                "admin": {
                    "email": ADMIN_EMAIL, "nom": "Admin", "prenom": "Semestre",
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
                    "nom": "Genie Logiciel Semestre", "code": "GLS",
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
                    "nom": "Session Semestre", "code": "SES-SEM",
                    "annee_academique": "2018-2019",
                    "date_debut": "2018-10-01", "date_fin": "2019-07-31",
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
                    "code": "GLS-L1", "nom": "GL Semestre L1",
                    "filiere_id": filiere["id"], "niveau_id": niveau["id"],
                },
                headers=admin,
            )
        ).json()
        etudiant = (
            await client.post(
                "/api/v1/etudiants/",
                json={
                    "nom": "Kane", "prenom": "Harouna", "sexe": "M",
                    "date_naissance": "1994-12-29",
                    "filiere": filiere["nom"], "niveau": niveau["nom"],
                    "classe_id": classe["id"], "session_id": session["id"],
                },
                headers=admin,
            )
        ).json()

        # --- Les deux semestres ---------------------------------------
        repartition = (
            await client.get(
                "/api/v1/academic/semestres/repartition",
                params={"session_id": session["id"]}, headers=admin,
            )
        )
        assert repartition.status_code == 200, repartition.text
        semestres = repartition.json()["semestres"]
        assert [s["numero"] for s in semestres] == [1, 2], semestres
        s1 = next(s for s in semestres if s["numero"] == 1)
        s2 = next(s for s in semestres if s["numero"] == 2)
        print("  [OK] Session creee avec deux semestres : S1, S2.")

        # Le numero est unique dans la session : deux « semestre 1 » rendraient
        # la moyenne par semestre ambigue.
        doublon = await client.post(
            "/api/v1/academic/semestres",
            params={"session_id": session["id"]},
            json={"numero": 1, "libelle": "S1 bis"},
            headers=admin,
        )
        assert doublon.status_code == 409, doublon.text
        assert "existe déjà" in doublon.json()["detail"], doublon.json()

        # Un semestre qui finit avant de commencer est refuse.
        incoherent = await client.post(
            "/api/v1/academic/semestres",
            params={"session_id": session["id"]},
            json={
                "numero": 3, "libelle": "S3",
                "date_debut": "2019-07-01", "date_fin": "2019-01-01",
            },
            headers=admin,
        )
        assert incoherent.status_code == 422, incoherent.text
        print("  [OK] Numero unique refuse ; semestre incoherent refuse.")

        # --- Le rattachement d'une UE a un semestre ---------------------
        # C'est par l'API que l'institut rattache ses UE. Sans cela, une UE
        # creee depuis l'ecran n'appartient a aucun semestre, et la moyenne du
        # semestre ne peut pas la voir.
        ue_creee = await client.post(
            "/api/v1/structure/ues",
            json={
                "nom": "UE de rattachement", "code": "UE-RATT",
                "credits": 3, "coefficient": 1.0, "heures": 50,
                "semestre": "S2", "semestre_id": s2["id"], "niveau": "L1",
                "filiere_id": filiere["id"],
            },
            headers=admin,
        )
        assert ue_creee.status_code == 201, ue_creee.text
        assert ue_creee.json()["semestre_id"] == s2["id"], ue_creee.json()

        # Un semestre inexistant est refuse en nommant le semestre fautif.
        # La cle etrangere l'aurait laisse passer en 500 « IntegrityError »,
        # sans dire lequel — un message que l'institut ne peut pas corriger.
        ue_orpheline = await client.post(
            "/api/v1/structure/ues",
            json={
                "nom": "UE sans semestre", "code": "UE-ORPH",
                "credits": 3, "coefficient": 1.0, "heures": 50,
                "semestre": "S2", "semestre_id": "semestre-inexistant",
                "niveau": "L1", "filiere_id": filiere["id"],
            },
            headers=admin,
        )
        assert ue_orpheline.status_code == 422, ue_orpheline.text
        assert "semestre-inexistant" in ue_orpheline.json()["detail"], (
            ue_orpheline.json()
        )

        # Le rattachement se modifie sans recreer l'UE, et se retire.
        rattachee = await client.put(
            f"/api/v1/structure/ues/{ue_creee.json()['id']}",
            json={"semestre_id": s1["id"]}, headers=admin,
        )
        assert rattachee.status_code == 200, rattachee.text
        assert rattachee.json()["semestre_id"] == s1["id"], rattachee.json()

        # Le listage par semestre se fait a l'identifiant : deux semestres
        # peuvent porter la meme etiquette, et le critere non ambigue est
        # l'identifiant.
        sur_s2 = (
            await client.get(
                "/api/v1/structure/ues", params={"semestre_id": s2["id"]},
                headers=admin,
            )
        ).json()
        assert sur_s2 == [], f"UE attendues sur S2 avant construction : {sur_s2}"

        await client.put(
            f"/api/v1/structure/ues/{ue_creee.json()['id']}",
            json={"semestre_id": s2["id"]}, headers=admin,
        )
        sur_s2 = (
            await client.get(
                "/api/v1/structure/ues", params={"semestre_id": s2["id"]},
                headers=admin,
            )
        ).json()
        assert [ue["code"] for ue in sur_s2] == ["UE-RATT"], sur_s2
        sur_s1 = (
            await client.get(
                "/api/v1/structure/ues", params={"semestre_id": s1["id"]},
                headers=admin,
            )
        ).json()
        assert sur_s1 == [], sur_s1
        print("  [OK] UE rattachee a un semestre, semestre inconnu refuse, listage par semestre.")

        # --- Un enseignement annuel -------------------------------------
        # Definition de l'institut, 26/09 : une matiere annuelle, c'est une
        # matiere que l'on retrouve sur **les deux semestres** et que l'on
        # evalue **sur chacun**. Elle n'appartient donc pas a un semestre
        # unique — et son rattachement a un seul semestre serait ignore a la
        # lecture, en silence. On refuse plutot que d'effacer derriere.
        ue_annuelle = await client.post(
            "/api/v1/structure/ues",
            json={
                "nom": "Expression ecrite", "code": "UE-ANN",
                "credits": 3, "coefficient": 1.0, "heures": 60,
                "regime": "annuelle", "niveau": "L1",
                "filiere_id": filiere["id"],
            },
            headers=admin,
        )
        assert ue_annuelle.status_code == 201, ue_annuelle.text
        corps_annuel = ue_annuelle.json()
        assert corps_annuel["regime"] == "annuelle", corps_annuel
        # Ni semestre, ni etiquette : elle en designe plusieurs.
        assert corps_annuel["semestre"] is None, corps_annuel
        assert corps_annuel["semestre_id"] is None, corps_annuel

        incoherent = await client.post(
            "/api/v1/structure/ues",
            json={
                "nom": "Annuel mal rattache", "code": "UE-ANN2",
                "credits": 3, "coefficient": 1.0, "heures": 60,
                "regime": "annuelle", "semestre_id": s1["id"],
                "niveau": "L1", "filiere_id": filiere["id"],
            },
            headers=admin,
        )
        assert incoherent.status_code == 422, incoherent.text
        assert "annuel" in incoherent.json()["detail"].lower(), incoherent.json()

        # Passer une UE semestrielle en annuelle sans retirer son semestre est
        # refuse aussi : l'etat resultante serait incoherent, et c'est
        # l'etat resultante qu'on verifie.
        bascule = await client.put(
            f"/api/v1/structure/ues/{ue_creee.json()['id']}",
            json={"regime": "annuelle"}, headers=admin,
        )
        assert bascule.status_code == 422, bascule.text

        inconnu = await client.post(
            "/api/v1/structure/ues",
            json={
                "nom": "Regime aberrant", "code": "UE-ANN3",
                "credits": 3, "coefficient": 1.0, "heures": 60,
                "regime": "trimestriel", "niveau": "L1",
                "filiere_id": filiere["id"],
            },
            headers=admin,
        )
        assert inconnu.status_code == 422, inconnu.text
        print("  [OK] Enseignement annuel : sans semestre, rattachement unique refuse.")

        # --- Construction du releve du semestre 2 ----------------------
        from app.models.academic import Inscription  # noqa: F401
        from app.models.pedagogie import Examen, Note
        from app.models.structure import Matiere, Semestre, UniteEnseignement
        from sqlalchemy import select
        import uuid

        fabrique = database.get_sessionmaker_for_tenant()
        async with fabrique() as db:
            for code, nom, cue, matieres in RELEVE_S2:
                ue = UniteEnseignement(
                    id=str(uuid.uuid4()),
                    filiere_id=filiere["id"],
                    nom=nom, code=code,
                    credits=cue, coefficient=1.0, heures=60,
                    semestre="S2", niveau="L1",
                    semestre_id=s2["id"],
                )
                db.add(ue)
                await db.flush()
                for rang, (libelle, cec, devoir, examen, _mec, _mue) in enumerate(matieres, 1):
                    matiere = Matiere(
                        id=str(uuid.uuid4()),
                        ue_id=ue.id, nom=libelle,
                        code=f"{code}-M{rang}",
                        credits=3, coefficient=cec,
                        heures_cm=20, heures_td=10, heures_tp=8,
                    )
                    db.add(matiere)
                    await db.flush()
                    for nom_eval, valeur, type_eval in (
                        ("Devoir", devoir, "CC"),
                        ("Examen", examen, "Examen Final"),
                    ):
                        evaluation = Examen(
                            id=str(uuid.uuid4()), nom=nom_eval,
                            session_id=session["id"], matiere_id=matiere.id,
                            type_examen=type_eval,
                            date_examen=date(2019, 1, 10),
                            duree_minutes=0 if type_eval == "CC" else 120,
                            coefficient=1.0 if type_eval == "CC" else 2.0,
                        )
                        db.add(evaluation)
                        await db.flush()
                        db.add(Note(
                            id=str(uuid.uuid4()),
                            etudiant_id=etudiant["id"],
                            matiere_id=matiere.id,
                            examen_id=evaluation.id,
                            session_id=session["id"],
                            valeur=valeur,
                            coefficient=1.0 if type_eval == "CC" else 2.0,
                        ))
            # Le semestre 1 : une seule UE, avec la moyenne affichee 11,77
            # obtenue en reconstituant les MUE du releve.
            ue1 = UniteEnseignement(
                id=str(uuid.uuid4()), filiere_id=filiere["id"],
                nom="Ue du premier semestre", code="UE1.1.0",
                credits=CREDITS_S1, coefficient=1.0, heures=60,
                semestre="S1", niveau="L1", semestre_id=s1["id"],
            )
            db.add(ue1)
            await db.flush()
            # Une matiere synthetique, reglee pour produire la moyenne voulue.
            matiere1 = Matiere(
                id=str(uuid.uuid4()), ue_id=ue1.id, nom="Ensemble semestre 1",
                code="S1-SYNTH", credits=3, coefficient=1.0,
                heures_cm=0, heures_td=0, heures_tp=0,
            )
            db.add(matiere1)
            await db.flush()
            evaluation1 = Examen(
                id=str(uuid.uuid4()), nom="Moyenne",
                session_id=session["id"], matiere_id=matiere1.id,
                type_examen="Examen Final", date_examen=date(2019, 1, 10),
                duree_minutes=120, coefficient=1.0,
            )
            db.add(evaluation1)
            await db.flush()
            db.add(Note(
                id=str(uuid.uuid4()), etudiant_id=etudiant["id"],
                matiere_id=matiere1.id, examen_id=evaluation1.id,
                session_id=session["id"], valeur=MOYENNE_S1, coefficient=1.0,
            ))
            await db.commit()

        # --- Deux devoirs dans une matiere -----------------------------
        # Regle confirmee par l'institut le 26/09 : « si une matiere a deux
        # devoirs, alors Devoir = (devoir1 + devoir2) / 2 ». Le cas se presente
        # rarement, et il n'a pas d'interet a etre pondere.
        #
        # Cette UE va sur un **semestre 3** cree pour elle, pas sur le
        # semestre 1 : ajouter une matiere a S1 decalerait sa moyenne, que le
        # test verifie contre le releve. Un controle ne doit pas pouvoir
        # fausser un autre controle.
        tiers = (
            await client.post(
                "/api/v1/academic/semestres",
                params={"session_id": session["id"]},
                json={"numero": 3, "libelle": "S3"},
                headers=admin,
            )
        )
        assert tiers.status_code in (200, 201), tiers.text
        s3 = tiers.json()

        async with fabrique() as db:
            ue_devoirs = UniteEnseignement(
                id=str(uuid.uuid4()), filiere_id=filiere["id"],
                nom="UE des deux devoirs", code="UE1.3.D",
                credits=1, coefficient=1.0, heures=60,
                semestre="S3", niveau="L1", semestre_id=s3["id"],
            )
            db.add(ue_devoirs)
            await db.flush()
            matiere_devoirs = Matiere(
                id=str(uuid.uuid4()), ue_id=ue_devoirs.id,
                nom="Matiere aux deux devoirs", code="UE1.3.D-M1",
                credits=3, coefficient=1.0,
                heures_cm=0, heures_td=0, heures_tp=0,
            )
            db.add(matiere_devoirs)
            await db.flush()
            for nom_eval, valeur, type_eval, poids in (
                ("Devoir 1", 8.0, "CC", 1.0),
                ("Devoir 2", 12.0, "CC", 1.0),
                ("Examen", 14.0, "Examen Final", 2.0),
            ):
                evaluation = Examen(
                    id=str(uuid.uuid4()), nom=nom_eval,
                    session_id=session["id"], matiere_id=matiere_devoirs.id,
                    type_examen=type_eval, date_examen=date(2019, 1, 10),
                    duree_minutes=0 if type_eval == "CC" else 120,
                    coefficient=poids,
                )
                db.add(evaluation)
                await db.flush()
                db.add(Note(
                    id=str(uuid.uuid4()), etudiant_id=etudiant["id"],
                    matiere_id=matiere_devoirs.id, examen_id=evaluation.id,
                    session_id=session["id"], valeur=valeur, coefficient=poids,
                ))
            await db.commit()

        async with fabrique() as db:
            from app.services import semestre_service as service

            bilan_devoirs = await service.bilan_semestre(
                db,
                etudiant_id=etudiant["id"],
                session_id=session["id"],
                semestre_id=s3["id"],
            )
        assert bilan_devoirs.porte_recapitulatif is False, (
            "Le semestre 3 est impair : il ne doit pas porter de recapitulatif."
        )
        matiere_test = bilan_devoirs.unites[0].matieres[0]
        assert matiere_test.mcc == 10.0, (
            f"MCC calcule {matiere_test.mcc} au lieu de 10,00. La regle est la "
            "moyenne simple des deux devoirs : (8 + 12) / 2. Une ponderation "
            "donnerait autre chose — et l'institut n'en demande pas."
        )
        assert matiere_test.exam == 14.0, matiere_test.exam
        # Le MEC, lui, pondere : (8x1 + 12x1 + 14x2) / 4 = 48/4 = 12,00.
        assert matiere_test.mec == 12.0, (
            f"MEC calcule {matiere_test.mec} au lieu de 12,00 : la ponderation "
            "par coefficient ne s'applique pas au niveau du groupe."
        )
        assert len(matiere_test.evaluations) == 3, matiere_test.evaluations
        print("  [OK] Deux devoirs : MCC = moyenne simple du groupe, MEC pondere.")

        # --- Verification du calcul -----------------------------------
        from app.services import semestre_service as service

        async with fabrique() as db:
            bilan = await service.bilan_semestre(
                db,
                etudiant_id=etudiant["id"],
                session_id=session["id"],
                semestre_id=s2["id"],
            )

        assert len(bilan.unites) == len(RELEVE_S2), (
            f"{len(RELEVE_S2)} UE attendues, {len(bilan.unites)} trouvees : "
            f"{[ue.code for ue in bilan.unites]}"
        )

        for (code, _nom, cue, matieres), ue in zip(RELEVE_S2, bilan.unites):
            assert ue.code == code, f"{ue.code} au lieu de {code}"
            assert ue.cue == cue, (
                f"{code} : CUE {ue.cue} au lieu de {cue}. Le CUE est le credit "
                "propre de l'UE, pas la somme des CEC."
            )
            for (libelle, cec, _devoir, _examen, mec, mue), m in zip(matieres, ue.matieres):
                assert m.nom == libelle, f"{code}/{libelle} : trouvee {m.nom}"
                assert m.cec == cec, f"{code}/{libelle} : CEC {m.cec} au lieu de {cec}"
                assert m.mec == mec, (
                    f"{code}/{libelle} : MEC calcule {m.mec} au lieu de {mec} "
                    "affiche sur le releve. Le devoir pese 1, l'examen 2."
                )
            if matieres[0][5] is not None:
                assert ue.mue == matieres[0][5], (
                    f"{code} : MUE calcule {ue.mue} au lieu de "
                    f"{matieres[0][5]} affiche sur le releve."
                )

        assert bilan.moyenne == MOYENNE_S2, (
            f"Moyenne du semestre {bilan.moyenne} au lieu de {MOYENNE_S2} "
            "affichee sur le releve."
        )
        assert bilan.credits_prevus == CREDITS_S2, bilan.credits_prevus
        print("  [OK] MEC, MUE et moyenne du semestre : conformes au releve.")

        # --- Le recapitulatif, sur le semestre pair seulement ----------
        assert bilan.porte_recapitulatif is True, (
            "Le semestre 2 doit porter le recapitulatif annuel."
        )
        async with fabrique() as db:
            bilan1 = await service.bilan_semestre(
                db,
                etudiant_id=etudiant["id"],
                session_id=session["id"],
                semestre_id=s1["id"],
            )
        assert bilan1.porte_recapitulatif is False, (
            "Le semestre 1 ne doit pas porter de recapitulatif annuel : il "
            "n'a pas d'annee complete a resumer."
        )
        assert bilan1.moyenne == MOYENNE_S1, bilan1.moyenne

        async with fabrique() as db:
            recap = await service.recap_annuel(
                db,
                etudiant_id=etudiant["id"],
                session_id=session["id"],
                semestre_id=s2["id"],
            )
        assert recap is not None, "Le semestre 2 doit porter un recapitulatif."
        assert recap["credits_precedent"] == CREDITS_S1, recap["credits_precedent"]
        assert recap["credits_courant"] == CREDITS_S2, recap["credits_courant"]
        assert recap["credits_total"] == CREDITS_S1 + CREDITS_S2, recap["credits_total"]
        assert recap["moyenne_precedente"] == MOYENNE_S1, recap["moyenne_precedente"]
        assert recap["moyenne_courante"] == MOYENNE_S2, recap["moyenne_courante"]
        assert recap["moyenne_annuelle"] == MOYENNE_GENERALE, (
            f"Moyenne generale {recap['moyenne_annuelle']} au lieu de "
            f"{MOYENNE_GENERALE} affichee sur le releve."
        )

        # Sur le semestre impair, pas de recapitulatif : le rendre vide
        # laisserait croire que l'etudiant n'a pas d'historique.
        async with fabrique() as db:
            recap1 = await service.recap_annuel(
                db,
                etudiant_id=etudiant["id"],
                session_id=session["id"],
                semestre_id=s1["id"],
            )
        assert recap1 is None, (
            "Le semestre 1 a produit un recapitulatif alors qu'il ne doit pas "
            "en porter : l'absence serait lue comme un historique manquant."
        )
        print("  [OK] Recapitulatif : sur le semestre pair seulement, moyenne annuelle conforme.")

        # --- Un enseignement annuel note sur chaque semestre -----------
        # 3 credits, notes **12 en S1** et **15 en S2** : deux evaluations
        # reelles pour une seule matiere annuelle.
        #
        # Ce bloc vient apres les verifications de fidelite au releve,
        # volontairement : l'enseignement annuel s'ajoute aux credits de chaque
        # semestre, et les controles precedents comparent 30 credits et 12,14.
        # Ils trouveraient fausses des valeurs qui n'ont pas change.
        #
        # Le test le plus utile ici est le **pairs** : une 12 et une 15
        # fusionnees donneraient 13,50 sur les deux semestres. Affirmer 12 puis
        # 15, c'est donc exclure la fusion des deux notes — l'erreur exacte que
        # ferait un moteur qui ignorerait le semestre d'une note.
        async with fabrique() as db:
            from app.models.structure import Matiere as _Matiere

            matiere_annuelle = _Matiere(
                id=str(uuid.uuid4()), ue_id=corps_annuel["id"],
                nom="Expression ecrite", code="UE-ANN-M1",
                credits=3, coefficient=1.0,
                heures_cm=0, heures_td=0, heures_tp=60,
            )
            db.add(matiere_annuelle)
            await db.flush()
            for semestre_id, valeur in ((s1["id"], 12.0), (s2["id"], 15.0)):
                evaluation = Examen(
                    id=str(uuid.uuid4()),
                    nom=f"Devoir S{semestre_id[-1]}",
                    session_id=session["id"], matiere_id=matiere_annuelle.id,
                    type_examen="CC", date_examen=date(2019, 1, 10),
                    duree_minutes=0, coefficient=1.0,
                )
                db.add(evaluation)
                await db.flush()
                db.add(Note(
                    id=str(uuid.uuid4()), etudiant_id=etudiant["id"],
                    matiere_id=matiere_annuelle.id, examen_id=evaluation.id,
                    session_id=session["id"], semestre_id=semestre_id,
                    valeur=valeur, coefficient=1.0,
                ))
            await db.commit()

        async with fabrique() as db:
            from app.services import semestre_service as service

            bilans_annuels = {}
            for cle, semestre_ref in (("S1", s1), ("S2", s2)):
                bilans_annuels[cle] = await service.bilan_semestre(
                    db, etudiant_id=etudiant["id"],
                    session_id=session["id"], semestre_id=semestre_ref["id"],
                )

        for cle, attendue in (("S1", 12.0), ("S2", 15.0)):
            bilan = bilans_annuels[cle]
            annuelle = next(
                (ue for ue in bilan.unites if ue.code == "UE-ANN"), None
            )
            assert annuelle is not None, (
                f"L'enseignement annuel ne figure pas sur le bulletin de {cle}. "
                f"Un enseignement annuel se retrouve sur **chaque** semestre : "
                f"UE trouvees = {[ue.code for ue in bilan.unites]}"
            )
            assert annuelle.annuelle is True, (
                f"Le bulletin de {cle} ne signale pas l'enseignement comme "
                "annuel. Deux UE identiques sur deux bulletins meritent une "
                "explication."
            )
            assert annuelle.mue == attendue, (
                f"MUE de l'enseignement annuel en {cle} : {annuelle.mue} au "
                f"lieu de {attendue}. Les deux notes (12 et 15) ont ete "
                "fusionnees, ou la note de l'autre semestre a eteemployee."
            )
            # Ses 3 credits entrent dans le total du semestre ou elle figure.
            # Le total se verifie par le chiffre, pas par une recherche : c'est
            # ce que l'agent lit sur le bulletin.
            assert bilan.credits_prevus == CREDITS_S2 + 3, (
                f"Credits du semestre {cle} : {bilan.credits_prevus} au lieu de "
                f"{CREDITS_S2 + 3}. Les 3 credits de l'enseignement annuel "
                "manquent, ou y sont comptes deux fois."
            )
            assert bilan.annuelles_sans_note == [], bilan.annuelles_sans_note

        # La presence sur les deux semestres double les credits de l'annee :
        # 30 + 3 + 30 + 3 = 66. C'est la consequence directe de la definition,
        # et c'est a l'institut de decider s'il inscrit 3 ou 1,5 par semestre —
        # le moteur ne le suppose pas.
        async with fabrique() as db:
            recap_annuel = await service.recap_annuel(
                db, etudiant_id=etudiant["id"],
                session_id=session["id"], semestre_id=s2["id"],
            )
        assert recap_annuel is not None
        assert recap_annuel["credits_total"] == 66, recap_annuel["credits_total"]
        print("  [OK] Enseignement annuel : 12 en S1, 15 en S2, jamais fusionnes.")

        # --- Un annuel entierement note ailleurs reste signale ------------
        # Une UE annuelle dont toutes les notes sont en S2 ne figure pas en
        # S1. C'est correct — mais le silence se lirait comme une UE
        # semestrielle disparue. Elle est donc annoncee, avec la raison.
        async with fabrique() as db:
            ue_369 = UniteEnseignement(
                id=str(uuid.uuid4()), filiere_id=filiere["id"],
                nom="Projet", code="UE-369", credits=3, coefficient=1.0,
                heures=60, semestre=None, regime="annuelle", niveau="L1",
            )
            db.add(ue_369)
            await db.flush()
            matiere_369 = _Matiere(
                id=str(uuid.uuid4()), ue_id=ue_369.id, nom="Projet",
                code="UE-369-M1", credits=3, coefficient=1.0,
                heures_cm=0, heures_td=0, heures_tp=60,
            )
            db.add(matiere_369)
            await db.flush()
            evaluation_369 = Examen(
                id=str(uuid.uuid4()), nom="Soutenance",
                session_id=session["id"], matiere_id=matiere_369.id,
                type_examen="Examen Final", date_examen=date(2019, 6, 15),
                duree_minutes=120, coefficient=1.0,
            )
            db.add(evaluation_369)
            await db.flush()
            db.add(Note(
                id=str(uuid.uuid4()), etudiant_id=etudiant["id"],
                matiere_id=matiere_369.id, examen_id=evaluation_369.id,
                session_id=session["id"], semestre_id=s2["id"],
                valeur=14.0, coefficient=1.0,
            ))
            await db.commit()

        async with fabrique() as db:
            bilan_s1_final = await service.bilan_semestre(
                db, etudiant_id=etudiant["id"],
                session_id=session["id"], semestre_id=s1["id"],
            )
        codes_annuels_sans_note = [e["code"] for e in bilan_s1_final.annuelles_sans_note]
        assert "UE-369" in codes_annuels_sans_note, (
            "L'enseignement annuel UE-369 n'a de note qu'en S2, et le bulletin "
            "de S1 ne le signale pas : son absence se lirait comme une UE "
            "semestrielle disparue."
        )
        print("  [OK] Enseignement annuel sans note ici : signale, pas muet.")

        # --- Le barème de mentions ------------------------------------
        from app.services.deliberation_service import BAREME_REPLI, mention_pour

        # Le barème de repli — celui que l'institut voit quand aucune règle
        # n'est confirmée — et celui que la migration 0021 corrige doivent
        # être le même. Sur une instance neuve, ``regles_deliberation`` est vide :
        # c'est le repli qui alimente la confirmation, pas la migration. Un
        # repli resté ancien ressusciterait le défaut, sans bruit, jusqu'à la
        # première confirmation. Les deux listes sont dupliquées par
        # necessity — une migration ne peut pas importer le service — donc rien
        # d'autre ne les relie. Ce controle est le lien.
        spec = importlib.util.spec_from_file_location(
            "m0021",
            Path(__file__).resolve().parent
            / "alembic" / "versions" / "0021_bareme_mentions.py",
        )
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        assert BAREME_REPLI["bareme_mentions"] == migration.BAREME_CORRECT, (
            "Le barème de repli et celui de la migration 0021 divergent : la "
            f"confirmation écrirait {BAREME_REPLI['bareme_mentions']} alors que "
            f"la migration corrige {migration.BAREME_CORRECT}."
        )
        # L'ordre est significatif : le module applique le premier seuil atteint
        # en descendant. Un barème trié à l'envers attribuerait « Insuffisant »
        # à tout le monde.
        seuils = [e["seuil_min"] for e in BAREME_REPLI["bareme_mentions"]]
        assert seuils == sorted(seuils, reverse=True), (
            f"Barème hors d'ordre ({seuils}) : la mention retenue serait la "
            "première trouvée, pas la plus élevée atteinte."
        )
        print("  [OK] Barème de repli aligné sur la migration 0021.")

        bareme = BAREME_REPLI["bareme_mentions"]
        for moyenne, attendue in (
            (16.50, "Très Bien"), (15.67, "Bien"), (14.33, "Bien"),
            (12.33, "Assez Bien"), (12.00, "Assez Bien"), (10.67, "Passable"),
            (10.00, "Passable"), (9.67, "Insuffisant"), (9.00, "Insuffisant"),
            (3.00, "Insuffisant"),
        ):
            obtenue = mention_pour(moyenne, bareme)
            assert obtenue == attendue, (
                f"{moyenne} : mention {obtenue!r} au lieu de {attendue!r}. "
                "Sous l'ancien barème, 3/20 s'affichait « Passable » : une "
                "affirmation fausse sur un document officiel."
            )
        print("  [OK] Bareme de mentions conforme aux releves, « Insuffisant » compris.")

    print("E2E moyennes par semestre : OK")


if __name__ == "__main__":
    asyncio.run(_cleanup())
    shutil.rmtree(TEST_DIR, ignore_errors=True)
    try:
        _migrate()
        asyncio.run(_run())
    finally:
        asyncio.run(_cleanup())
        shutil.rmtree(TEST_DIR, ignore_errors=True)
