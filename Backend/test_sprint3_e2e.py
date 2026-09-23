"""
Test de Bout en Bout (E2E) — Sprint 3 : Parcours Premier Lancement
Valide la chaîne complète :
1. Base vierge -> GET /setup/status retourne is_configured: False
2. Initialisation -> POST /setup/initialize crée Établissement, SuperAdmin, Session 2025-2026
3. Sécurité anti re-initialisation -> POST /setup/initialize retourne 409 Conflict
4. État configuré -> GET /setup/status retourne is_configured: True
5. Authentification -> POST /auth/login valide les identifiants et émet le JWT
6. Profil -> GET /auth/me restitue le profil SuperAdmin complet
"""

import asyncio
import os
import sys
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text

# Configuration de test sur base SQLite asynchrone isolée
TEST_DB_PATH = "test_sprint3_virgin.db"
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

# Forcer DATABASE_URL pour le test
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["TENANT_MODE"] = "standalone"

from app.core.config import settings
settings.DATABASE_URL = TEST_DB_URL
settings.TENANT_MODE = "standalone"

# Réinitialiser les caches de moteurs dans database.py
import app.core.database as db_module
db_module._engines_cache.clear()
db_module._sessionmakers_cache.clear()

import app.models
from app.main import app as fastapi_app
from app.models.base import Base


async def cleanup():
    # Disposer des connexions
    for eng in db_module._engines_cache.values():
        await eng.dispose()
    db_module._engines_cache.clear()
    db_module._sessionmakers_cache.clear()
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass


async def run_e2e_tests():
    print("==================================================================")
    print("   TEST DE BOUT EN BOUT SPRINT 3 : PARCOURS PREMIER LANCEMENT    ")
    print("==================================================================")

    await cleanup()

    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as client:

        # -------------------------------------------------------------------
        # ÉTAPE 1 : Test sur Base Vierge (GET /setup/status)
        # -------------------------------------------------------------------
        print("\n[TEST 1] Vérification sur base vierge (GET /api/v1/setup/status)...")
        r1 = await client.get("/api/v1/setup/status")
        assert r1.status_code == 200, f"Erreur status_code {r1.status_code}"
        data1 = r1.json()
        print("  Réponse:", data1)
        assert data1["is_configured"] is False, "Le système ne devrait pas être configuré sur une base vierge !"
        print("  -> SUCCÈS : is_configured est bien False.")

        # -------------------------------------------------------------------
        # ÉTAPE 2 : Premier Paramétrage (POST /setup/initialize)
        # -------------------------------------------------------------------
        print("\n[TEST 2] Exécution du Setup Wizard (POST /api/v1/setup/initialize)...")
        init_payload = {
            "etablissement": {
                "nom": "Institut Supérieur des Technologies & Management",
                "code": "ISTM",
                "adresse": "Boulevard de France, Cocody Riviera, Abidjan, Côte d'Ivoire",
                "telephone": "+225 27 22 00 00",
                "email": "contact@istm-edu.com",
                "devise": "FCFA",
                "license_key": "EMP-LIC-2026-ENTERPRISE-PRO"
            },
            "admin": {
                "nom": "Directeur",
                "prenom": "Principal",
                "email": "admin@edumanagepro.com",
                "password": "Admin@2026!",
                "telephone": "+225 07 00 00 01"
            },
            "init_default_academic_session": True
        }
        r2 = await client.post("/api/v1/setup/initialize", json=init_payload)
        assert r2.status_code == 201, f"Échec initialisation: {r2.status_code} - {r2.text}"
        data2 = r2.json()
        print("  Réponse:", {k: v for k, v in data2.items() if k != "access_token"})
        assert data2["success"] is True
        assert "access_token" in data2
        assert data2["user"]["email"] == "admin@edumanagepro.com"
        assert data2["user"]["role"] == "ADMIN"
        print("  -> SUCCÈS : Établissement, SuperAdmin et Session 2025-2026 créés avec succès !")

        # -------------------------------------------------------------------
        # ÉTAPE 3 : Sécurité Anti Re-initialisation (POST /setup/initialize)
        # -------------------------------------------------------------------
        print("\n[TEST 3] Tentative de ré-initialisation interdite (POST /api/v1/setup/initialize)...")
        r3 = await client.post("/api/v1/setup/initialize", json=init_payload)
        print("  Status code reçu:", r3.status_code)
        assert r3.status_code == 409, f"Devrait retourner 409 Conflict mais a retourné {r3.status_code}"
        print(f"  Détail erreur: {r3.json().get('detail')}")
        print("  -> SUCCÈS : Erreur 409 Conflict correctement déclenchée.")

        # -------------------------------------------------------------------
        # ÉTAPE 4 : Statut sur Base Initialisée (GET /setup/status)
        # -------------------------------------------------------------------
        print("\n[TEST 4] Vérification du statut après initialisation (GET /api/v1/setup/status)...")
        r4 = await client.get("/api/v1/setup/status")
        assert r4.status_code == 200
        data4 = r4.json()
        print("  Réponse:", data4)
        assert data4["is_configured"] is True
        assert data4["etablissement_nom"] == "Institut Supérieur des Technologies & Management"
        assert data4["etablissement_code"] == "ISTM"
        print("  -> SUCCÈS : Le système confirme is_configured = True (guidant vers /login).")

        # -------------------------------------------------------------------
        # ÉTAPE 5 : Authentification Login (POST /auth/login)
        # -------------------------------------------------------------------
        print("\n[TEST 5] Connexion avec mauvais mot de passe puis mot de passe valide...")
        # 5a. Mauvais mot de passe
        r5_bad = await client.post("/api/v1/auth/login", json={"email": "admin@edumanagepro.com", "password": "mauvaismotdepasse"})
        assert r5_bad.status_code == 401
        print("  [OK] Rejet identifiants invalides (401 Unauthorized):", r5_bad.json().get("detail"))

        # 5b. Bons identifiants créés lors du Setup
        r5 = await client.post("/api/v1/auth/login", json={"email": "admin@edumanagepro.com", "password": "Admin@2026!"})
        assert r5.status_code == 200
        data5 = r5.json()
        token = data5["access_token"]
        print("  [OK] Token JWT généré avec succès (Bearer):", token[:25] + "...")
        assert data5["user"]["email"] == "admin@edumanagepro.com"
        assert data5["user"]["role"] == "ADMIN"
        print("  -> SUCCÈS : Connexion SuperAdmin validée.")

        # -------------------------------------------------------------------
        # ÉTAPE 6 : Récupération du Profil Courant (GET /auth/me)
        # -------------------------------------------------------------------
        print("\n[TEST 6] Récupération du profil SuperAdmin connecté (GET /api/v1/auth/me)...")
        # 6a. Sans token
        r6_anon = await client.get("/api/v1/auth/me")
        assert r6_anon.status_code == 401
        print("  [OK] Accès anonyme refusé (401)")

        # 6b. Avec token
        r6 = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r6.status_code == 200
        data6 = r6.json()
        print("  Profil récupéré:", {
            "nom_complet": f"{data6['prenom']} {data6['nom']}",
            "email": data6["email"],
            "role": data6["role"],
            "is_superuser": data6["is_superuser"]
        })
        assert data6["email"] == "admin@edumanagepro.com"
        assert data6["role"] == "ADMIN"
        assert data6["is_superuser"] is True
        print("  -> SUCCÈS : Profil SuperAdmin validé avec les permissions intégrales.")

        # -------------------------------------------------------------------
        # ÉTAPE 7 : Vérification Session Académique & Tranches
        # -------------------------------------------------------------------
        print("\n[TEST 7] Vérification de la session active créée automatiquement...")
        r7 = await client.get("/api/v1/sessions/active")
        assert r7.status_code == 200
        data7 = r7.json()
        print(f"  Session: {data7['nom']} ({data7['code']}) - Statut: {data7['statut']}")
        print(f"  Tranches de paiement générées: {len(data7['periodes'])} tranches")
        assert len(data7['periodes']) == 10
        print("  Exemples de tranches:", [p["nom"] for p in data7["periodes"][:3]])
        print("  -> SUCCÈS : Calendrier de 10 tranches mensuelles vérifié.")

    await cleanup()
    print("\n==================================================================")
    print("   PARCOURS COMPLET SETUP -> LOGIN -> DASHBOARD VALIDÉ (7/7) !   ")
    print("==================================================================")


if __name__ == "__main__":
    asyncio.run(run_e2e_tests())
