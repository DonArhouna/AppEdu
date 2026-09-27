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


def _ue(code: str):
    """L'UE du releve portant ce code."""

    for entree in RELEVE_S2:
        if entree[0] == code:
            return entree
    raise KeyError(f"{code} n'est pas dans le releve de test")


def _mue_attendue(code: str):
    """La MUE **affichee** sur le releve pour cette UE.

    Elle est portee par la premiere matiere de l'entree : c'est un support de
    test, pas un modele. On lit la valeur du document plutot que de la
    recalculer — la recalculer ferait verifier le calcul par lui-meme.
    """

    return _ue(code)[3][0][5]


def _matieres(code: str):
    """Les matieres de cette UE, dans l'ordre du releve."""

    return [entree[0] for entree in _ue(code)[3]]


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

        # --- Le contenu du bulletin ------------------------------------
        # Le bulletin se construit en deux couches : le contenu d'abord, la
        # mise en page ensuite. Ce controle porte sur la premiere — c'est elle
        # qui decide, et c'est donc la seule qui merite d'etre verifiee contre
        # le document.
        from app.services.bulletin_service import NON_RENSEIGNE, composer_bulletin
        from app.services.deliberation_service import BAREME_REPLI as _bar

        async with fabrique() as db:
            bulletin = composer_bulletin(
                bilan,
                infos={
                    "etablissement": {
                        "nom": "Institut Semestre E2E", "sigle": "ISE",
                        "adresse": "Km 5, Dakar", "telephone": "+221 33 000 00 00",
                        "email": "contact@ise.org", "pays": "Sénégal",
                    },
                    "etudiant": {
                        "nom": "Kane", "prenom": "Harouna",
                        "matricule": "2018-GLS-0001", "filiere": "Génie Logiciel",
                        "niveau": "L1", "classe": "GLS-L1",
                    },
                    "session": {"nom": "Session Semestre", "annee_academique": "2018-2019"},
                    "bareme_mentions": _bar["bareme_mentions"],
                },
                recap=recap,
            )

        # L'en-tete : ce qui identifie le document et son destinataire.
        assert bulletin.etablissement_nom == "Institut Semestre E2E"
        assert bulletin.matricule == "2018-GLS-0001"
        assert bulletin.filiere == "Génie Logiciel"
        assert bulletin.semestre_numero == 2
        assert bulletin.semestre_libelle == "S2"
        assert bulletin.session_annee == "2018-2019"

        # Les sept UE du releve, dans l'ordre du code — pas dans l'ordre de la
        # base. L'ordre de lecture est celui des releves : UE1.2.1, UE1.2.2, …
        assert [bloc.code for bloc in bulletin.blocs] == [c for c, *_ in RELEVE_S2], (
            [bloc.code for bloc in bulletin.blocs]
        )

        # Chaque UE porte son CUE, ses matieres et sa MUE affichee.
        for (code, _nom, cue, _releve), bloc in zip(RELEVE_S2, bulletin.blocs):
            assert bloc.cue == cue, f"{code} : CUE {bloc.cue} au lieu de {cue}"
            assert bloc.mue == _mue_attendue(code), (
                f"{code} : MUE affichee {bloc.mue} au lieu de "
                f"{_mue_attendue(code)}."
            )
            assert len(bloc.matieres) == len(_matieres(code)), bloc.matieres

        # La moyenne du semestre et sa mention, 12,51 → Assez Bien.
        assert bulletin.moyenne_semestre == MOYENNE_S2, bulletin.moyenne_semestre
        assert bulletin.mention_semestre == "Assez Bien", bulletin.mention_semestre
        assert bulletin.credits_prevus == CREDITS_S2, bulletin.credits_prevus
        assert bulletin.matieres() == 14, bulletin.matieres()

        # Les nombres s'impriment a la francaise : « 12,51 », pas « 12.51 ».
        # Le meme nombre ecrit autrement sur un document officiel se lit comme
        # une autre note.
        premiere = bulletin.blocs[0].matieres[0]
        assert premiere.cec_texte() == "1,00", premiere.cec_texte()
        assert premiere.mec == 12.00, premiere.mec

        # Le recapitulatif annuel : deux lignes, plus la synthese.
        assert [ligne.libelle for ligne in bulletin.recapitulatif] == ["S1", "S2"], (
            bulletin.recapitulatif
        )
        assert bulletin.moyenne_annuelle == MOYENNE_GENERALE, bulletin.moyenne_annuelle
        assert bulletin.mention_annuelle == "Assez Bien", bulletin.mention_annuelle

        # Un semestre sans recapitulatif ne laisse pas un bloc vide : la
        # fonction rend le bulletin du semestre impair, sans ces lignes.
        async with fabrique() as db:
            bulletin_s1 = composer_bulletin(
                bilan1,
                infos={"etablissement": {"nom": "ISE"}, "etudiant": {"nom": "Kane", "prenom": "Harouna"}},
                recap=recap1,
            )
        assert bulletin_s1.recapitulatif == [], bulletin_s1.recapitulatif
        assert bulletin_s1.moyenne_annuelle is None, bulletin_s1.moyenne_annuelle
        print("  [OK] Bulletin : 7 UE, moyenne 12,51, recapitulatif 12,14, nombres a la francaise.")

        # --- Les deux routes du bulletin ------------------------------
        # Le JSON et le PDF sortent du meme calcul. Les verifier separement
        # n'a d'interet que si les deux disent la meme chose — c'est
        # exactement ce que controle cet enonce.
        contenu = await client.get(
            f"/api/v1/pedagogie/bulletins/{etudiant['id']}/{s2['id']}",
            headers=admin,
        )
        assert contenu.status_code == 200, contenu.text
        corps = contenu.json()

        assert corps["session"]["semestre_libelle"] == "S2", corps["session"]
        assert corps["totaux"]["moyenne"] == MOYENNE_S2, corps["totaux"]
        assert corps["totaux"]["mention"] == "Assez Bien", corps["totaux"]
        assert corps["totaux"]["credits_prevus"] == CREDITS_S2, corps["totaux"]
        assert [u["code"] for u in corps["unites"]] == [c for c, *_ in RELEVE_S2], (
            [u["code"] for u in corps["unites"]]
        )
        assert corps["recapitulatif"]["moyenne_annuelle"] == MOYENNE_GENERALE, (
            corps["recapitulatif"]
        )
        # Aucune deliberation n'a ete tenue sur cette instance : le bulletin
        # doit le dire, plutot que de laisser croire que le jury s'est prononce.
        assert corps["observations"]["deliberation_absente"] is True, corps["observations"]

        # L'etudiant inconnu et le semestre inconnu ne donnent pas le meme
        # message : l'agent ne cherche pas au meme endroit.
        inconnu = await client.get(
            f"/api/v1/pedagogie/bulletins/etudiant-inexistant/{s2['id']}",
            headers=admin,
        )
        assert inconnu.status_code == 404, inconnu.text
        assert "étudiant" in inconnu.json()["detail"], inconnu.json()

        sans_semestre = await client.get(
            f"/api/v1/pedagogie/bulletins/{etudiant['id']}/semestre-inexistant",
            headers=admin,
        )
        assert sans_semestre.status_code == 404, sans_semestre.text
        assert "semestre" in sans_semestre.json()["detail"], sans_semestre.json()

        # Le PDF, lui, doit etre un PDF, et porter les memes chiffres.
        pdf = await client.get(
            f"/api/v1/pedagogie/bulletins/{etudiant['id']}/{s2['id']}/pdf",
            headers=admin,
        )
        assert pdf.status_code == 200, pdf.text
        assert pdf.headers["content-type"] == "application/pdf", pdf.headers
        assert pdf.content[:5] == b"%PDF-", pdf.content[:20]
        assert "attachment" in pdf.headers.get("content-disposition", ""), (
            pdf.headers.get("content-disposition")
        )
        # Ni signature ni cachet imprimes : le document se signe a la main.
        assert pdf.content.count(b"/Subtype /Image") == 0, (
            "Le bulletin contient une image. Ni signature ni cachet ne doivent "
            "y figurer : ils sont apposes a la main, apres impression."
        )
        print("  [OK] Bulletin : JSON et PDF concordants, 404 nommes, rien de signe.")

        # --- Aucune case vide, et pourquoi elle est vide -----------------
        # Une matiere notee d'un seul coup affiche « n. c. » et non un tiret :
        # un tiret affirmerait qu'aucun examen n'existe, alors qu'on ne peut
        # pas distinguer « pas d'examen » de « examen non saisi ».
        from app.services.bulletin_service import LigneMatiere as _Ligne

        seule = _Ligne(code="X1", nom="Notée par un seul contrôle", mec=14.0)
        assert seule.mec == 14.0
        assert NON_RENSEIGNE == "n. c.", repr(NON_RENSEIGNE)

        # L'incoherence que les donnees revelent sans rien supposer du plan de
        # l'institut : un controle sans examen, ou l'inverse. Elle est
        # signalee, parce que « n. c. » ne dit pas s'il manque une note ou une
        # epreuve.
        async with fabrique() as db:
            ue_incomplete = UniteEnseignement(
                id=str(uuid.uuid4()), filiere_id=filiere["id"],
                nom="UE au controle seul", code="UE1.3.I",
                credits=3, coefficient=1.0, heures=60,
                semestre="S3", niveau="L1", semestre_id=s3["id"],
            )
            db.add(ue_incomplete)
            await db.flush()
            matiere_incomplete = Matiere(
                id=str(uuid.uuid4()), ue_id=ue_incomplete.id,
                nom="Controle sans examen", code="UE1.3.I-M1",
                credits=3, coefficient=1.0,
                heures_cm=0, heures_td=0, heures_tp=0,
            )
            db.add(matiere_incomplete)
            await db.flush()
            evaluation_incomplete = Examen(
                id=str(uuid.uuid4()), nom="Devoir",
                session_id=session["id"], matiere_id=matiere_incomplete.id,
                type_examen="CC", date_examen=date(2019, 1, 10),
                duree_minutes=0, coefficient=1.0,
            )
            db.add(evaluation_incomplete)
            await db.flush()
            db.add(Note(
                id=str(uuid.uuid4()), etudiant_id=etudiant["id"],
                matiere_id=matiere_incomplete.id, examen_id=evaluation_incomplete.id,
                session_id=session["id"], semestre_id=s3["id"],
                valeur=13.0, coefficient=1.0,
            ))
            await db.commit()

        async with fabrique() as db:
            bilan_incomplet = await service.bilan_semestre(
                db, etudiant_id=etudiant["id"],
                session_id=session["id"], semestre_id=s3["id"],
            )
            bulletin_incomplet = composer_bulletin(
                bilan_incomplet,
                infos={
                    "etablissement": {"nom": "ISE"},
                    "etudiant": {"nom": "Kane", "prenom": "Harouna"},
                },
            )
        assert len(bulletin_incomplet.incompletudes) == 1, (
            bulletin_incomplet.incompletudes
        )
        manque = bulletin_incomplet.incompletudes[0]
        assert manque["code"] == "UE1.3.I-M1", manque
        assert manque["manque"] == "examen", manque
        # La matiere deux-devoirs du meme semestre, elle, a controle **et**
        # examen : elle n'est pas signalee, et c'est voulu.
        codes_signales = {e["code"] for e in bulletin_incomplet.incompletudes}
        assert "UE1.3.D-M1" not in codes_signales, codes_signales
        print("  [OK] Case sans valeur : « n. c. », et l'incoherence signalee.")

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
            # L'identifiant est genere : le **code** ne le remplace pas, et
            # l'utiliser ici creerait une note sur une matiere inexistante —
            # silencieusement, puisque rien ne verifie qu'elle existe.
            id_matiere_annuelle = matiere_annuelle.id
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
            # ce que l'agent lit sur le bulletin. Le controle porte sur la
            # mecanique d'addition, pas sur un equilibre de credits que c'est
            # l'institut qui tient.
            assert bilan.credits_prevus == CREDITS_S2 + 3, (
                f"Credits du semestre {cle} : {bilan.credits_prevus} au lieu de "
                f"{CREDITS_S2 + 3}. Les 3 credits de l'enseignement annuel "
                "manquent, ou y sont comptes deux fois."
            )
            assert bilan.annuelles_sans_note == [], bilan.annuelles_sans_note

        # Les credits d'un enseignement annuel entrent dans **chaque** semestre
        # ou il figure. Ici l'UE vaut 3, donc chaque semestre affiche 30 + 3.
        #
        # Ce 33 n'est **pas** une regle du produit, et le test ne pretend pas
        # en verifier une : un institut equilibre ses semestre a 30 credits en
        # portant 1,5 + 1,5 sur un annuel, ce qui donne 30 / 30 / 60. Le
        # controle porte sur la mecanique — les credits s'ajoutent une fois par
        # semestre — et la mecanique est la meme dans les deux conventions.
        async with fabrique() as db:
            recap_annuel = await service.recap_annuel(
                db, etudiant_id=etudiant["id"],
                session_id=session["id"], semestre_id=s2["id"],
            )
        assert recap_annuel is not None
        assert recap_annuel["credits_total"] == (
            CREDITS_S1 + CREDITS_S2 + 2 * 3
        ), recap_annuel["credits_total"]
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

        # --- Le rattrapage remplace, il ne s'ajoute pas ------------------
        # C'est le point entier du flux. Si le rattrapage ne **remplace** pas
        # la premiere tentative, le moteur moyenne les deux : (12 + 15) / 2 =
        # 13,50, une moyenne que personne n'a notee, et que l'etudiant
        # chercherait ensuite dans son dossier.
        #
        # On travaille sur la matiere « Expression ecrite » (UE-ANN), notee
        # 12 en S1. On y ajoute un rattrapage a 16.
        rattrapage_evaluation = Examen(
            id=str(uuid.uuid4()), nom="Rattrapage",
            session_id=session["id"], matiere_id=id_matiere_annuelle,
            type_examen="Rattrapage", date_examen=date(2019, 7, 1),
            duree_minutes=120, coefficient=1.0,
        )
        async with fabrique() as db:
            db.add(rattrapage_evaluation)
            await db.flush()
            db.add(Note(
                id=str(uuid.uuid4()), etudiant_id=etudiant["id"],
                matiere_id=id_matiere_annuelle, examen_id=rattrapage_evaluation.id,
                session_id=session["id"], semestre_id=s1["id"],
                valeur=16.0, coefficient=1.0, statut="Rattrapage",
            ))
            await db.commit()

        async with fabrique() as db:
            bilan_apres = await service.bilan_semestre(
                db, etudiant_id=etudiant["id"],
                session_id=session["id"], semestre_id=s1["id"],
            )
        annuelle_apres = next(
            ue for ue in bilan_apres.unites if ue.code == "UE-ANN"
        )
        assert annuelle_apres.mue == 16.0, (
            f"MUE de l'enseignement annuel apres rattrapage : "
            f"{annuelle_apres.mue} au lieu de 16,00. Si le moteur avait "
            "moyenne les deux notes, il afficherait 14,00 — une moyenne qui "
            "n'appartient a aucune epreuve."
        )
        assert len(annuelle_apres.matieres[0].evaluations) == 1, (
            f"Le bulletin porte {len(annuelle_apres.matieres[0].evaluations)} "
            "evaluations pour cette matiere apres rattrapage : la premiere "
            "tentative n'a pas ete ecartee."
        )
        # S2 n'est pas touche : le rattrapage ne vaut que sur le semestre ou il
        # a ete passe. Sans cela, une reussite en rattrapage accorderait des
        # credits sur l'autre semestre, ou aucune epreuve n'a eu lieu.
        async with fabrique() as db:
            bilan_s2_apres = await service.bilan_semestre(
                db, etudiant_id=etudiant["id"],
                session_id=session["id"], semestre_id=s2["id"],
            )
        annuelle_s2 = next(
            ue for ue in bilan_s2_apres.unites if ue.code == "UE-ANN"
        )
        assert annuelle_s2.mue == 15.0, (
            f"Le rattrapage passe en S1 a modifie le S2 : {annuelle_s2.mue} au "
            "lieu de 15,00. Une epreuve ne vaut que sur son semestre."
        )
        print("  [OK] Rattrapage : 16 remplace 12, S2 inchange, jamais de moyenne des deux.")

        # --- La liste des matieres a reprendre ---------------------------
        # Elle se lit dans les decisions du jury, pas dans les propositions.
        rattrapage = await client.get(
            f"/api/v1/pedagogie/rattrapage/{etudiant['id']}",
            params={"session_id": session["id"]}, headers=admin,
        )
        assert rattrapage.status_code == 200, rattrapage.text
        corps_rattrapage = rattrapage.json()
        # Aucune seance de jury n'a ete tenue dans ce test : c'est un etat a
        # lui, pas une liste vide qui se lirait comme « rien a reprendre ».
        assert corps_rattrapage["etat"] == "aucune_seance", corps_rattrapage
        assert corps_rattrapage["unites"] == [], corps_rattrapage
        assert corps_rattrapage["message"], "Un etat doit porter son explication."

        inconnu_rat = await client.get(
            "/api/v1/pedagogie/rattrapage/etudiant-inexistant",
            params={"session_id": session["id"]}, headers=admin,
        )
        assert inconnu_rat.status_code == 404, inconnu_rat.text
        print("  [OK] Rattrapage : absence de seance signalee comme telle.")

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
