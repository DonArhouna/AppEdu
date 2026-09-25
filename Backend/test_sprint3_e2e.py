"""
Test de Bout en Bout (E2E) — Sprint 3 : Parcours Premier Lancement
Valide la chaîne complète :
1. Base vierge -> GET /setup/status retourne is_configured: False
2. Initialisation -> POST /setup/initialize crée uniquement l'établissement et le SuperAdmin
3. Sécurité anti re-initialisation -> POST /setup/initialize retourne 409 Conflict
4. État configuré -> GET /setup/status retourne is_configured: True
5. Authentification -> POST /auth/login valide les identifiants et émet le JWT
6. Profil -> GET /auth/me restitue le profil SuperAdmin complet
"""

import asyncio
import gc
import os
import shutil
import sqlite3
import time
from pathlib import Path
from alembic import command
from alembic.config import Config
from httpx import AsyncClient, ASGITransport

TEST_ESTABLISSEMENT = "Établissement Test EduManagePro"
TEST_ETABLISSEMENT_CODE = "EMP-TEST"
TEST_ADMIN_EMAIL = "admin@ecole-ci.org"
TEST_ADMIN_PASSWORD = "Test-Only-2026!Secure"

# Base SQLite isolée par défaut; la CI fournit une URL PostgreSQL temporaire.
TEST_DB_PATH = Path(__file__).resolve().parent / "test_sprint3_virgin.db"
TEST_STORAGE_PATH = Path(__file__).resolve().parent / "test_sprint3_uploads"
TEST_SQLITE_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH}"
TEST_DB_URL = os.getenv("TEST_DATABASE_URL", TEST_SQLITE_URL)
IS_SQLITE_TEST = TEST_DB_URL.startswith("sqlite+")

# Forcer DATABASE_URL et un stockage éphémère pour le test
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["ADMISSIONS_STORAGE_DIR"] = str(TEST_STORAGE_PATH)
os.environ["TENANT_MODE"] = "standalone"
os.environ["DEBUG"] = "False"

from app.core.config import settings
settings.DATABASE_URL = TEST_DB_URL
settings.TENANT_MODE = "standalone"
settings.ADMISSIONS_STORAGE_DIR = TEST_STORAGE_PATH
settings.DEBUG = False

# Réinitialiser les caches de moteurs dans database.py
import app.core.database as db_module
db_module._engines_cache.clear()
db_module._sessionmakers_cache.clear()

import app.models
from app.main import app as fastapi_app


async def cleanup():
    # Disposer des connexions
    for eng in db_module._engines_cache.values():
        await eng.dispose()
    db_module._engines_cache.clear()
    db_module._sessionmakers_cache.clear()
    if IS_SQLITE_TEST and TEST_DB_PATH.exists():
        gc.collect()
        for _ in range(5):
            try:
                TEST_DB_PATH.unlink()
                break
            except OSError:
                try:
                    sqlite3.connect(str(TEST_DB_PATH)).close()
                except sqlite3.Error:
                    pass
                await asyncio.sleep(0.2)
    if TEST_STORAGE_PATH.exists():
        shutil.rmtree(TEST_STORAGE_PATH, ignore_errors=True)


async def run_e2e_tests():
    print("==================================================================")
    print("   TEST DE BOUT EN BOUT SPRINT 3 : PARCOURS PREMIER LANCEMENT    ")
    print("==================================================================")

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
                "nom": TEST_ESTABLISSEMENT,
                "code": TEST_ETABLISSEMENT_CODE,
                "adresse": "Adresse de test",
                "telephone": "",
                "email": "contact@ecole-ci.org",
                "devise": "XOF"
            },
            "admin": {
                "nom": "Admin",
                "prenom": "Test",
                "email": TEST_ADMIN_EMAIL,
                "password": TEST_ADMIN_PASSWORD
            }
        }
        if IS_SQLITE_TEST:
            r2 = await client.post("/api/v1/setup/initialize", json=init_payload)
            setup_responses = [r2]
        else:
            setup_responses = list(
                await asyncio.gather(
                    client.post("/api/v1/setup/initialize", json=init_payload),
                    client.post("/api/v1/setup/initialize", json=init_payload),
                )
            )
            assert sorted(response.status_code for response in setup_responses) == [201, 409]
            r2 = next(response for response in setup_responses if response.status_code == 201)
        assert r2.status_code == 201, f"Échec initialisation: {r2.status_code} - {r2.text}"
        data2 = r2.json()
        print("  Réponse:", {k: v for k, v in data2.items() if k != "access_token"})
        assert data2["success"] is True
        assert "access_token" in data2
        assert data2["user"]["email"] == TEST_ADMIN_EMAIL
        assert data2["user"]["role"] == "ADMIN"
        print("  -> SUCCÈS : Établissement et SuperAdmin créés, sans donnée métier implicite.")

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
        assert data4["etablissement_nom"] == TEST_ESTABLISSEMENT
        assert data4["etablissement_code"] == TEST_ETABLISSEMENT_CODE
        print("  -> SUCCÈS : Le système confirme is_configured = True (guidant vers /login).")

        # -------------------------------------------------------------------
        # ÉTAPE 5 : Authentification Login (POST /auth/login)
        # -------------------------------------------------------------------
        print("\n[TEST 5] Connexion avec mauvais mot de passe puis mot de passe valide...")
        # 5a. Mauvais mot de passe
        r5_bad = await client.post("/api/v1/auth/login", json={"email": TEST_ADMIN_EMAIL, "password": "mauvais-mot-de-passe"})
        assert r5_bad.status_code == 401
        print("  [OK] Rejet identifiants invalides (401 Unauthorized):", r5_bad.json().get("detail"))

        # 5b. Bons identifiants créés lors du Setup
        r5 = await client.post("/api/v1/auth/login", json={"email": TEST_ADMIN_EMAIL, "password": TEST_ADMIN_PASSWORD})
        assert r5.status_code == 200
        data5 = r5.json()
        token = data5["access_token"]
        print("  [OK] Token JWT généré avec succès (Bearer):", token[:25] + "...")
        assert data5["user"]["email"] == TEST_ADMIN_EMAIL
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
        assert data6["email"] == TEST_ADMIN_EMAIL
        assert data6["role"] == "ADMIN"
        assert data6["is_superuser"] is True
        print("  -> SUCCÈS : Profil SuperAdmin validé avec les permissions intégrales.")

        profile_update = await client.patch(
            "/api/v1/auth/me",
            json={"telephone": "+0000000000"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert profile_update.status_code == 200, profile_update.text
        assert profile_update.json()["telephone"] == "+0000000000"
        password_update = await client.post(
            "/api/v1/auth/me/password",
            json={"current_password": TEST_ADMIN_PASSWORD, "new_password": "Test-Only-2026!Updated"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert password_update.status_code == 204, password_update.text
        print("  [OK] Modification du profil et du mot de passe via l'API.")

        # -------------------------------------------------------------------
        # ÉTAPE 7 : Protection des données métier & session académique
        # -------------------------------------------------------------------
        print("\n[TEST 7] Vérification des accès protégés et création API d'une session...")
        protected_paths = [
            "/api/v1/etudiants/",
            "/api/v1/pedagogie/notes",
            "/api/v1/finances/paiements/paiement-non-authorise",
        ]
        for protected_path in protected_paths:
            anonymous = await client.get(protected_path)
            assert anonymous.status_code == 401, (
                f"{protected_path} doit refuser l'accès anonyme, reçu {anonymous.status_code}"
            )
        print("  [OK] Données étudiants, notes et paiements refusées sans JWT.")

        auth_headers = {"Authorization": f"Bearer {token}"}
        session_payload = {
            "nom": "Session E2E",
            "code": "SES-E2E-2026",
            "annee_academique": "2026-2027",
            "date_debut": "2026-09-01",
            "date_fin": "2027-07-31",
            "statut": "active",
            "description": "Session créée explicitement par le test",
            "periodes": [
                {
                    "nom": "Première échéance",
                    "mois": "Octobre",
                    "date_echeance": "2026-10-15",
                    "montant_estime": 1000,
                    "pourcentage": 50,
                    "ordre": 1,
                },
                {
                    "nom": "Deuxième échéance",
                    "mois": "Février",
                    "date_echeance": "2027-02-15",
                    "montant_estime": 1000,
                    "pourcentage": 50,
                    "ordre": 2,
                },
            ],
        }
        created = await client.post("/api/v1/sessions/", json=session_payload, headers=auth_headers)
        assert created.status_code == 201, f"Création session impossible: {created.text}"

        r7 = await client.get("/api/v1/sessions/active", headers=auth_headers)
        assert r7.status_code == 200
        data7 = r7.json()
        assert data7["code"] == session_payload["code"]
        assert len(data7["periodes"]) == 2
        context_response = await client.get("/api/v1/context/academique", headers=auth_headers)
        assert context_response.status_code == 200, context_response.text
        assert context_response.json()["annee_academique"] == session_payload["annee_academique"]
        context_update = await client.put(
            "/api/v1/context/academique",
            json={
                "annee_academique": session_payload["annee_academique"],
                "session_id": data7["id"],
            },
            headers=auth_headers,
        )
        assert context_update.status_code == 200, context_update.text
        assert context_update.json()["configuree"] is True
        assert context_update.json()["session_id"] == data7["id"]
        print("  [OK] Contexte academic global et session courante configures via l'API.")

        campus_response = await client.post(
            "/api/v1/structure/campuses",
            json={
                "nom": "Campus E2E",
                "code": "CAMP-E2E",
                "description": "Campus de test",
            },
            headers=auth_headers,
        )
        assert campus_response.status_code == 201, campus_response.text
        campus_id = campus_response.json()["id"]
        department_response = await client.post(
            "/api/v1/structure/departements",
            json={
                "nom": "Département E2E",
                "code": "DEP-E2E",
                "campus_id": campus_id,
            },
            headers=auth_headers,
        )
        assert department_response.status_code == 201, department_response.text
        department_id = department_response.json()["id"]
        filiere_response = await client.post(
            "/api/v1/structure/filieres",
            json={
                "nom": "Filière E2E",
                "code": "E2E",
                "diplome": "Licence",
                "duree": 3,
                "departement_id": department_id,
            },
            headers=auth_headers,
        )
        assert filiere_response.status_code == 201, filiere_response.text
        filiere_id = filiere_response.json()["id"]
        campuses_hierarchy = await client.get("/api/v1/structure/campuses", headers=auth_headers)
        assert campuses_hierarchy.status_code == 200, campuses_hierarchy.text
        assert any(
            any(filiere["id"] == filiere_id for filiere in departement["filieres"])
            for campus in campuses_hierarchy.json()
            for departement in campus["departements"]
        )

        candidature_response = await client.post(
            "/api/v1/admissions/candidatures",
            json={
                "nom": "Candidat",
                "prenom": "Admission",
                "email": "candidat.admission@ecole-ci.org",
                "telephone": "+0000000000",
                "filiere_id": filiere_id,
                "niveau": "Licence 1",
                "session_id": data7["id"],
                "source": "E2E",
            },
            headers=auth_headers,
        )
        assert candidature_response.status_code == 201, candidature_response.text
        candidature_data = candidature_response.json()
        candidature_id = candidature_data["id"]
        assert candidature_data["statut"] == "nouvelle"
        assert candidature_data["reference"].startswith("CAND-")

        bulk_candidate_response = await client.post(
            "/api/v1/admissions/candidatures",
            json={
                "nom": "Candidat",
                "prenom": "Groupe",
                "email": "candidat.groupe@ecole-ci.org",
                "filiere_id": filiere_id,
                "niveau": "Licence 1",
                "session_id": data7["id"],
            },
            headers=auth_headers,
        )
        assert bulk_candidate_response.status_code == 201, bulk_candidate_response.text
        bulk_candidate_id = bulk_candidate_response.json()["id"]
        saved_view_response = await client.post(
            "/api/v1/admissions/vues",
            json={"nom": "Nouvelles E2E", "filtres": {"statut": "nouvelle"}},
            headers=auth_headers,
        )
        assert saved_view_response.status_code == 201, saved_view_response.text
        saved_view_id = saved_view_response.json()["id"]
        saved_views = await client.get("/api/v1/admissions/vues", headers=auth_headers)
        assert saved_views.status_code == 200
        assert any(view["id"] == saved_view_id for view in saved_views.json())
        updated_view = await client.put(
            f"/api/v1/admissions/vues/{saved_view_id}",
            json={"nom": "Nouvelles E2E mise à jour", "filtres": {"statut": "en_verification"}},
            headers=auth_headers,
        )
        assert updated_view.status_code == 200, updated_view.text
        assert updated_view.json()["filtres"]["statut"] == "en_verification"
        bulk_action_response = await client.post(
            "/api/v1/admissions/candidatures/actions",
            json={"ids": [bulk_candidate_id], "action": "mettre_en_verification"},
            headers=auth_headers,
        )
        assert bulk_action_response.status_code == 200, bulk_action_response.text
        assert bulk_action_response.json()["updated_ids"] == [bulk_candidate_id]
        bulk_detail = await client.get(
            f"/api/v1/admissions/candidatures/{bulk_candidate_id}",
            headers=auth_headers,
        )
        assert bulk_detail.json()["statut"] == "en_verification"
        deleted_view = await client.delete(
            f"/api/v1/admissions/vues/{saved_view_id}", headers=auth_headers
        )
        assert deleted_view.status_code == 204

        premature_decision = await client.post(
            f"/api/v1/admissions/candidatures/{candidature_id}/decisions",
            json={"decision": "acceptee"},
            headers=auth_headers,
        )
        assert premature_decision.status_code == 409

        verification_response = await client.patch(
            f"/api/v1/admissions/candidatures/{candidature_id}/statut",
            json={"statut": "en_verification"},
            headers=auth_headers,
        )
        assert verification_response.status_code == 200, verification_response.text

        piece_response = await client.post(
            f"/api/v1/admissions/candidatures/{candidature_id}/pieces",
            json={"type": "Diplôme", "nom_fichier": "diplome-e2e.pdf"},
            headers=auth_headers,
        )
        assert piece_response.status_code == 201, piece_response.text
        piece_id = piece_response.json()["id"]
        incomplete_status = await client.patch(
            f"/api/v1/admissions/candidatures/{candidature_id}/statut",
            json={"statut": "complete"},
            headers=auth_headers,
        )
        assert incomplete_status.status_code == 422
        uploaded_piece = await client.post(
            f"/api/v1/admissions/pieces/{piece_id}/fichier",
            files={"file": ("diplome-e2e.pdf", b"%PDF-1.4\nE2E document", "application/pdf")},
            headers=auth_headers,
        )
        assert uploaded_piece.status_code == 201, uploaded_piece.text
        assert uploaded_piece.json()["fichier_disponible"] is True
        assert "chemin_stockage" not in uploaded_piece.json()
        downloaded_piece = await client.get(
            f"/api/v1/admissions/pieces/{piece_id}/fichier",
            headers=auth_headers,
        )
        assert downloaded_piece.status_code == 200
        assert downloaded_piece.content.startswith(b"%PDF-1.4")
        assert TEST_STORAGE_PATH.exists()
        invalid_upload = await client.post(
            f"/api/v1/admissions/pieces/{piece_id}/fichier",
            files={"file": ("piece.exe", b"MZnot-allowed", "application/octet-stream")},
            headers=auth_headers,
        )
        assert invalid_upload.status_code == 422
        received_piece = await client.put(
            f"/api/v1/admissions/pieces/{piece_id}",
            json={"statut": "recue"},
            headers=auth_headers,
        )
        assert received_piece.status_code == 200
        validated_piece = await client.put(
            f"/api/v1/admissions/pieces/{piece_id}",
            json={"statut": "validee"},
            headers=auth_headers,
        )
        assert validated_piece.status_code == 200
        complete_response = await client.patch(
            f"/api/v1/admissions/candidatures/{candidature_id}/statut",
            json={"statut": "complete"},
            headers=auth_headers,
        )
        assert complete_response.status_code == 200
        decision_response = await client.post(
            f"/api/v1/admissions/candidatures/{candidature_id}/decisions",
            json={"decision": "acceptee", "motif": "Dossier complet"},
            headers=auth_headers,
        )
        assert decision_response.status_code == 201, decision_response.text
        assert decision_response.json()["statut"] == "acceptee"
        bypass_conversion = await client.patch(
            f"/api/v1/admissions/candidatures/{candidature_id}/statut",
            json={"statut": "converti"},
            headers=auth_headers,
        )
        assert bypass_conversion.status_code == 422
        conversion_response = await client.post(
            f"/api/v1/admissions/candidatures/{candidature_id}/convertir",
            headers=auth_headers,
        )
        assert conversion_response.status_code == 201, conversion_response.text
        converted_student_id = conversion_response.json()["etudiant"]["id"]
        assert conversion_response.json()["candidature"]["statut"] == "converti"
        users_after_conversion = await client.get("/api/v1/users/", headers=auth_headers)
        assert users_after_conversion.status_code == 200
        assert all(
            user["email"] != "candidat.admission@ecole-ci.org"
            for user in users_after_conversion.json()
        )
        candidature_list = await client.get(
            "/api/v1/admissions/candidatures",
            params={"search": candidature_data["reference"]},
            headers=auth_headers,
        )
        assert candidature_list.status_code == 200
        assert candidature_list.json()["page"] == 1
        assert candidature_list.json()["page_size"] == 20
        assert candidature_list.json()["total"] == 1
        assert any(
            item["id"] == candidature_id for item in candidature_list.json()["items"]
        )
        candidature_detail = await client.get(
            f"/api/v1/admissions/candidatures/{candidature_id}",
            headers=auth_headers,
        )
        assert candidature_detail.status_code == 200
        assert len(candidature_detail.json()["pieces"]) == 1
        assert len(candidature_detail.json()["decisions"]) == 1
        print("  [OK] Candidature, pièce, décision et conversion en dossier étudiant validées via l'API.")

        etudiant_response = await client.post(
            "/api/v1/etudiants/",
            json={
                "nom": "Etudiant",
                "prenom": "E2E",
                "email": "etudiant@ecole-ci.org",
                "filiere": "Filière E2E",
                "filiere_id": filiere_id,
                "niveau": "Licence 1",
                "statut": "actif",
                "session_id": data7["id"],
            },
            headers=auth_headers,
        )
        assert etudiant_response.status_code == 201, etudiant_response.text
        etudiant_id = etudiant_response.json()["id"]

        fee_response = await client.post(
            "/api/v1/finances/grilles-tarifaires",
            json={
                "filiere_id": filiere_id,
                "filiere": "Filière E2E",
                "niveau": "Licence 1",
                "droits_inscription": 100,
                "scolarite_mensuelle": 50,
                "nombre_mois": 2,
                "actif": True,
            },
            headers=auth_headers,
        )
        assert fee_response.status_code == 201, fee_response.text
        assert fee_response.json()["total_annuel"] == 200

        payment_response = await client.post(
            "/api/v1/finances/paiements",
            json={
                "etudiant_id": etudiant_id,
                "session_id": data7["id"],
                "periode_id": data7["periodes"][0]["id"],
                "montant": 50,
                "mode_paiement": "Espèces",
            },
            headers=auth_headers,
        )
        assert payment_response.status_code == 201, payment_response.text
        payment_id = payment_response.json()["id"]
        receipt_response = await client.get(
            f"/api/v1/finances/paiements/{payment_id}/recu",
            headers=auth_headers,
        )
        assert receipt_response.status_code == 200
        assert receipt_response.json()["donnees_json"]["etudiant"]["id"] == etudiant_id
        partial_payment_response = await client.post(
            "/api/v1/finances/paiements",
            json={
                "etudiant_id": etudiant_id,
                "session_id": data7["id"],
                "periode_id": data7["periodes"][0]["id"],
                "montant": 25,
                "mode_paiement": "Espèces",
            },
            headers=auth_headers,
        )
        assert partial_payment_response.status_code == 201, partial_payment_response.text
        print("  [OK] Filière, étudiant, grille tarifaire, paiements partiels et reçus validés via l'API.")

        user_response = await client.post(
            "/api/v1/users/",
            json={
                "nom": "Enseignant",
                "prenom": "E2E",
                "email": "enseignant@ecole-ci.org",
                "role": "ENSEIGNANT",
                "password": "Enseignant-2026!",
            },
            headers=auth_headers,
        )
        assert user_response.status_code == 201, user_response.text
        user_id = user_response.json()["id"]
        updated_user = await client.put(
            f"/api/v1/users/{user_id}",
            json={"telephone": "+0000000000"},
            headers=auth_headers,
        )
        assert updated_user.status_code == 200

        ue_response = await client.post(
            "/api/v1/structure/ues",
            json={
                "nom": "UE E2E",
                "code": "UE-E2E",
                "filiere_id": filiere_id,
                "credits": 6,
                "coefficient": 2,
                "heures": 30,
                "semestre": "S1",
                "niveau": "Licence 1",
            },
            headers=auth_headers,
        )
        assert ue_response.status_code == 201, ue_response.text
        ue_id = ue_response.json()["id"]
        matiere_response = await client.post(
            "/api/v1/structure/matieres",
            json={
                "nom": "Matière E2E",
                "code": "MAT-E2E",
                "ue_id": ue_id,
                "credits": 3,
                "coefficient": 1,
                "heures_cm": 10,
                "heures_td": 5,
                "heures_tp": 5,
            },
            headers=auth_headers,
        )
        assert matiere_response.status_code == 201, matiere_response.text
        matiere_id = matiere_response.json()["id"]
        cours_response = await client.post(
            "/api/v1/pedagogie/cours",
            json={
                "matiere_id": matiere_id,
                "enseignant_id": user_id,
                "salle": "Salle E2E",
                "jour_semaine": "Lundi",
                "heure_debut": "08:00",
                "heure_fin": "10:00",
                "type_cours": "CM",
            },
            headers=auth_headers,
        )
        assert cours_response.status_code == 201, cours_response.text
        note_response = await client.post(
            "/api/v1/pedagogie/notes",
            json={
                "etudiant_id": etudiant_id,
                "matiere_id": matiere_id,
                "session_id": data7["id"],
                "valeur": 15,
                "coefficient": 2,
            },
            headers=auth_headers,
        )
        assert note_response.status_code == 201, note_response.text
        note_id = note_response.json()["id"]
        updated_note = await client.put(
            f"/api/v1/pedagogie/notes/{note_id}",
            json={"valeur": 16},
            headers=auth_headers,
        )
        assert updated_note.status_code == 200
        absence_response = await client.post(
            "/api/v1/pedagogie/absences",
            json={
                "etudiant_id": etudiant_id,
                "matiere_id": matiere_id,
                "session_id": data7["id"],
                "date_absence": "2026-10-01",
                "duree_heures": 2,
                "justifiee": True,
            },
            headers=auth_headers,
        )
        assert absence_response.status_code == 201, absence_response.text

        # Portail enseignant : les données sont filtrées par lidentity du compte.
        teacher_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "enseignant@ecole-ci.org", "password": "Enseignant-2026!"},
        )
        assert teacher_login.status_code == 200, teacher_login.text
        teacher_token = teacher_login.json()["access_token"]
        teacher_headers = {"Authorization": f"Bearer {teacher_token}"}
        teacher_global_registry = await client.get(
            "/api/v1/etudiants/", headers=teacher_headers
        )
        assert teacher_global_registry.status_code == 403
        teacher_assigned_students = await client.get(
            "/api/v1/pedagogie/etudiants-assignes",
            params={"matiere_id": matiere_id, "session_id": data7["id"]},
            headers=teacher_headers,
        )
        assert teacher_assigned_students.status_code == 200, teacher_assigned_students.text
        assert any(
            student["id"] == etudiant_id
            for student in teacher_assigned_students.json()
        )
        assert all(
            "email" not in student and "telephone" not in student
            for student in teacher_assigned_students.json()
        )
        external_filiere_response = await client.post(
            "/api/v1/structure/filieres",
            json={
                "nom": "Filière hors périmètre",
                "code": "E2X",
                "diplome": "Licence",
                "duree": 3,
                "departement_id": department_id,
            },
            headers=auth_headers,
        )
        assert external_filiere_response.status_code == 201
        external_student_response = await client.post(
            "/api/v1/etudiants/",
            json={
                "nom": "Hors",
                "prenom": "Perimetre",
                "filiere": "Filière hors périmètre",
                "filiere_id": external_filiere_response.json()["id"],
                "niveau": "Licence 1",
                "statut": "actif",
                "session_id": data7["id"],
            },
            headers=auth_headers,
        )
        assert external_student_response.status_code == 201
        external_student_id = external_student_response.json()["id"]
        teacher_note_without_session = await client.post(
            "/api/v1/pedagogie/notes",
            json={
                "etudiant_id": etudiant_id,
                "matiere_id": matiere_id,
                "valeur": 11,
                "coefficient": 1,
            },
            headers=teacher_headers,
        )
        assert teacher_note_without_session.status_code == 422
        teacher_out_of_scope_note = await client.post(
            "/api/v1/pedagogie/notes",
            json={
                "etudiant_id": external_student_id,
                "matiere_id": matiere_id,
                "session_id": data7["id"],
                "valeur": 12,
                "coefficient": 1,
            },
            headers=teacher_headers,
        )
        assert teacher_out_of_scope_note.status_code == 422
        teacher_absence_without_session = await client.post(
            "/api/v1/pedagogie/absences",
            json={
                "etudiant_id": etudiant_id,
                "matiere_id": matiere_id,
                "date_absence": "2026-10-02",
                "duree_heures": 1,
                "justifiee": False,
            },
            headers=teacher_headers,
        )
        assert teacher_absence_without_session.status_code == 422
        teacher_portal = await client.get("/api/v1/portail/enseignant", headers=teacher_headers)
        assert teacher_portal.status_code == 200, teacher_portal.text
        teacher_data = teacher_portal.json()
        assert any(cours["id"] == cours_response.json()["id"] for cours in teacher_data["cours"])
        assert any(note["id"] == note_response.json()["id"] for note in teacher_data["notes"])
        assert any(student["id"] == etudiant_id for student in teacher_data["etudiants"])
        teacher_wrong_portal = await client.get("/api/v1/portail/etudiant", headers=teacher_headers)
        assert teacher_wrong_portal.status_code == 403
        teacher_admissions = await client.get("/api/v1/admissions/candidatures", headers=teacher_headers)
        assert teacher_admissions.status_code == 403
        teacher_piece_download = await client.get(
            f"/api/v1/admissions/pieces/{piece_id}/fichier",
            headers=teacher_headers,
        )
        assert teacher_piece_download.status_code == 403
        teacher_context_update = await client.put(
            "/api/v1/context/academique",
            json={"annee_academique": "2099-2100", "session_id": None},
            headers=teacher_headers,
        )
        assert teacher_context_update.status_code == 403

        accounting_user_response = await client.post(
            "/api/v1/users/",
            json={
                "nom": "Comptabilité",
                "prenom": "E2E",
                "email": "comptabilite@ecole-ci.org",
                "role": "COMPTABILITE",
                "password": "Comptabilite-2026!",
            },
            headers=auth_headers,
        )
        assert accounting_user_response.status_code == 201, accounting_user_response.text
        accounting_user_id = accounting_user_response.json()["id"]
        accounting_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "comptabilite@ecole-ci.org", "password": "Comptabilite-2026!"},
        )
        assert accounting_login.status_code == 200, accounting_login.text
        accounting_headers = {
            "Authorization": f"Bearer {accounting_login.json()['access_token']}"
        }
        accounting_full_registry = await client.get(
            "/api/v1/etudiants/", headers=accounting_headers
        )
        assert accounting_full_registry.status_code == 403
        accounting_student_detail = await client.get(
            f"/api/v1/etudiants/{etudiant_id}", headers=accounting_headers
        )
        assert accounting_student_detail.status_code == 403
        accounting_summary = await client.get(
            "/api/v1/etudiants/summary", headers=accounting_headers
        )
        assert accounting_summary.status_code == 200, accounting_summary.text
        assert any(student["id"] == etudiant_id for student in accounting_summary.json())
        assert all(
            not ({"email", "telephone", "date_naissance", "adresse", "sexe", "photo_url"} & student.keys())
            for student in accounting_summary.json()
        )
        accounting_audit = await client.get(
            "/api/v1/audit/events", headers=accounting_headers
        )
        assert accounting_audit.status_code == 403

        # Portail étudiant : le compte est lié au dossier et ne voit pas le registre global.
        student_user_response = await client.post(
            "/api/v1/users/",
            json={
                "nom": "E2E",
                "prenom": "Etudiant",
                "email": "etudiant@ecole-ci.org",
                "role": "ETUDIANT",
                "password": "Etudiant-2026!",
                "etudiant_id": etudiant_id,
            },
            headers=auth_headers,
        )
        assert student_user_response.status_code == 201, student_user_response.text
        student_user_id = student_user_response.json()["id"]
        assert student_user_response.json()["etudiant_id"] == etudiant_id
        duplicate_student_account = await client.post(
            "/api/v1/users/",
            json={
                "nom": "Doublon",
                "prenom": "Etudiant",
                "email": "doublon.etudiant@ecole-ci.org",
                "role": "ETUDIANT",
                "password": "Doublon-2026!",
                "etudiant_id": etudiant_id,
            },
            headers=auth_headers,
        )
        assert duplicate_student_account.status_code == 409
        student_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "etudiant@ecole-ci.org", "password": "Etudiant-2026!"},
        )
        assert student_login.status_code == 200, student_login.text
        student_token = student_login.json()["access_token"]
        student_headers = {"Authorization": f"Bearer {student_token}"}
        student_portal = await client.get("/api/v1/portail/etudiant", headers=student_headers)
        assert student_portal.status_code == 200, student_portal.text
        student_data = student_portal.json()
        assert student_data["etudiant"]["id"] == etudiant_id
        assert all(facture["etudiant_id"] == etudiant_id for facture in student_data["factures"])
        assert any(cours["id"] == cours_response.json()["id"] for cours in student_data["cours"])
        student_global_registry = await client.get("/api/v1/etudiants/", headers=student_headers)
        assert student_global_registry.status_code == 403

        from app.core.database import async_session_factory
        from app.models.utilisateur import Utilisateur
        from app.services.user_security import (
            LastActiveAdministratorError,
            assert_not_last_active_administrator,
        )

        async with async_session_factory() as security_db:
            sole_admin = await security_db.get(Utilisateur, data2["user"]["id"])
            assert sole_admin is not None
            try:
                await assert_not_last_active_administrator(
                    security_db,
                    sole_admin,
                    target_role="SECRETARIAT",
                )
            except LastActiveAdministratorError:
                pass
            else:
                raise AssertionError("Le dernier administrateur actif a pu être rétrogradé")

        self_disable_admin = await client.put(
            f"/api/v1/users/{data2['user']['id']}",
            json={"is_active": False},
            headers=auth_headers,
        )
        assert self_disable_admin.status_code == 400
        self_delete_admin = await client.delete(
            f"/api/v1/users/{data2['user']['id']}", headers=auth_headers
        )
        assert self_delete_admin.status_code == 400
        audit_events = await client.get(
            "/api/v1/audit/events",
            params={"limit": 200},
            headers=auth_headers,
        )
        assert audit_events.status_code == 200, audit_events.text
        audit_actions = {event["action"] for event in audit_events.json()}
        assert "security.setup.initialized" in audit_actions
        assert "security.user.created" in audit_actions
        assert "security.user.updated" in audit_actions
        print("  [OK] Portails filtrés, registres protégés et journal d'audit validés.")

        deleted_accounting_user = await client.delete(
            f"/api/v1/users/{accounting_user_id}", headers=auth_headers
        )
        assert deleted_accounting_user.status_code == 204
        deleted_student_user = await client.delete(
            f"/api/v1/users/{student_user_id}", headers=auth_headers
        )
        assert deleted_student_user.status_code == 204
        deleted_teacher_user = await client.delete(
            f"/api/v1/users/{user_id}", headers=auth_headers
        )
        assert deleted_teacher_user.status_code == 204

        deleted_converted_student = await client.delete(
            f"/api/v1/etudiants/{converted_student_id}", headers=auth_headers
        )
        assert deleted_converted_student.status_code == 204

        deleted_student = await client.delete(
            f"/api/v1/etudiants/{etudiant_id}", headers=auth_headers
        )
        assert deleted_student.status_code == 204
        deleted_external_student = await client.delete(
            f"/api/v1/etudiants/{external_student_id}", headers=auth_headers
        )
        assert deleted_external_student.status_code == 204

        updated = await client.put(
            f"/api/v1/sessions/{data7['id']}",
            json={"description": "Session mise à jour par l'API", "statut": "cloturee"},
            headers=auth_headers,
        )
        assert updated.status_code == 200
        assert updated.json()["description"] == "Session mise à jour par l'API"

        deleted = await client.delete(
            f"/api/v1/sessions/{data7['id']}",
            headers=auth_headers,
        )
        assert deleted.status_code == 204
        print("  [OK] Modification et suppression de session validées.")

    print("\n==================================================================")
    print("   PARCOURS COMPLET SETUP -> LOGIN -> DASHBOARD VALIDÉ (7/7) !   ")
    print("==================================================================")


def migrate_test_database() -> None:
    """Construit la base de test avec le vrai chemin Alembic de production."""
    backend_dir = Path(__file__).resolve().parent
    alembic_config = Config(str(backend_dir / "alembic.ini"))
    command.upgrade(alembic_config, "head")


def remove_test_database_file() -> None:
    if not IS_SQLITE_TEST or not TEST_DB_PATH.exists():
        return
    for _ in range(10):
        try:
            TEST_DB_PATH.unlink()
            return
        except OSError:
            time.sleep(0.2)


if __name__ == "__main__":
    asyncio.run(cleanup())
    try:
        migrate_test_database()
        asyncio.run(run_e2e_tests())
    finally:
        asyncio.run(cleanup())
        remove_test_database_file()
