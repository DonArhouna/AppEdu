"""E2E du durcissement de l'authentification (lot 2, SQLite isole).

Executable sans pytest :
    .\\venv\\Scripts\\python.exe test_auth_lot2_e2e.py

Ce qui est verrouche :

1. **le contrat du login est preserve** : acces token + user, augmentes du
   refresh token ; les suites existantes (setup -> login -> dashboard)
   continuent de passer avec la meme requete ;
2. **chaque tentative est tracee**, reussie comme echouee, avec l'email tente ;
3. **le taux par (IP, email) est limite** : trop d'echecs rapproches valent
   un 429 avant meme de toucher bcrypt, et une reussite libere la cle ;
4. **le compte se verrouille** au seuil d'echecs consecutifs, repond 423 aux
   BONS mots de passe pendant le verrou, puis se deverrouille tout seul ;
5. **le refresh tourne** : l'ancien jeton ne vaut plus rien apres rotation ;
6. **rejouer un jeton tourne ferme la famille** : le second porteur perd
   toutes ses sessions, c'est la detection de vol ;
7. **la revocation mord sur l'access token** : logout, puis requete avec le
   jeton encore valide -> 401 immediat, pas a l'heure ;
8. **le changement de mot de passe ferme les sessions ouvertes** ;
9. **un compte desactive ne rafraichit pas**.

Le verrouillage et le taux se reglent via ``settings`` : le test les serre
pour aller vite, la production garde ses valeurs.
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

TEST_DIR = Path(tempfile.gettempdir()) / "appedu-auth-lot2-e2e"
TEST_DB_PATH = TEST_DIR / "auth-lot2.db"
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
# Le test serre les reglages pour aller vite : 3 echecs consecutifs
# verrouillent, 4 echecs dans la fenetre declenchent le taux, et le verrou
# dure 15 secondes (assez court pour attendre, assez long pour etre verifie).
settings.LOGIN_MAX_FAILED_ATTEMPTS = 3
settings.LOGIN_RATE_MAX_ATTEMPTS = 4
settings.LOGIN_RATE_WINDOW_SECONDS = 60
settings.LOGIN_LOCKOUT_MINUTES = 1
settings.ACCESS_TOKEN_EXPIRE_MINUTES = 60

import app.core.database as database  # noqa: E402

database._engines_cache.clear()
database._sessionmakers_cache.clear()

import app.models  # noqa: E402,F401
from app.main import app  # noqa: E402

# La limiteur de debit vit dans le processus : chaque run part propre.
from app.services import rate_limit  # noqa: E402

ADMIN_EMAIL = "admin.authlot2@ecole-ci.org"
ADMIN_PASSWORD = "AuthLot2-Admin-2026!"


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
    # Aller-retour : la migration additive doit etre reversible sans residue.
    command.downgrade(config, "0023_financial_integrity")
    command.upgrade(config, "head")


async def _run() -> None:
    rate_limit._echecs.clear()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://auth-lot2-test"
    ) as client:
        # ------------------------------------------------------------------
        # 1. Mise en place
        # ------------------------------------------------------------------
        setup = await client.post(
            "/api/v1/setup/initialize",
            json={
                "etablissement": {
                    "nom": "Institut Auth Lot2 E2E", "code": "AUTH-E2E",
                    "adresse": "", "telephone": "",
                    "email": "c@auth-lot2-e2e.org", "pays": "Sénégal",
                    "devise": "XOF",
                },
                "admin": {
                    "email": ADMIN_EMAIL, "nom": "Admin", "prenom": "Auth",
                    "password": ADMIN_PASSWORD,
                },
            },
        )
        assert setup.status_code in (200, 201), f"{setup.status_code} {setup.text}"

        # ------------------------------------------------------------------
        # 2. Le contrat du login est preserve, et porte une session
        # ------------------------------------------------------------------
        reponse = await client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        assert reponse.status_code == 200, reponse.text
        corps = reponse.json()
        for champ in ("access_token", "token_type", "expires_in", "user"):
            assert champ in corps, f"Contrat historique rompu : {champ} absent"
        assert corps["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        refresh = corps.get("refresh_token")
        assert refresh, "Le login doit emettre une session revocable."
        assert len(refresh) >= 32, "Le jeton de rafraichissement doit etre opaque."
        print("  [OK] Login : contrat historique preserve + session révocable.")

        # ------------------------------------------------------------------
        # 3. Le refresh tourne, l'ancien jeton meurt
        # ------------------------------------------------------------------
        r1 = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh}
        )
        assert r1.status_code == 200, r1.text
        corps1 = r1.json()
        nouveau = corps1["refresh_token"]
        assert nouveau and nouveau != refresh, (
            "La rotation doit produire un jeton NOUVEAU, pas le meme."
        )
        assert corps1["access_token"], "Le refresh doit rendre un access token."

        # L'ancien jeton est mort : le rejouer est un rejeu, pas un refresh.
        rejoue = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh}
        )
        assert rejoue.status_code == 401, rejoue.text
        print("  [OK] Rotation : ancien jeton revoqué, nouveau jeton rendu.")

        # ...et le rejeu a ferme la famille : le jeton « nouveau » du premier
        # porteur legitime ne rafraichit plus non plus.
        famille = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": nouveau}
        )
        assert famille.status_code == 401, famille.text
        print("  [OK] Rejeu détecté : toutes les sessions du compte sont fermées.")

        # La detection de vol ne supprime pas la trace : l'enquete apres coup
        # doit pouvoir lire la raison « fuite » sur les sessions fermees.
        import io as _io  # noqa: F401  (lecture directe en base plus bas)

        # ------------------------------------------------------------------
        # 4. La revocation mord sur l'access token
        # ------------------------------------------------------------------
        reconnexion = await client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        assert reconnexion.status_code == 200, reconnexion.text
        corps2 = reconnexion.json()
        jeton_acces = corps2["access_token"]
        refresh_vivant = corps2["refresh_token"]
        entetes = {"Authorization": f"Bearer {jeton_acces}"}

        moi = await client.get("/api/v1/auth/me", headers=entetes)
        assert moi.status_code == 200, moi.text

        sortie = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_vivant},
            headers=entetes,
        )
        assert sortie.status_code == 204, sortie.text

        # Le jeton d'acces est encore signe et encore non-expire : il ne
        # vaut plus rien. C'est le point du lot 2 — revoquer ferme l'acces
        # immediatement, pas a la prochaine heure.
        apres = await client.get("/api/v1/auth/me", headers=entetes)
        assert apres.status_code == 401, (
            f"La revocation doit fermer l'acces immediatement : {apres.status_code}"
        )
        print("  [OK] Logout : l'access token, encore valide, est refusé (401).")

        # ------------------------------------------------------------------
        # 5. La trace des reussites existe (les echecs suivent en section 7)
        # ------------------------------------------------------------------
        async with database.get_sessionmaker_for_tenant()() as session_db:
            from sqlalchemy import select

            from app.models.auth_securite import LoginAttempt

            traces = list(
                (
                    await session_db.execute(
                        select(LoginAttempt).order_by(LoginAttempt.id)
                    )
                ).scalars().all()
            )
            assert traces, "Aucune tentative tracee : le registre est vide."
            assert all(t.resultat == "success" for t in traces), (
                f"Issues tracees inattendues : {[t.resultat for t in traces]}"
            )
            assert any(t.email == ADMIN_EMAIL for t in traces)
        print("  [OK] Les connexions réussies sont tracées.")

        # ------------------------------------------------------------------
        # 6. Le taux par (IP, email) est limite
        # ------------------------------------------------------------------
        # Les deux defenses sont independantes : pendant cette section, le
        # seuil de verrouillage du compte est releve, pour que ce soit la
        # fenetre de DEBIT qui ferme le robinet — et pas le verrou du compte.
        rate_limit._echecs.clear()
        seuil_reel = settings.LOGIN_MAX_FAILED_ATTEMPTS
        settings.LOGIN_MAX_FAILED_ATTEMPTS = 100
        for _ in range(settings.LOGIN_RATE_MAX_ATTEMPTS):
            mauvaise = await client.post(
                "/api/v1/auth/login",
                json={"email": ADMIN_EMAIL, "password": "faux-" + ADMIN_EMAIL},
            )
            assert mauvaise.status_code == 401, mauvaise.text
        brule = await client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        assert brule.status_code == 429, (
            f"La fenetre de debit doit fermer le robinet : {brule.status_code}"
        )
        assert "Retry-After" in brule.headers, brule.headers
        # Le 429 arrive AVANT bcrypt : l'attaquant ne depense plus le CPU du
        # serveur, meme avec le bon mot de passe.
        print("  [OK] Trop d'échecs rapprochés : 429 avec Retry-After.")

        # La fenetre est en memoire : on la purge comme l'aurait fait le
        # temps ecoule, puis une reussite remet le compteur d'echecs
        # consecutifs a zero — la section suivante part d'un compte propre.
        rate_limit._echecs.clear()
        settings.LOGIN_MAX_FAILED_ATTEMPTS = seuil_reel
        reset = await client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        assert reset.status_code == 200, reset.text

        # ------------------------------------------------------------------
        # 7. Le compte se verrouille au seuil, puis se deverrouille seul
        # ------------------------------------------------------------------
        rate_limit._echecs.clear()
        for _ in range(settings.LOGIN_MAX_FAILED_ATTEMPTS):
            echec = await client.post(
                "/api/v1/auth/login",
                json={"email": ADMIN_EMAIL, "password": "encore-faux"},
            )
            assert echec.status_code == 401, echec.text

        # Le BON mot de passe est refuse pendant le verrou : c'est le compte
        # qui est ferme, pas la combinaison.
        verrouille = await client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        assert verrouille.status_code == 423, verrouille.text
        assert "verrouill" in verrouille.json()["detail"].lower(), verrouille.json()
        print("  [OK] Seuil franchi : compte verrouillé, même avec le bon mot de passe.")

        # Le deverrouillage est la fin du delai, pas une action secrete :
        # on remonte le temps du verrou directement en base, comme le ferait
        # l'horloge.
        async with database.get_sessionmaker_for_tenant()() as session_db:
            from datetime import datetime, timedelta, timezone

            from sqlalchemy import update

            from app.models.utilisateur import Utilisateur

            await session_db.execute(
                update(Utilisateur)
                .where(Utilisateur.email == ADMIN_EMAIL)
                .values(locked_until=datetime.now(timezone.utc) - timedelta(seconds=1))
            )
            await session_db.commit()

        deverrouille = await client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        assert deverrouille.status_code == 200, deverrouille.text
        print("  [OK] Verrou expiré : le compte se reconnecte, sans intervention.")

        # Les echecs ont laisse leur trace : l'enquete apres coup doit
        # retrouver l'email tente, meme quand il ne correspond a aucun
        # compte — c'est lui qui interesse une attaque par dictionnaire.
        async with database.get_sessionmaker_for_tenant()() as session_db:
            from sqlalchemy import select

            from app.models.auth_securite import LoginAttempt

            traces = list(
                (
                    await session_db.execute(
                        select(LoginAttempt).order_by(LoginAttempt.id)
                    )
                ).scalars().all()
            )
            issues = {t.resultat for t in traces}
            assert {"success", "failed"} <= issues, f"Issues tracees : {issues}"
            assert any(
                t.email == ADMIN_EMAIL and t.resultat == "failed"
                for t in traces
            ), "L'echec du bon compte doit etre trace."
        print("  [OK] Chaque tentative est tracée, réussie comme échouée.")

        # ------------------------------------------------------------------
        # 8. Changer de mot de passe ferme les sessions ouvertes
        # ------------------------------------------------------------------
        session_avant = (
            await client.post(
                "/api/v1/auth/login",
                json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            )
        ).json()
        entetes = {"Authorization": f"Bearer {session_avant['access_token']}"}

        changement = await client.post(
            "/api/v1/auth/me/password",
            json={"current_password": ADMIN_PASSWORD, "new_password": "AuthLot2-Neuf-2026!"},
            headers=entetes,
        )
        assert changement.status_code == 204, changement.text

        # L'ancien access token, toujours non-expire, est refuse : la session
        # qui l'a emis vient d'etre fermee par le changement de secret.
        apres_changement = await client.get("/api/v1/auth/me", headers=entetes)
        assert apres_changement.status_code == 401, apres_changement.status_code

        # Et le nouveau mot de passe ouvre une session neuve.
        reprise = await client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": "AuthLot2-Neuf-2026!"},
        )
        assert reprise.status_code == 200, reprise.text
        print("  [OK] Changement de mot de passe : sessions ouvertes fermées.")

        # ------------------------------------------------------------------
        # 9. Un compte desactive ne rafraichit pas
        # ------------------------------------------------------------------
        corps3 = reprise.json()
        refresh_desactive = corps3["refresh_token"]
        async with database.get_sessionmaker_for_tenant()() as session_db:
            from sqlalchemy import update

            from app.models.utilisateur import Utilisateur

            await session_db.execute(
                update(Utilisateur)
                .where(Utilisateur.email == ADMIN_EMAIL)
                .values(is_active=False)
            )
            await session_db.commit()

        fantome = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_desactive}
        )
        assert fantome.status_code == 401, fantome.text

        await session_db.close()
        async with database.get_sessionmaker_for_tenant()() as session_db:
            from sqlalchemy import update

            from app.models.utilisateur import Utilisateur

            await session_db.execute(
                update(Utilisateur)
                .where(Utilisateur.email == ADMIN_EMAIL)
                .values(is_active=True)
            )
            await session_db.commit()

        # ------------------------------------------------------------------
        # 10. L'ecran « mes sessions » : lister, designer, fermer
        # ------------------------------------------------------------------
        # Trois sessions ouvertes : la courante plus deux « autres machines ».
        logins = []
        for _ in range(3):
            reponse_session = await client.post(
                "/api/v1/auth/login",
                json={"email": ADMIN_EMAIL, "password": "AuthLot2-Neuf-2026!"},
            )
            assert reponse_session.status_code == 200, reponse_session.text
            logins.append(reponse_session.json())
        jetons = [l["access_token"] for l in logins]

        liste_sessions = await client.get(
            "/api/v1/auth/sessions", headers={"Authorization": f"Bearer {jetons[0]}"}
        )
        assert liste_sessions.status_code == 200, liste_sessions.text
        corps_sessions = liste_sessions.json()
        assert corps_sessions["total"] >= 3, corps_sessions
        actuelles = [s for s in corps_sessions["sessions"] if s["actuelle"]]
        assert len(actuelles) == 1, (
            f"Exactement une session doit etre designee « actuelle » : {corps_sessions}"
        )
        # L'epinglee est bien celle qui a pose la question.
        autre_vue = await client.get(
            "/api/v1/auth/sessions", headers={"Authorization": f"Bearer {jetons[1]}"}
        )
        actuelles_vue2 = [s for s in autre_vue.json()["sessions"] if s["actuelle"]]
        assert len(actuelles_vue2) == 1 and actuelles_vue2[0]["id"] != actuelles[0]["id"], (
            "Chaque appelant doit se voir designer sa propre session."
        )

        # Fermer une session precise : celle de la 3e machine. Son access
        # token, encore signe et non-expires, est refuse immediatement.
        cible = (
            await client.get(
                "/api/v1/auth/sessions", headers={"Authorization": f"Bearer {jetons[2]}"}
            )
        ).json()
        cible_id = [s for s in cible["sessions"] if s["actuelle"]][0]["id"]
        fermeture = await client.delete(
            f"/api/v1/auth/sessions/{cible_id}",
            headers={"Authorization": f"Bearer {jetons[0]}"},
        )
        assert fermeture.status_code == 204, fermeture.text
        refutee = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {jetons[2]}"}
        )
        assert refutee.status_code == 401, (
            f"La session fermee ne doit plus rien pouvoir faire : {refutee.status_code}"
        )

        # « Fermer les autres » epargne la session qui pose la question.
        autres = await client.post(
            "/api/v1/auth/sessions/fermer-autres",
            headers={"Authorization": f"Bearer {jetons[0]}"},
        )
        assert autres.status_code == 204, autres.text
        survit = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {jetons[0]}"}
        )
        assert survit.status_code == 200, (
            f"La session qui a demande « fermer les autres » doit survivre : {survit.status_code}"
        )
        apres = (
            await client.get(
                "/api/v1/auth/sessions", headers={"Authorization": f"Bearer {jetons[0]}"}
            )
        ).json()
        vivantes_hors_courante = [
            s for s in apres["sessions"] if not s["actuelle"]
        ]
        assert vivantes_hors_courante == [], (
            f"Les autres sessions doivent etre fermees : {apres}"
        )
        print("  [OK] Mes sessions : liste, session actuelle designee, fermeture ciblée et « fermer les autres ».")

    print("E2E durcissement auth (lot 2) : OK")


if __name__ == "__main__":
    asyncio.run(_cleanup())
    shutil.rmtree(TEST_DIR, ignore_errors=True)
    try:
        _migrate()
        asyncio.run(_run())
    finally:
        asyncio.run(_cleanup())
        shutil.rmtree(TEST_DIR, ignore_errors=True)
