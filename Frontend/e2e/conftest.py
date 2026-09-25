"""
Fixtures de la suite E2E frontend (Playwright).

La suite est **hermetique** : elle ne touche jamais la base de l'institut.

- une base SQLite temporaire, migree jusqu'a `head` ;
- un backend uvicorn dedie, sur un port libre, avec cette base et des
  repertoires de stockage temporaires ;
- un serveur Vite dedie, pointe vers ce backend ;
- un catalogue de donnees realistes cree via l'API, afin que les pages
  soient exercees **avec du contenu** : une page vide ne traverse pas le
  code qui plante.

Point cle : chaque navigation collecte les erreurs et avertissements de la
console du navigateur. C'est ce qui detecte un plantage de rendu ou un HTML
invalide, la ou un simple `assert` de presence d'element passe.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import pytest
import requests
from playwright.sync_api import ConsoleMessage, Page, sync_playwright

RACINE = Path(__file__).resolve().parents[1]          # Frontend/
BACKEND = RACINE.parent / "Backend"
VENV_PYTHON = BACKEND / "venv" / "Scripts" / "python.exe"

# Alembic execute ``alembic/env.py`` qui importe ``app.*``. La suite etant
# lancee depuis Frontend/, le repertoire Backend doit etre importable.
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

#: Identifiants de l'instance de test, crees par le Setup Wizard.
ADMIN_EMAIL = "admin.e2e@ecole-ci.org"
ADMIN_PASSWORD = "E2E-Admin-2026!"
SECRETARY_EMAIL = "secretariat.e2e@ecole-ci.org"
SECRETARY_PASSWORD = "E2E-Secretary-2026!"

#: Comptes des portails personnels. Ils ne doivent pas etre visibles dans le
#: menu d'un administrateur, mais leur propre page doit fonctionner.
TEACHER_EMAIL = "enseignant.e2e@ecole-ci.org"
TEACHER_PASSWORD = "E2E-Teacher-2026!"
STUDENT_EMAIL = "etudiant.e2e@ecole-ci.org"
STUDENT_PASSWORD = "E2E-Student-2026!"

#: Delai d'affichage d'une page : chargement du bundle puis restauration de la
#: session aupres de l'API. Partage par tous les modules de test.
DELAI_RENDU = 20000

#: Messages de console qui ne sont pas des defauts applicatifs et qui
#: pollueraient le signal.
#:
#: Les journaux reseau de Chrome (« Failed to load resource ») sont exprimes
#: pour tout statut HTTP non 2xx, y compris un refus **attendu** : un
#: televersement de logo invalide repond 422, le navigateur le consigne, et
#: l'application affiche son message. Etre sever sur ce journal
#: interdirait de tester les cas de refus — qui sont justement ceux qui
#: comptent. Le traitement applicatif de l'erreur reste verifie : par
#: l'assertion sur le message affiche.
BRUITS_CONSOLE = (
    "React Router Future Flag Warning",
    "React DevTools",
    "Download the React DevTools",
    "React Router will begin wrapping state updates",
    "Relative route resolution within Splat routes",
    "Failed to load resource",
)


def _port_libre(preference: int) -> int:
    """Reserve un port libre, en evitant les collisions entre runs."""

    for candidat in [preference, preference + 1, preference + 2, preference + 3]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as prise:
            try:
                prise.bind(("127.0.0.1", candidat))
            except OSError:
                continue
            return candidat
    raise RuntimeError("Aucun port libre disponible pour la suite E2E.")


def _attendre(url: str, delai_max: float = 90.0) -> None:
    """Attend qu'une URL reponde, sans dependre d'un outil externe."""

    limite = time.time() + delai_max
    while time.time() < limite:
        try:
            reponse = requests.get(url, timeout=2)
            if reponse.status_code < 500:
                return
        except requests.RequestException:
            pass
        time.sleep(0.4)
    raise RuntimeError(f"Le service {url} n'a pas demarre dans le delai imparti.")


#: Plages de ports reservees a la suite. Les processus portees de ces ports
#: proviennent uniquement des runs precedents.
_PORTS_E2E = ("8111", "8112", "8113", "8114", "5173", "5174", "5175", "5176")


def _tuer_processus_residuels() -> None:
    """Tue les processus E2E des runs precedents.

    Le ciblage se fait sur la ligne de commande ET sur les ports reserves :
    les serveurs de developpement de l'utilisateur (8080, 8000) ne sont
    jamais concernes.
    """

    if os.name == "nt":
        enumeration = "Get-CimInstance Win32_Process"
        filtre = (
            f"{enumeration} -Filter \"Name = 'python.exe' OR Name = 'node.exe'\" | "
            "Where-Object { $_.CommandLine -match '--strictPort' -or "
            "$_.CommandLine -match '--port 81(11|12|13|14)' -or "
            "$_.CommandLine -match 'log-level warning' } | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", filtre],
            capture_output=True,
            timeout=60,
        )
    else:  # pragma: no cover - environnement de developpement Windows
        subprocess.run(["pkill", "-f", "strictPort"], capture_output=True)
        subprocess.run(["pkill", "-f", "log-level warning"], capture_output=True)
    time.sleep(1.0)


#: Repertoires de stockage que le backend doit utiliser, et qui ne peuvent
#: pas deborder du dossier temporaire de la suite. Si l'un d'eux n'est pas
#: passe au processus, il se resout par defaut relativement au dossier du
#: backend — et les tests deposent alors leurs fichiers dans le stockage de
#: production, silencieusement.
REPERTOIRES_STOCKAGE = (
    "ADMISSIONS_STORAGE_DIR",
    "DOCUMENTS_STORAGE_DIR",
    "BRANDING_STORAGE_DIR",
)


def _resoudre_sans_echouer(chemin: Path) -> Path:
    """``resolve`` qui ne leve pas sur un chemin inexistant."""

    try:
        return chemin.resolve()
    except OSError:  # pragma: no cover - depend du systeme de fichiers
        return chemin


def _verifier_isollement_stockage(dossier: Path, env_alembic: dict) -> None:
    """Echoue si un repertoire de stockage sort du dossier de la suite.

    Le controle porte sur l'environnement **transmis** au backend, et non sur
    celui du processus de test : c'est la valeur reellement recue par
    l'application qui compte, et c'est elle qui a deja produit la pollution.
    """

    racine = _resoudre_sans_echouer(dossier)
    debordements: list[str] = []

    for nom in REPERTOIRES_STOCKAGE:
        valeur = env_alembic.get(nom)
        if not valeur:
            debordements.append(f"{nom} non defini (defaut relatif au backend)")
            continue
        cible = Path(valeur)
        resolue = _resoudre_sans_echouer(
            cible if cible.is_absolute() else (RACINE.parent / "Backend" / cible)
        )
        if not str(resolue).lower().startswith(str(racine).lower()):
            debordements.append(f"{nom}={valeur}")

    if debordements:
        raise RuntimeError(
            "La suite E2E utiliserait un stockage hors de son dossier "
            "temporaire, ce qui deposerait des fichiers d'essai chez le "
            f"client :\n  - " + "\n  - ".join(debordements) +
            f"\nDossier attendu : {racine}"
        )


def _nettoyer_dossier(dossier: Path, tentatives: int = 5) -> None:
    """Supprime le dossier temporaire, en echouant si un verrou persiste.

    Un ``rmtree(ignore_errors=True)`` masquerait un fichier SQLite encore
    ouvert par un processus fantome : le run suivant aurait alors herite
    d'une base deja amorcee. Mieux vaut une erreur explicite.
    """

    for tentative in range(tentatives):
        if not dossier.exists():
            return
        shutil.rmtree(dossier, ignore_errors=True)
        if not dossier.exists():
            return
        time.sleep(0.6)
    raise RuntimeError(
        f"Impossible de supprimer le dossier temporaire {dossier}. "
        "Un processus E2E le verrouille encore ; fermez-le puis relancez."
    )


def _arreter_arbre(processus: subprocess.Popen) -> None:
    """Termine un processus et toute sa descendance."""

    if processus.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(processus.pid), "/T", "/F"],
            capture_output=True,
            timeout=30,
        )
    else:  # pragma: no cover
        try:
            os.killpg(os.getpgid(processus.pid), 15)
        except Exception:
            processus.terminate()
    try:
        processus.wait(timeout=15)
    except Exception:
        processus.kill()


@dataclass
class Environnement:
    dossier: Path
    port_backend: int
    port_frontend: int
    racine_frontend: Path
    repertoire_log: Path
    processus_backend: subprocess.Popen
    processus_frontend: subprocess.Popen
    base_backend: str = ""
    base_frontend: str = ""
    _logs: list = field(default_factory=list)

    def arreter(self) -> None:
        for processus in (self.processus_frontend, self.processus_backend):
            _arreter_arbre(processus)


@pytest.fixture(scope="session")
def environnement() -> Iterator[Environnement]:
    """Demarre la pile de test (base, backend, frontend) puis laarrete."""

    # Les runs precedents peuvent avoir laisse des processus orphelins
    # (voir _arreter_arbre) : on les elimine avant de reserve les ports.
    _tuer_processus_residuels()

    dossier = Path(tempfile.gettempdir()) / "appedu-e2e-frontend"
    _nettoyer_dossier(dossier)
    dossier.mkdir(parents=True, exist_ok=True)

    base_sqlite = dossier / "e2e.db"
    url_sqlite = f"sqlite+aiosqlite:///{base_sqlite.as_posix()}"
    # 1. Schema : migrations Alembic sur la base temporaire uniquement, dans
    #    un sous-processus (voir note sur asyncio.run plus haut).
    env_alembic = {
        **os.environ,
        "DATABASE_URL": url_sqlite,
        "ENVIRONMENT": "development",
        "ADMISSIONS_STORAGE_DIR": str(dossier / "admissions"),
        "DOCUMENTS_STORAGE_DIR": str(dossier / "documents"),
        "BRANDING_STORAGE_DIR": str(dossier / "branding"),
    }
    migration = subprocess.run(
        [str(VENV_PYTHON), "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND),
        env=env_alembic,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if migration.returncode != 0:
        raise RuntimeError(
            "Echec de la migration de la base E2E :\n"
            f"{migration.stdout}\n{migration.stderr}"
        )

    port_backend = _port_libre(8111)
    port_frontend = _port_libre(5173)
    logs = dossier / "logs"
    logs.mkdir(exist_ok=True)

    env_backend = {
        **env_alembic,
        "PYTHONUNBUFFERED": "1",
    }
    fichier_log_backend = (logs / "backend.log").open("w", encoding="utf-8", errors="replace")
    processus_backend = subprocess.Popen(
        [
            str(VENV_PYTHON), "-m", "uvicorn", "app.main:app",
            "--host", "127.0.0.1", "--port", str(port_backend), "--log-level", "warning",
        ],
        cwd=str(BACKEND),
        env=env_backend,
        stdout=fichier_log_backend,
        stderr=subprocess.STDOUT,
    )
    base_backend = f"http://127.0.0.1:{port_backend}"

    env_frontend = {
        **os.environ,
        "VITE_API_URL": f"{base_backend}/api/v1",
        "FORCE_COLOR": "0",
    }
    # Sous Windows, ``npx`` n'existe que comme script PowerShell/CMD : Popen
    # ne le trouve pas sans chemin absolu. On resout l'executable.
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if npx is None:
        raise RuntimeError("npx est introuvable : le serveur Vite ne peut pas demarrer.")

    fichier_log_frontend = (logs / "frontend.log").open("w", encoding="utf-8", errors="replace")
    processus_frontend = subprocess.Popen(
        [
            npx, "vite", "--host", "127.0.0.1", "--port", str(port_frontend),
            "--strictPort", "--config", str(RACINE / "vite.config.ts"),
        ],
        cwd=str(RACINE),
        env=env_frontend,
        stdout=fichier_log_frontend,
        stderr=subprocess.STDOUT,
    )
    base_frontend = f"http://127.0.0.1:{port_frontend}"

    env = Environnement(
        dossier=dossier,
        port_backend=port_backend,
        port_frontend=port_frontend,
        racine_frontend=RACINE,
        repertoire_log=logs,
        processus_backend=processus_backend,
        processus_frontend=processus_frontend,
        base_backend=base_backend,
        base_frontend=base_frontend,
    )

    try:
        _attendre(f"{base_backend}/health")
        _verifier_isollement_stockage(dossier, env_alembic)
        _attendre(base_frontend)
        _semer(env)
        yield env
    finally:
        env.arreter()
        fichier_log_backend.close()
        fichier_log_frontend.close()
        # Les poignees SQLite peuvent mettre quelques instants a se liberer.
        for _ in range(5):
            shutil.rmtree(dossier, ignore_errors=True)
            if not dossier.exists():
                break
            time.sleep(0.6)


# ---------------------------------------------------------------------------
# Jeu de donnees : cree via l'API, jamais en SQL
# ---------------------------------------------------------------------------
def _api(env: Environnement, methode: str, chemin: str, **kwargs) -> requests.Response:
    return requests.request(
        methode, f"{env.base_backend}/api/v1{chemin}", timeout=30, **kwargs
    )


def _api_ok(env: Environnement, methode: str, chemin: str, **kwargs) -> requests.Response:
    """Appel d'API qui doit aboutir ; sinon l'erreur est explicite.

    Un seeding tolerant echouerait silencieusement et produirait des pages
    vides, donc des tests qui passent sans rien verifier.
    """

    reponse = _api(env, methode, chemin, **kwargs)
    if reponse.status_code >= 400:
        raise RuntimeError(
            f"Appel {methode} {chemin} refuse ({reponse.status_code}) : {reponse.text}"
        )
    return reponse


def _semer(env: Environnement) -> None:
    """Instruit une instance minimale mais realiste.

    Les sessions comportent des periodes de paiement : sans elles, la tuile
    de periode du modal de paiement n'est pas rendue — c'est precisement le
    chemin qui plantait.
    """

    initialisation = _api(env, "POST", "/setup/initialize", json={
        "etablissement": {
            "nom": "Institut E2E Frontend",
            "code": "E2E-FE",
            "adresse": "Rue des tests",
            "telephone": "+2250000000000",
            "email": "contact@e2e.example.org",
            "devise": "XOF",
        },
        "admin": {
            "email": ADMIN_EMAIL, "nom": "Admin", "prenom": "E2E",
            "password": ADMIN_PASSWORD,
        },
    })
    if initialisation.status_code >= 400:
        raise RuntimeError(
            f"Initialisation E2E refusee ({initialisation.status_code}) : "
            f"{initialisation.text}"
        )

    jeton = _connexion(env, ADMIN_EMAIL, ADMIN_PASSWORD)
    entetes = {"Authorization": f"Bearer {jeton}"}

    _api_ok(env, "POST", "/users/", json={
        "email": SECRETARY_EMAIL, "nom": "Secretariat", "prenom": "E2E",
        "role": "SECRETARIAT", "password": SECRETARY_PASSWORD,
    }, headers=entetes)

    # Delegation d'emission au secretariat : c'est l'usage prevu de
    # ``documents.issue`` (migration 0015). Le role legacy SECRETARIAT ne la
    # porte pas par heritage — elle s'accorde, sinon le secretariat n'a pas
    # son outil de travail.
    _api_ok(env, "PUT", "/rbac/roles/ROLE_SECRETARIAT/permissions",
            json={"permissions": ["documents.issue"]}, headers=entetes)
    _api_ok(env, "POST", "/rbac/roles/ROLE_SECRETARIAT/users",
            json={"user_ids": [_identifiant_utilisateur(env, entetes, SECRETARY_EMAIL)]},
            headers=entetes)

    filiere = _api_ok(env, "POST", "/structure/filieres", json={
        "nom": "Genie Logiciel", "code": "GL", "duree": 3,
        "diplome": "Licence", "niveau": "L1",
    }, headers=entetes).json()

    session = _api_ok(env, "POST", "/sessions/", json={
        "nom": "Session 2026-2027", "code": "SES-2627",
        "annee_academique": "2026-2027",
        "date_debut": "2026-10-01", "date_fin": "2027-07-31",
        "statut": "active",
        "periodes": [
            {"nom": "Tranche 1", "mois": "Octobre", "date_echeance": "2026-10-15",
             "montant_estime": 75000, "pourcentage": 25, "ordre": 1},
            {"nom": "Tranche 2", "mois": "Janvier", "date_echeance": "2027-01-15",
             "montant_estime": 75000, "pourcentage": 25, "ordre": 2},
            {"nom": "Tranche 3", "mois": "Avril", "date_echeance": "2027-04-15",
             "montant_estime": 75000, "pourcentage": 25, "ordre": 3},
        ],
    }, headers=entetes).json()

    cycle = _api_ok(env, "POST", "/academic/cycles",
                  json={"nom": "Licence", "code": "LIC"}, headers=entetes).json()
    niveau = _api_ok(env, "POST", "/academic/niveaux",
                  json={"code": "L1", "nom": "Licence 1", "cycle_id": cycle["id"]},
                  headers=entetes).json()
    classe = _api_ok(env, "POST", "/academic/classes", json={
        "code": "GL-L1", "nom": "Genie Logiciel L1",
        "filiere_id": filiere["id"], "niveau_id": niveau["id"],
    }, headers=entetes).json()

    ue = _api_ok(env, "POST", "/structure/ues", json={
        "nom": "Algorithmique 2", "code": "ALGO2", "credits": 4, "coefficient": 2,
        "filiere_id": filiere["id"], "niveau": "L1", "semestre": "S1", "heures": 60,
    }, headers=entetes).json()
    matiere = _api_ok(env, "POST", "/structure/matieres", json={
        "nom": "Tri et recurrence", "code": "TRM1", "credits": 3, "coefficient": 1.5,
        "heures_cm": 20, "heures_td": 10, "heures_tp": 8, "ue_id": ue["id"],
    }, headers=entetes).json()

    _api_ok(env, "POST", "/finances/grilles-tarifaires", json={
        "filiere": filiere["nom"], "filiere_id": filiere["id"], "niveau": "L1",
        "droits_inscription": 100000, "scolarite_mensuelle": 75000,
        "nombre_mois": 8, "actif": True,
    }, headers=entetes)

    for index in range(1, 4):
        # Le premier dossier porte l'email du compte portail etudiant : le
        # backend resout le lien par email, ce qui exerce ce chemin reel.
        courriel = STUDENT_EMAIL if index == 1 else f"etudiant{index}.e2e@ecole-ci.org"
        etudiant = _api_ok(env, "POST", "/etudiants/", json={
            "nom": f"Etudiant{index}", "prenom": "Jean",
            "sexe": "M", "matricule": f"E2E-{index:04d}",
            "date_naissance": "2005-03-12", "email": courriel,
            "classe_id": classe["id"], "session_id": session["id"],
        }, headers=entetes).json()
        _api_ok(env, "POST", "/pedagogie/examens", json={
            "nom": "Examen E2E", "type_examen": "Examen Final",
            "date_examen": "2026-12-15", "duree_minutes": 120, "coefficient": 1,
            "matiere_id": matiere["id"], "session_id": session["id"],
        }, headers=entetes)
        _api_ok(env, "POST", "/pedagogie/notes", json={
            "etudiant_id": etudiant["id"], "matiere_id": matiere["id"],
            "valeur": 10 + index, "coefficient": 1, "session_id": session["id"],
        }, headers=entetes)

    _api_ok(env, "POST", "/users/", json={
        "email": TEACHER_EMAIL, "nom": "Enseignant", "prenom": "E2E",
        "role": "ENSEIGNANT", "password": TEACHER_PASSWORD,
    }, headers=entetes)
    _api_ok(env, "POST", "/users/", json={
        "email": STUDENT_EMAIL, "nom": "Etudiant", "prenom": "Jean",
        "role": "ETUDIANT", "password": STUDENT_PASSWORD,
    }, headers=entetes)


def _identifiant_utilisateur(
    env: "Environnement", entetes: dict, email: str
) -> str:
    """Relit l'identifiant d'un compte depuis l'API, plutot que de le deviner."""

    comptes = _api_ok(env, "GET", "/users/", headers=entetes).json()
    trouve = next((c for c in comptes if c["email"] == email), None)
    if trouve is None:
        raise RuntimeError(f"Compte absent apres creation : {email}")
    return trouve["id"]


def _connexion(env: Environnement, email: str, mot_de_passe: str) -> str:
    reponse = _api(env, "POST", "/auth/login",
                   json={"email": email, "password": mot_de_passe})
    reponse.raise_for_status()
    return reponse.json()["access_token"]


class Administration:
    """Client HTTP authentifie, pour les preparations qu'un test E2E doit faire.

    Certains scenarios ne peuvent pas passer par l'interface : accorder une
    permission ne se fait pas depuis l'ecran que l'on est en train de tester.
    """

    def __init__(self, env: "Environnement", token: str) -> None:
        self.base = f"{env.base_backend}/api/v1"
        self.headers = {"Authorization": f"Bearer {token}"}

    def _api_ok(self, methode: str, chemin: str, **kwargs) -> requests.Response:
        reponse = requests.request(
            methode, f"{self.base}{chemin}", timeout=30,
            headers=self.headers, **kwargs,
        )
        if reponse.status_code >= 400:
            raise RuntimeError(
                f"Preparation E2E refusee ({reponse.status_code}) {methode} {chemin} "
                f": {reponse.text}"
            )
        return reponse


@pytest.fixture
def administration(environnement) -> Administration:
    """Client API en tant qu'administrateur."""

    jeton = _connexion(environnement, ADMIN_EMAIL, ADMIN_PASSWORD)
    return Administration(environnement, jeton)


# ---------------------------------------------------------------------------
# Navigateur
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def app_url(environnement) -> str:
    """URL racine de l'application servie pour la suite."""

    return environnement.base_frontend


@pytest.fixture(scope="session")
def navigateur():
    with sync_playwright() as p:
        yield p


@pytest.fixture
def page_console(navigateur, environnement) -> Iterator[tuple[Page, list[str]]]:
    """Page vierge qui enregistre les messages de console.

    Le second element de la sortie est la liste des problemes detectes :
    une page peut s'afficher et Nonetheless produire une erreur console.
    """

    navigateur_web = navigateur.chromium.launch()
    contexte = navigateur_web.new_context(viewport={"width": 1440, "height": 900})
    page = contexte.new_page()
    page.set_default_timeout(20000)

    problemes: list[str] = []

    def _sur_message(message: ConsoleMessage) -> None:
        if message.type not in ("error", "warning"):
            return
        texte = message.text
        if any(bruit in texte for bruit in BRUITS_CONSOLE):
            return
        problemes.append(f"[{message.type}] {texte}")

    def _sur_exception(erreur) -> None:
        problemes.append(f"[exception] {erreur}")

    page.on("console", _sur_message)
    page.on("pageerror", _sur_exception)

    try:
        yield page, problemes
    finally:
        contexte.close()
        navigateur_web.close()


@pytest.fixture
def page(page_console) -> Page:
    return page_console[0]


def _connecter(page: Page, app_url: str, email: str, mot_de_passe: str) -> Page:
    """Ouvre une session authentifiee et attend la redirection."""

    page.goto(f"{app_url}/login")
    page.fill("#email", email)
    page.fill("#password", mot_de_passe)
    page.get_by_role("button", name="Se connecter").click()
    page.wait_for_url(lambda url: "/login" not in url, timeout=25000)
    return page


@pytest.fixture
def admin_connecte(page: Page, environnement) -> Page:
    """Session authentifiee en tant qu'administrateur."""

    return _connecter(page, environnement.base_frontend, ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture
def secretariat_connecte(page: Page, environnement) -> Page:
    """Session authentifiee en tant que secretariat."""

    return _connecter(page, environnement.base_frontend, SECRETARY_EMAIL, SECRETARY_PASSWORD)


@pytest.fixture
def enseignant_connecte(page: Page, environnement) -> Page:
    """Session authentifiee en tant qu'enseignant."""

    return _connecter(page, environnement.base_frontend, TEACHER_EMAIL, TEACHER_PASSWORD)


@pytest.fixture
def etudiant_connecte(page: Page, environnement) -> Page:
    """Session authentifiee en tant qu'etudiant."""

    return _connecter(page, environnement.base_frontend, STUDENT_EMAIL, STUDENT_PASSWORD)


def journal_erreurs(problemes: list[str]) -> str:
    """Formate les problemes console pour un message d'echec lisible."""

    if not problemes:
        return "Aucun message console."
    uniques = list(dict.fromkeys(problemes))
    return "\n".join(f"  - {message}" for message in uniques[:12])
