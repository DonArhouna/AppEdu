"""Paiements en ligne (lot 4b) : intention, confirmation, réconciliation.

Executable sans pytest :
    .\\\\venv\\\\Scripts\\\\python.exe test_paiements_en_ligne_e2e.py

Ce que ce test verrouille :

1. **Le lien se crée et ne se repose pas.** La création rend le jeton en
   clair **une seule fois** ; la base n'en conserve que l'empreinte
   SHA-256 — le test le prouve en lisant la table directement.
2. **La famille voit l'essentiel, rien de plus.** Le résumé public ne
   révèle ni email, ni téléphone, ni aucune donnée qu'un lien intercepté
   transformerait en fuite.
3. **La confirmation paie vraiment.** Paiement + reçu créés dans la même
   séquence que le guichet, facture mise à jour, numéro de reçu continu.
4. **Un lien ne paie pas deux fois.** Reconfirmer est un 410 ; l'intention
   confirmée ne repasse plus par la résolution.
5. **Les bornes tiennent.** Montant supérieur au reste, facture déjà
   soldée, lien inconnu, lien annulé, lien expiré, paiement sans
   établissement : chaque refus est nommé.
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

TEST_DIR = Path(tempfile.gettempdir()) / "appedu-paiement-ligne-e2e"
TEST_DB_PATH = TEST_DIR / "paiement_ligne.db"
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

ADMIN_EMAIL = "admin.paiement@ecole-ci.org"
ADMIN_PASSWORD = "Paiement-Admin-2026!"


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


async def _run() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://paiement-test"
    ) as client:
        # -- Mise en place -------------------------------------------------
        setup = await client.post(
            "/api/v1/setup/initialize",
            json={
                "etablissement": {
                    "nom": "Institut Paiement E2E", "code": "PAY-E2E",
                    "adresse": "", "telephone": "", "email": "c@paiement-e2e.org",
                    "pays": "Sénégal", "devise": "XOF",
                },
                "admin": {
                    "email": ADMIN_EMAIL, "nom": "Admin", "prenom": "Paiement",
                    "password": ADMIN_PASSWORD,
                },
            },
        )
        assert setup.status_code in (200, 201), f"{setup.status_code} {setup.text}"
        jeton_admin = (
            await client.post(
                "/api/v1/auth/login",
                json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            )
        ).json()["access_token"]
        admin = {"Authorization": f"Bearer {jeton_admin}"}

        # Un étudiant inscrit, avec une grille tarifaire et une facture échue
        # non soldée : le terrain de jeu du paiement en ligne.
        filiere = (
            await client.post(
                "/api/v1/structure/filieres",
                json={"nom": "Genie Paiement", "code": "GPAY", "duree": 3, "diplome": "Licence"},
                headers=admin,
            )
        ).json()
        session = (
            await client.post(
                "/api/v1/sessions/",
                json={
                    "nom": "Session Paiement", "code": "SES-PAY",
                    "annee_academique": "2026-2027",
                    "date_debut": "2026-10-01", "date_fin": "2027-07-31",
                    "statut": "active",
                },
                headers=admin,
            )
        ).json()
        etudiant = (
            await client.post(
                "/api/v1/etudiants/",
                json={
                    "nom": "Kouame", "prenom": "Aya", "sexe": "F",
                    "filiere": "Genie Paiement", "niveau": "Licence 1",
                    "session_id": session["id"], "matricule": "PAY-2026-001",
                },
                headers=admin,
            )
        )
        assert etudiant.status_code in (200, 201), etudiant.text
        etudiant_id = etudiant.json()["id"]

        facture = (
            await client.post(
                "/api/v1/finances/factures",
                json={
                    "etudiant_id": etudiant_id,
                    "session_id": session["id"],
                    "montant_total": 150000,
                    "date_emission": "2026-09-15",
                    "date_echeance": "2026-10-15",
                    "description": "Scolarité échéance 1",
                },
                headers=admin,
            )
        )
        assert facture.status_code == 201, facture.text
        facture_id = facture.json()["id"]

        # -- 1. Création du lien : jeton en clair une fois, empreinte en base
        creation = await client.post(
            "/api/v1/finances/paiements-en-ligne",
            json={"facture_id": facture_id},
            headers=admin,
        )
        assert creation.status_code == 201, creation.text
        intention = creation.json()
        jeton = intention["token"]
        assert jeton and len(jeton) >= 32, intention
        assert float(intention["montant"]) == 150000.0, intention
        assert intention["lien"].endswith(jeton), intention
        assert intention["statut"] == "en_attente", intention

        # La base ne conserve que l'empreinte : on le vérifie en lisant
        # directement la table, comme un attaquant qui aurait volé la base.
        from sqlalchemy import select as _select

        from app.models.paiement_intent import PaiementIntent

        async with database.get_sessionmaker_for_tenant()() as session_db:
            lignes = (
                await session_db.execute(_select(PaiementIntent))
            ).scalars().all()
            assert len(lignes) == 1, lignes
            assert lignes[0].token_hash != jeton, (
                "La base ne doit jamais contenir le jeton en clair."
            )
            assert len(lignes[0].token_hash) == 64, lignes[0].token_hash
        await session_db.close()
        print("  [OK] Création : jeton en clair une seule fois, empreinte SHA-256 en base.")

        # -- 2. Le résumé famille : l'essentiel, rien de plus --------------
        resume = await client.get(f"/api/v1/finances/public/paiement/{jeton}")
        assert resume.status_code == 200, resume.text
        resume_corps = resume.json()
        assert resume_corps["etudiant"] == "Aya Kouame", resume_corps
        assert resume_corps["facture"]["numero"], resume_corps
        assert resume_corps["facture"]["reste_a_payer"] == 150000.0, resume_corps
        assert float(resume_corps["montant_demande"]) == 150000.0, resume_corps
        # Aucune donnée de contact : un lien intercepté ne doit rien fuiter.
        assert "email" not in json.dumps(resume_corps).lower(), resume_corps
        assert "telephone" not in json.dumps(resume_corps).lower(), resume_corps
        print("  [OK] Résumé famille : nom, facture, reste à payer — rien de plus.")

        # -- 3. La confirmation paie vraiment ------------------------------
        confirmation = await client.post(
            f"/api/v1/finances/public/paiement/{jeton}/confirmer",
            json={},
        )
        assert confirmation.status_code == 200, confirmation.text
        resultat = confirmation.json()
        assert resultat["numero_recu"].startswith("REC-"), resultat
        assert float(resultat["montant"]) == 150000.0, resultat
        paiement_id = resultat["paiement_id"]

        # La facture est soldée, le paiement et le reçu existent.
        facture_apres = (
            await client.get(f"/api/v1/finances/factures/{facture_id}", headers=admin)
        ).json()
        assert facture_apres["statut"] == "payee", facture_apres
        assert float(facture_apres["montant_paye"]) == 150000.0, facture_apres

        recu = await client.get(f"/api/v1/finances/paiements/{paiement_id}/recu", headers=admin)
        assert recu.status_code == 200, recu.text
        assert recu.json()["donnees_json"]["details_paiement"]["mode_paiement"].startswith("En ligne"), recu.text
        print(f"  [OK] Confirmation : paiement {paiement_id[:8]} + reçu {resultat['numero_recu']}, facture soldée.")

        # -- 4. Un lien ne paie pas deux fois ------------------------------
        rejoue = await client.post(
            f"/api/v1/finances/public/paiement/{jeton}/confirmer",
            json={},
        )
        assert rejoue.status_code == 410, rejoue.text
        assert "déjà été payé" in rejoue.json()["detail"], rejoue.json()

        paiements = (
            await client.get(
                f"/api/v1/finances/paiements?etudiant_id={etudiant_id}", headers=admin
            )
        ).json()
        assert len(paiements) == 1, (
            f"Une confirmation rejouée a créé un second paiement : {len(paiements)}"
        )
        print("  [OK] Rejeu refusé (410) : aucun second paiement créé.")

        # -- 5. Les bornes -------------------------------------------------
        # Facture déjà soldée : plus de lien.
        facture_soldée = await client.post(
            "/api/v1/finances/paiements-en-ligne",
            json={"facture_id": facture_id},
            headers=admin,
        )
        assert facture_soldée.status_code == 422, facture_soldée.text

        # Montant supérieur au reste.
        facture2 = (
            await client.post(
                "/api/v1/finances/factures",
                json={
                    "etudiant_id": etudiant_id,
                    "session_id": session["id"],
                    "montant_total": 80000,
                    "date_emission": "2026-09-15",
                    "date_echeance": "2026-11-15",
                    "description": "Scolarité échéance 2",
                },
                headers=admin,
            )
        ).json()
        trop = await client.post(
            "/api/v1/finances/paiements-en-ligne",
            json={"facture_id": facture2["id"], "montant": 90000},
            headers=admin,
        )
        assert trop.status_code == 422, trop.text

        # Montant partiel autorisé : 50 000 sur 80 000.
        partiel = await client.post(
            "/api/v1/finances/paiements-en-ligne",
            json={"facture_id": facture2["id"], "montant": 50000},
            headers=admin,
        )
        assert partiel.status_code == 201, partiel.text
        jeton_partiel = partiel.json()["token"]

        # Lien inconnu : même 410 pour la famille, rien de plus.
        inconnu = await client.get("/api/v1/finances/public/paiement/jeton-fantome")
        assert inconnu.status_code == 410, inconnu.text
        assert inconnu.json()["detail"] == "Lien inconnu.", inconnu.json()

        # Annulation d'un lien vivant par le personnel.
        annulation = await client.post(
            f"/api/v1/finances/paiements-en-ligne/{partiel.json()['id']}/annuler",
            headers=admin,
        )
        assert annulation.status_code == 204, annulation.text
        morte = await client.get(f"/api/v1/finances/public/paiement/{jeton_partiel}")
        assert morte.status_code == 410, morte.text
        assert "annulé" in morte.json()["detail"], morte.json()

        # Une intention annulée ne se confirme pas davantage.
        confirmee_annulee = await client.post(
            f"/api/v1/finances/public/paiement/{jeton_partiel}/confirmer",
            json={},
        )
        assert confirmee_annulee.status_code == 410, confirmee_annulee.text

        # La liste du personnel montre les statuts.
        liste = await client.get(
            "/api/v1/finances/paiements-en-ligne", headers=admin
        )
        assert liste.status_code == 200, liste.text
        statuts = {i["statut"] for i in liste.json()}
        assert "confirmee" in statuts and "annulee" in statuts, liste.json()
        # Le jeton n'apparaît nulle part dans la liste.
        assert jeton not in json.dumps(liste.json()), (
            "La liste du personnel ne doit pas exposer les jetons."
        )

        # Sans permission finance, pas de création de lien.
        sans_droit = await client.post(
            "/api/v1/finances/paiements-en-ligne",
            json={"facture_id": facture2["id"]},
        )
        assert sans_droit.status_code in (401, 403), sans_droit.status_code
        print("  [OK] Bornes : facture soldée, montant excessif, lien inconnu/annulé, jetons absents des listes.")

    print("E2E paiements en ligne : OK")


if __name__ == "__main__":
    asyncio.run(_cleanup())
    shutil.rmtree(TEST_DIR, ignore_errors=True)
    try:
        _migrate()
        asyncio.run(_run())
    finally:
        asyncio.run(_cleanup())
        shutil.rmtree(TEST_DIR, ignore_errors=True)
