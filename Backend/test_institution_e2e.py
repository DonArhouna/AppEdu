"""E2E de la configuration institutionnelle versionnee (SQLite isole).

Executable sans pytest :
    .\\venv\\Scripts\\python.exe test_institution_e2e.py

La base est un fichier temporaire sous %TEMP% : aucune instance locale n'est
touchee, aucun reset n'est effectue.

Le scenario verifie la chaine complete :

1. migration jusqu'a 0016 et presence de la permission ``institution.settings`` ;
2. lecture de la configuration : version 0, celle du Setup Wizard ;
3. **versionnement** : une ecriture reelle incremente la version, et
   l'historique conserve l'ancienne valeur champ par champ ;
4. **pas de version fantome** : renvoyer des valeurs identiques ne cree
   aucune version — sinon l'historique ne prouverait plus rien ;
5. logo : telechargement, validation sur les **octets** (un fichier qui n'est
   pas une image est refuse, meme s'il s'appelle ``logo.png``), service du
   fichier, retrait ;
6. traversee de repertoire refusee sur ``logo_url`` ;
7. permissions : le secretariat lit, ne modifie pas ; la permission dediee
   permet de deleguer a une direction sans ouvrir ``users.manage`` ;
8. le logo apparait dans le PDF emis, et le certificat reste valide apres
   son retrait.

Le point 8 est le plus important : une configuration qui n'atteint pas le
document officiel ne sert a rien.
"""

import asyncio
import gc
import os
import shutil
import sqlite3
import struct
import tempfile
import zlib
from pathlib import Path

from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient


TEST_DIR = Path(tempfile.gettempdir()) / "appedu-institution-e2e"
TEST_DB_PATH = TEST_DIR / "institution.db"
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
# Le logo du scenario doit rester dans %TEMP% : ecrire dans le dossier de
# runtime de production laisserait un fichier d'essai chez le client.
settings.BRANDING_STORAGE_DIR = str(TEST_DIR / "branding")
settings.DOCUMENTS_STORAGE_DIR = str(TEST_DIR / "documents")

import app.core.database as database  # noqa: E402

database._engines_cache.clear()
database._sessionmakers_cache.clear()

import app.models  # noqa: E402,F401
from app.main import app  # noqa: E402

ADMIN_EMAIL = "admin.institution@ecole-ci.org"
ADMIN_PASSWORD = "Institution-Admin-2026!"
SECRETARY_EMAIL = "secretariat.institution@ecole-ci.org"
SECRETARY_PASSWORD = "Institution-Secretary-2026!"
DIRECTOR_EMAIL = "direction.institution@ecole-ci.org"
DIRECTOR_PASSWORD = "Institution-Director-2026!"
TEACHER_EMAIL = "enseignant.institution@ecole-ci.org"
TEACHER_PASSWORD = "Institution-Teacher-2026!"

NOM_INITIAL = "Institut Institution E2E"
ADRESSE_INITIALE = ""


# ---------------------------------------------------------------------------
# Fabriques d'images
# ---------------------------------------------------------------------------
def _png(largeur: int = 240, hauteur: int = 120, couleur=(15, 76, 129), bruit: bool = False) -> bytes:
    """Fabrique un PNG valide sans dependance externe.

    Un logo de test doit etre un vrai PNG : c'est ce que la reconnaissance
    sur les octets verifie, et ce que ReportLab doit savoir rendre.

    ``bruit=True`` remplit l'image de donnees incompressibles, pour produire
    un PNG qui depasse reellement la limite de taille — une image d'une seule
    couleur se compresse a quelques kilo-octets et ne testerait rien.
    """

    def morceau(type_png: bytes, donnees: bytes) -> bytes:
        return (
            struct.pack(">I", len(donnees))
            + type_png
            + donnees
            + struct.pack(">I", zlib.crc32(type_png + donnees) & 0xFFFFFFFF)
        )

    if bruit:
        # Un octet de filtre par ligne, puis du bruit : incompressible.
        lignes = b"".join(b"\x00" + os.urandom(largeur * 3) for _ in range(hauteur))
    else:
        lignes = b"".join(b"\x00" + bytes(couleur) * largeur for _ in range(hauteur))
    entete = struct.pack(">IIBBBBB", largeur, hauteur, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + morceau(b"IHDR", entete)
        + morceau(b"IDAT", zlib.compress(lignes, 9))
        + morceau(b"IEND", b"")
    )


#: Fichier qui n'est pas une image, mais que le client pretendra etre un PNG.
FUSIONE_PNG = b"\x89PNG\r\n\x1a\n" + b"%PDF-1.7\n% contenu arbitraire\n"


def _contient_image(pdf: bytes) -> bool:
    """Le PDF contient-il un objet image ?

    ReportLab ecrit les images en XObject ``/Subtype /Image``. Le flux est
    souvent compresse, mais l'en-tete du dictionnaire reste en clair : c'est
    ce qu'on cherche.
    """

    return b"/Subtype /Image" in pdf or b"/Subtype/Image" in pdf


async def _cleanup() -> None:
    shutil.rmtree(TEST_DIR / "branding", ignore_errors=True)
    shutil.rmtree(TEST_DIR / "documents", ignore_errors=True)
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
    command.upgrade(config, "0015_documents_officiels")
    command.upgrade(config, "head")
    # Aller-retour : la migration doit etre reversible sans residue.
    command.downgrade(config, "0015_documents_officiels")
    command.upgrade(config, "head")


async def _login(client: AsyncClient, email: str, password: str) -> dict:
    reponse = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert reponse.status_code == 200, reponse.text
    return {"Authorization": f"Bearer {reponse.json()['access_token']}"}


async def _run() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://institution-test"
    ) as client:
        # ------------------------------------------------------------------
        # 1. Mise en place
        # ------------------------------------------------------------------
        setup = await client.post(
            "/api/v1/setup/initialize",
            json={
                "etablissement": {
                    "nom": NOM_INITIAL,
                    "code": "INST-E2E",
                    "adresse": ADRESSE_INITIALE,
                    "telephone": "",
                    "email": "contact@institution-e2e.org",
                    "devise": "XOF",
                },
                "admin": {
                    "email": ADMIN_EMAIL,
                    "nom": "Admin",
                    "prenom": "Institution",
                    "password": ADMIN_PASSWORD,
                },
            },
        )
        assert setup.status_code in (200, 201), f"Setup: {setup.status_code} {setup.text}"
        admin = await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)

        for email, password, role in (
            (SECRETARY_EMAIL, SECRETARY_PASSWORD, "SECRETARIAT"),
            (DIRECTOR_EMAIL, DIRECTOR_PASSWORD, "DIRECTEUR_ETUDES"),
            (TEACHER_EMAIL, TEACHER_PASSWORD, "ENSEIGNANT"),
        ):
            cree = await client.post(
                "/api/v1/users/",
                json={
                    "email": email, "nom": role, "prenom": "Institution",
                    "role": role, "password": password,
                },
                headers=admin,
            )
            assert cree.status_code == 201, cree.text

        # Socle minimal pour emettre ensuite un certificat avec le logo.
        filiere = await client.post(
            "/api/v1/structure/filieres",
            json={
                "nom": "Genie Logiciel Institution", "code": "GLI", "duree": 3,
                "diplome": "Licence", "niveau": "L1",
            },
            headers=admin,
        )
        assert filiere.status_code in (200, 201), filiere.text

        session_cree = await client.post(
            "/api/v1/sessions/",
            json={
                "nom": "Session Institution", "code": "SES-INST",
                "annee_academique": "2026-2027",
                "date_debut": "2026-10-01", "date_fin": "2027-07-31",
                "statut": "active",
            },
            headers=admin,
        )
        assert session_cree.status_code in (200, 201), session_cree.text
        session_id = session_cree.json()["id"]

        cycle_cree = await client.post(
            "/api/v1/academic/cycles",
            json={"nom": "Licence", "code": "LIC"}, headers=admin,
        )
        cycle_id = cycle_cree.json()["id"]
        niveau_cree = await client.post(
            "/api/v1/academic/niveaux",
            json={"code": "L1", "nom": "Licence 1", "cycle_id": cycle_id}, headers=admin,
        )
        niveau_id = niveau_cree.json()["id"]
        classe_creee = await client.post(
            "/api/v1/academic/classes",
            json={
                "code": "GLI-L1", "nom": "Genie Logiciel L1",
                "filiere_id": filiere.json()["id"], "niveau_id": niveau_id,
            },
            headers=admin,
        )
        classe_id = classe_creee.json()["id"]
        etudiant = (
            await client.post(
                "/api/v1/etudiants/",
                json={
                    "nom": "Etudiant", "prenom": "Institution",
                    "matricule": "INST-0001", "sexe": "M",
                    "date_naissance": "2004-01-15",
                    "filiere": "Genie Logiciel Institution", "niveau": "L1",
                    "classe_id": classe_id, "session_id": session_id,
                },
                headers=admin,
            )
        ).json()

        # ------------------------------------------------------------------
        # 2. Version 0 : la configuration du Setup Wizard
        # ------------------------------------------------------------------
        configuration = await client.get("/api/v1/institution/configuration", headers=admin)
        assert configuration.status_code == 200, configuration.text
        etat = configuration.json()
        assert etat["version"] == 0, etat
        assert etat["nom"] == NOM_INITIAL, etat
        assert etat["sigle"] == "INST-E2E", etat
        assert etat["devise"] == "XOF", etat
        assert etat["logo_present"] is False, etat

        historique = await client.get("/api/v1/institution/versions", headers=admin)
        assert historique.status_code == 200, historique.text
        assert historique.json() == [], historique.json()
        print("  [OK] Version 0 : configuration issue du Setup Wizard, historique vide.")

        # ------------------------------------------------------------------
        # 3. Une ecriture reelle incremente la version et trace l'ancien etat
        # ------------------------------------------------------------------
        maj = await client.put(
            "/api/v1/institution/configuration",
            json={"adresse": "Rue de l'Example 12, Cocody", "telephone": "+225 01 02 03 04"},
            headers=admin,
        )
        assert maj.status_code == 200, maj.text
        resultat = maj.json()
        assert resultat["version"] == 1, resultat
        modifications = resultat["modifications"]
        assert set(modifications) == {"adresse", "telephone"}, modifications
        # L'historique doit porter l'AVANT, sinon il ne sert a rien.
        assert modifications["adresse"]["avant"] == ADRESSE_INITIALE, modifications
        assert modifications["adresse"]["apres"] == "Rue de l'Example 12, Cocody"
        assert modifications["telephone"]["avant"] == "", modifications

        versions = (await client.get("/api/v1/institution/versions", headers=admin)).json()
        assert len(versions) == 1, versions
        assert versions[0]["version"] == 1, versions[0]
        assert versions[0]["nature"] == "etablissement", versions[0]
        assert versions[0]["modifie_par_email"] == ADMIN_EMAIL, versions[0]
        # Le snapshot doit permettre de restaurer sans rejouer l'historique.
        assert versions[0]["instantane"]["adresse"] == "Rue de l'Example 12, Cocody", (
            versions[0]
        )
        assert versions[0]["instantane"]["telephone"] == "+225 01 02 03 04", versions[0]
        assert versions[0]["logo_present"] is False, versions[0]
        print("  [OK] Version 1 : ecriture tracee, ancienne valeur conservee.")

        # ------------------------------------------------------------------
        # 4. Pas de version fantome
        # ------------------------------------------------------------------
        identique = await client.put(
            "/api/v1/institution/configuration",
            json={"adresse": "Rue de l'Example 12, Cocody", "telephone": "+225 01 02 03 04"},
            headers=admin,
        )
        assert identique.status_code == 200, identique.text
        assert identique.json()["version"] == 1, identique.json()
        assert identique.json()["modifications"] == {}, identique.json()

        # Meme valeur, espaces differents : ce n'est pas un changement.
        espaces = await client.put(
            "/api/v1/institution/configuration",
            json={"adresse": "  Rue de l'Example 12, Cocody  "}, headers=admin,
        )
        assert espaces.status_code == 200, espaces.text
        assert espaces.json()["modifications"] == {}, (
            "Des espaces de bord ne doivent pas produire une version : "
            f"{espaces.json()['modifications']}"
        )

        # Le nombre de versions n'a pas bouge.
        versions = (await client.get("/api/v1/institution/versions", headers=admin)).json()
        assert len(versions) == 1, versions

        # Mais un changement reel, si.
        devise = await client.put(
            "/api/v1/institution/configuration", json={"devise": "eur"}, headers=admin
        )
        assert devise.json()["version"] == 2, devise.json()
        assert devise.json()["configuration"]["devise"] == "EUR", devise.json()
        assert devise.json()["modifications"]["devise"] == {"avant": "XOF", "apres": "EUR"}
        versions = (await client.get("/api/v1/institution/versions", headers=admin)).json()
        assert len(versions) == 2, versions
        assert versions[0]["version"] == 2 and versions[1]["version"] == 1, versions
        # On revient a XOF pour la suite du scenario.
        await client.put(
            "/api/v1/institution/configuration", json={"devise": "XOF"}, headers=admin
        )
        print("  [OK] Versionnement : aucune version fantome, changement reel trace.")

        # ------------------------------------------------------------------
        # 5. Logo : validation par le decodeur reellement utilise au rendu
        # ------------------------------------------------------------------
        vrai_png = _png()

        # Un fichier qui n'est pas une image, nomme comme un PNG.
        deguise = await client.post(
            "/api/v1/institution/logo",
            files={"fichier": ("logo.png", FUSIONE_PNG, "image/png")},
            headers=admin,
        )
        assert deguise.status_code == 422, deguise.text
        assert "image" in deguise.json()["detail"].lower(), deguise.json()

        # Une signature JPEG suivie de donnees inexploitables : le fichier
        # « a l'air d'etre » un JPEG mais ne se decode pas. Il doit etre
        # refuse, car c'est exactement le fichier qui ne s'afficherait pas.
        jpeg_tronque = await client.post(
            "/api/v1/institution/logo",
            files={"fichier": ("logo.jpg", b"\xff\xd8\xff" + b"x" * 500, "image/jpeg")},
            headers=admin,
        )
        assert jpeg_tronque.status_code == 422, jpeg_tronque.text
        assert "image" in jpeg_tronque.json()["detail"].lower(), jpeg_tronque.json()

        # Fichier vide.
        vide = await client.post(
            "/api/v1/institution/logo",
            files={"fichier": ("logo.png", b"", "image/png")},
            headers=admin,
        )
        assert vide.status_code == 422, vide.text

        # Dimensions inadaptees : un PNG valide mais minuscule, illisible.
        minuscule = _png(largeur=8, hauteur=8)
        refuse_minuscule = await client.post(
            "/api/v1/institution/logo",
            files={"fichier": ("logo.png", minuscule, "image/png")},
            headers=admin,
        )
        assert refuse_minuscule.status_code == 422, refuse_minuscule.text
        assert "px" in refuse_minuscule.json()["detail"], refuse_minuscule.json()

        # Aucun de ces refus n'a rien ecrit sur le disque.
        assert sorted((TEST_DIR / "branding").glob("*")) == [], (
            "Un fichier refuse ne doit jamais atteindre le disque : "
            f"{sorted((TEST_DIR / 'branding').glob('*'))}"
        )

        # Trop volumineux : au-dela de la limite, refuse avant ecriture.
        trop_gros = _png(largeur=600, hauteur=600, bruit=True)
        assert len(trop_gros) > 512 * 1024, len(trop_gros)
        refuse_gros = await client.post(
            "/api/v1/institution/logo",
            files={"fichier": ("logo.png", trop_gros, "image/png")},
            headers=admin,
        )
        assert refuse_gros.status_code == 422, refuse_gros.text
        assert "Ko" in refuse_gros.json()["detail"], refuse_gros.json()

        print("  [OK] Logo : decodage reel exige, nom genere, rien d'ecrit sur un refus.")

        # Le PNG valide, lui, est accepte.
        accepte = await client.post(
            "/api/v1/institution/logo",
            files={"fichier": ("marque.png", vrai_png, "image/png")},
            headers=admin,
        )
        assert accepte.status_code == 200, accepte.text
        assert accepte.json()["configuration"]["logo_present"] is True, accepte.json()
        version_logo = accepte.json()["version"]
        # « absent » et non « present » : les fichiers refuses plus haut n'ont
        # jamais ete acceptes. C'est la preuve qu'un refus ne laisse pas de
        # trace a moitie appliquee.
        assert accepte.json()["modifications"] == {
            "logo": {"avant": "absent", "apres": "present"}
        }, accepte.json()["modifications"]
        # Le fichier precedent a ete supprime apres le commit.
        stockes = sorted(p.name for p in (TEST_DIR / "branding").glob("*"))
        assert len(stockes) == 1 and stockes[0].endswith(".png"), stockes
        assert stockes[0] != "marque.png", (
            f"Le nom d'origine ne doit pas etre reutilise : {stockes[0]}"
        )

        # ------------------------------------------------------------------
        # 6. Le logo est servi, et la traversee de repertoire est refusee
        # ------------------------------------------------------------------
        servi = await client.get("/api/v1/institution/logo", headers=admin)
        assert servi.status_code == 200, servi.headers
        assert servi.headers["content-type"] == "image/png", servi.headers
        assert servi.content == vrai_png, "Les octets servis doivent etre ceux du fichier."

        # Un logo_url pointant hors de la racine ne doit rien divulguer.
        from sqlalchemy import text as sql_text

        fabrique = database.get_sessionmaker_for_tenant("default")

        async def _pointer_ailleurs(chemin: str) -> None:
            async with fabrique() as session:
                await session.execute(
                    sql_text("UPDATE etablissements SET logo_url = :p"), {"p": chemin}
                )
                await session.commit()

        await _pointer_ailleurs("../../../Backend/.env")
        traversal = await client.get("/api/v1/institution/logo", headers=admin)
        assert traversal.status_code == 404, f"{traversal.status_code} {traversal.text}"
        await _pointer_ailleurs(stockes[0])
        print("  [OK] Logo servi tel quel ; traversee de repertoire refusee (404).")

        # ------------------------------------------------------------------
        # 7. Permissions
        # ------------------------------------------------------------------
        secretariat = await _login(client, SECRETARY_EMAIL, SECRETARY_PASSWORD)

        # Le secretariat voit l'identite qu'il va imprimer...
        lecture = await client.get("/api/v1/institution/configuration", headers=secretariat)
        assert lecture.status_code == 200, lecture.text
        assert lecture.json()["nom"] == NOM_INITIAL, lecture.json()
        logo_secretariat = await client.get("/api/v1/institution/logo", headers=secretariat)
        assert logo_secretariat.status_code == 200, logo_secretariat.status_code

        # ...mais ne la modifie pas.
        ecriture_secretariat = await client.put(
            "/api/v1/institution/configuration",
            json={"adresse": "Adresse imposee par le secretariat"}, headers=secretariat,
        )
        assert ecriture_secretariat.status_code == 403, ecriture_secretariat.text
        envoi_secretariat = await client.post(
            "/api/v1/institution/logo",
            files={"fichier": ("x.png", vrai_png, "image/png")}, headers=secretariat,
        )
        assert envoi_secretariat.status_code == 403, envoi_secretariat.text

        # Delegation : la permission dediee suffit, sans users.manage.
        direction_id = next(
            u["id"] for u in (await client.get("/api/v1/users/", headers=admin)).json()
            if u["email"] == DIRECTOR_EMAIL
        )
        roles = (await client.get("/api/v1/rbac/roles", headers=admin)).json()
        codes_roles = {r["code"] for r in roles}
        assert "ROLE_DIRECTEUR_ETUDES" in codes_roles, codes_roles

        attribue = await client.put(
            "/api/v1/rbac/roles/ROLE_DIRECTEUR_ETUDES/permissions",
            json={"permissions": ["institution.settings"]},
            headers=admin,
        )
        assert attribue.status_code == 200, attribue.text
        affecte = await client.post(
            "/api/v1/rbac/roles/ROLE_DIRECTEUR_ETUDES/users",
            json={"user_ids": [direction_id]},
            headers=admin,
        )
        assert affecte.status_code == 200, affecte.text

        direction = await _login(client, DIRECTOR_EMAIL, DIRECTOR_PASSWORD)
        modif_direction = await client.put(
            "/api/v1/institution/configuration",
            json={"telephone": "+225 05 06 07 08"}, headers=direction,
        )
        assert modif_direction.status_code == 200, modif_direction.text
        # ...sans avoir gagne la gestion des comptes.
        assert (
            await client.get("/api/v1/users/", headers=direction)
        ).status_code == 403, "La delegation ne doit pas ouvrir users.manage."

        enseignant = await _login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
        refuse = await client.put(
            "/api/v1/institution/configuration",
            json={"nom": "Usurpation"}, headers=enseignant,
        )
        assert refuse.status_code == 403, refuse.text
        print("  [OK] Permissions : lecture au secretariat, ecriture delegable, enseignant refuse.")

        # ------------------------------------------------------------------
        # 8. Le logo atteint le PDF, et le certificat survit a son retrait
        # ------------------------------------------------------------------
        emis = await client.post(
            f"/api/v1/documents/etudiants/{etudiant['id']}",
            json={"type_document": "certificat_scolarite", "session_id": session_id},
            headers=admin,
        )
        assert emis.status_code == 201, emis.text
        document = emis.json()
        assert document["donnees"]["etablissement"]["logo_url"], (
            "L'instantane d'emission doit conserver le logo employe : "
            f"{document['donnees']['etablissement']}"
        )

        telecharge = await client.get(
            f"/api/v1/documents/{document['id']}/telecharger", headers=admin
        )
        assert telecharge.status_code == 200, telecharge.status_code
        assert telecharge.content.startswith(b"%PDF"), "Le document doit rester un PDF."
        # Verification reelle : le PDF doit contenir un objet image. Une
        # comparaison de taille ne prouverait rien — un logo minuscule peut
        # ne peser que quelques centaines d'octets.
        assert _contient_image(telecharge.content), (
            "Aucun objet image dans le PDF : le logo n'a pas ete incorpore."
        )

        # Retrait du logo : la configuration le dit, le document reste valable.
        retire = await client.delete("/api/v1/institution/logo", headers=admin)
        assert retire.status_code == 200, retire.text
        assert retire.json()["configuration"]["logo_present"] is False, retire.json()
        assert (
            await client.get("/api/v1/institution/logo", headers=admin)
        ).status_code == 404

        # L'instantane d'emission conserve la trace du logo employe.
        journal = await client.get("/api/v1/documents/", headers=admin)
        assert journal.status_code == 200, journal.text
        entree = next(
            d for d in journal.json() if d["id"] == document["id"]
        )
        assert entree["donnees"]["etablissement"]["logo_url"], (
            "Un document deja delivre doit garder l'identite sous laquelle il a ete emis."
        )
        assert (
            await client.get(
                f"/api/v1/documents/{document['id']}/telecharger", headers=admin
            )
        ).status_code == 200
        print("  [OK] Le logo atteint le PDF ; le document delivre survit a son retrait.")

        # ------------------------------------------------------------------
        # 9. Un logo disparu est signale, pas masque
        # ------------------------------------------------------------------
        from app.services.branding_service import racine_branding

        for fichier in racine_branding().glob("*"):
            fichier.unlink()
        orphelin = await client.get("/api/v1/institution/logo", headers=admin)
        assert orphelin.status_code == 404, orphelin.status_code
        configuration_orpheline = await client.get(
            "/api/v1/institution/configuration", headers=admin
        )
        assert configuration_orpheline.json()["logo_present"] is False, (
            "Un fichier absent ne doit pas laisser croire a un branding actif : "
            f"{configuration_orpheline.json()}"
        )

        # Cas negatif du test d'image : un document emis sans logo exploitable
        # ne doit contenir aucun objet image. Sans cette contre-verification,
        # le controle precedent ne prouverait rien.
        sans_logo = await client.post(
            f"/api/v1/documents/etudiants/{etudiant['id']}",
            json={"type_document": "certificat_scolarite", "session_id": session_id},
            headers=admin,
        )
        assert sans_logo.status_code == 201, sans_logo.text
        pdf_sans_logo = await client.get(
            f"/api/v1/documents/{sans_logo.json()['id']}/telecharger", headers=admin
        )
        assert pdf_sans_logo.status_code == 200, pdf_sans_logo.status_code
        assert not _contient_image(pdf_sans_logo.content), (
            "Un document emis sans logo exploitable ne doit pas embarquer "
            "d'image : le controle positif serait alors sans valeur."
        )
        print("  [OK] Contre-verification : document sans logo, aucune image embarquee.")
        print("  [OK] Logo enregistre mais fichier absent : signale, pas presente comme actif.")

    print("E2E configuration institutionnelle : OK")


if __name__ == "__main__":
    asyncio.run(_cleanup())
    shutil.rmtree(TEST_DIR, ignore_errors=True)
    try:
        _migrate()
        asyncio.run(_run())
    finally:
        asyncio.run(_cleanup())
        shutil.rmtree(TEST_DIR, ignore_errors=True)
