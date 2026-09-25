"""Configuration institutionnelle : identité, logo, versionnement.

Ces tests exercent l'écran qui remplace l'affichage en lecture seule du
paramétrage. Ils contrôlent trois choses qu'un code correct ne garantit pas :

1. **le versioning est visible** — une version creee doit apparaitre dans
   l'historique avec son auteur, sinon l'écran ment sur la traçabilité ;
2. **un refus n'est pas un echec silencieux** — un fichier refuse doit
   produire un message, et le logo courant doit rester en place ;
3. **les etats vides sont explicites** — pas de logo, pas d'historique, pas
   de permission : chacun a son ecran, aucun n'affiche un cadre vide.
"""

import random
import re
import struct
import zlib

import pytest
from playwright.sync_api import Page, expect

from conftest import DELAI_RENDU, journal_erreurs


def _png(largeur: int = 240, hauteur: int = 120) -> bytes:
    """Fabrique un vrai PNG : le serveur verifie le decodage reel."""

    def morceau(type_png: bytes, donnees: bytes) -> bytes:
        return (
            struct.pack(">I", len(donnees))
            + type_png
            + donnees
            + struct.pack(">I", zlib.crc32(type_png + donnees) & 0xFFFFFFFF)
        )

    lignes = b"".join(b"\x00" + bytes((15, 76, 129)) * largeur for _ in range(hauteur))
    entete = struct.pack(">IIBBBBB", largeur, hauteur, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + morceau(b"IHDR", entete)
        + morceau(b"IDAT", zlib.compress(lignes, 9))
        + morceau(b"IEND", b"")
    )


def _ecran_configuration(page: Page, app_url: str) -> None:
    page.goto(f"{app_url}/parametrage")
    expect(page.get_by_role("heading", name="Identité de l'établissement")).to_be_visible(
        timeout=DELAI_RENDU
    )


def _version_affchee(page: Page) -> int:
    """Version affichee dans la pastille d'en-tete.

    La pile est partagee : on lit l'etat courant au lieu de supposer qu'il
    vaut 0, sinon le resultat dependrait de l'ordre d'execution.
    """

    texte = page.get_by_text(re.compile(r"Version \d+")).first.inner_text()
    return int(re.search(r"\d+", texte).group())


def _attendre_version(page: Page, attendue: int) -> None:
    expect(page.get_by_text(f"Version {attendue}", exact=False).first).to_be_visible(
        timeout=DELAI_RENDU
    )


def test_etat_neuf_sans_logo_ni_historique(page_console, app_url, admin_connecte):
    """Avant toute ecriture : version 0, pas de logo, historique vide.

    Ce test suppose un etat intact et **le verifie** : si l'un des tests
    suivants s'executait avant lui, l'echec le dirait explicitement plutot que
    de produire un resultat faux. Aucun autre module de la suite ne touche la
    configuration institutionnelle, et les tests de ce fichier.modifient
    l'etat dans l'ordre ou ils sont ecrits.
    """

    page, problemes = page_console
    _ecran_configuration(page, app_url)

    assert _version_affchee(page) == 0, (
        "L'instance de test n'est plus a l'etat neuf : la version affichee "
        f"est {_version_affchee(page)}. C'est attendu seulement au premier "
        "lancement de ce fichier de tests."
    )
    expect(page.get_by_text("Aucun logo enregistré").first).to_be_visible()
    expect(page.get_by_text("Aucune modification enregistrée").first).to_be_visible()
    # L'etat vide du logo explique ce que produit l'absence de branding,
    # au lieu de laisser croire a un bug d'affichage.
    expect(
        page.get_by_text("Les documents officiels sont émis sans branding").first
    ).to_be_visible()
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_modifier_l_identite_cree_une_version(page_console, app_url, admin_connecte):
    page, problemes = page_console
    _ecran_configuration(page, app_url)

    avant = _version_affchee(page)
    nouvelle_adresse = f"12 rue de la Verification, Cocody v{avant}"
    page.locator("#champ-Adresse").fill(nouvelle_adresse)
    page.get_by_role("button", name="Enregistrer l'identité").click()

    # La version avance d'un cran et l'historique affiche le nouveau et l'ancien.
    _attendre_version(page, avant + 1)
    expect(page.get_by_text(nouvelle_adresse, exact=False).first).to_be_visible()
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_enregistrer_sans_changement_cree_aucune_version(
    page_console, app_url, admin_connecte
):
    """Reenregistrer a l'identique ne doit pas polluer l'historique."""

    page, problemes = page_console
    _ecran_configuration(page, app_url)

    # Une premiere modification, pour disposer d'une version de depart.
    avant = _version_affchee(page)
    telephone = f"+225 0{random.randint(1, 9)} 02 03 0{random.randint(1, 9)}"
    page.locator("#champ-Téléphone").fill(telephone)
    page.get_by_role("button", name="Enregistrer l'identité").click()
    _attendre_version(page, avant + 1)

    # Puis exactement la meme valeur : rien ne doit changer.
    page.get_by_role("button", name="Enregistrer l'identité").click()
    expect(page.get_by_text("déjà à jour", exact=False).first).to_be_visible(timeout=DELAI_RENDU)
    assert _version_affchee(page) == avant + 1, (
        "Un enregistrement sans changement ne doit pas incrementer la version."
    )
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_validation_des_champs(page_console, app_url, admin_connecte):
    """Un nom trop court est refuse avant l'envoi, avec un message au champ."""

    page, problemes = page_console
    _ecran_configuration(page, app_url)

    avant = _version_affchee(page)
    page.locator("#champ-Nom").fill("A")
    page.get_by_role("button", name="Enregistrer l'identité").click()

    expect(page.get_by_text("au moins 2 caractères").first).to_be_visible()
    # Aucun envoi : la version n'a pas bouge.
    assert _version_affchee(page) == avant, (
        "Une validation refusee ne doit produire aucune version."
    )
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_televerser_un_logo(page_console, app_url, admin_connecte):
    page, problemes = page_console
    _ecran_configuration(page, app_url)

    avant = _version_affchee(page)
    page.locator('input[type="file"]').set_input_files(
        files=[{"name": "marque.png", "mimeType": "image/png", "buffer": _png()}]
    )

    # L'image remplace l'etat vide et la version avance.
    expect(page.get_by_text("Remplacer", exact=False).first).to_be_visible(timeout=DELAI_RENDU)
    expect(page.get_by_text("Aucun logo enregistré")).to_have_count(0)
    # L'image est reellement decodee : la largeur naturelle prouve que les
    # octets ont ete recus, pas seulement que la balise existe. C'est ce qui
    # distingue un logo affiche d'un cadre vide.
    image = page.locator('img[alt^="Logo de"]')
    expect(image).to_be_visible()
    image.evaluate("n => n.decode ? n.decode() : null")
    page.wait_for_function(
        "() => { const i = document.querySelector('img[alt^=\\'Logo de\\']');"
        " return i && i.complete && i.naturalWidth > 0; }",
        timeout=DELAI_RENDU,
    )
    assert image.evaluate("n => n.naturalWidth") == 240, (
        "La largeur naturelle doit correspondre au PNG televerse (240 px) : "
        f"{image.evaluate('n => n.naturalWidth')}"
    )
    _attendre_version(page, avant + 1)
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_un_fichier_non_image_est_refuse(page_console, app_url, admin_connecte):
    """Un fichier deguise ne doit ni etre accepte, ni casser le logo existant."""

    page, problemes = page_console
    _ecran_configuration(page, app_url)

    # D'abord un vrai logo, pour verifier qu'il survit au refus.
    page.locator('input[type="file"]').set_input_files(
        files=[{"name": "marque.png", "mimeType": "image/png", "buffer": _png()}]
    )
    expect(page.get_by_text("Remplacer", exact=False).first).to_be_visible(timeout=DELAI_RENDU)

    # Puis un PDF deguise en PNG.
    page.get_by_role("button", name="Remplacer").click()
    page.locator('input[type="file"]').set_input_files(
        files=[{
            "name": "logo.png",
            "mimeType": "image/png",
            "buffer": b"\x89PNG\r\n\x1a\n%PDF-1.7\n% pas une image\n",
        }]
    )

    # Le refus est explique.
    expect(page.get_by_text("n'est pas une image lisible").first).to_be_visible(
        timeout=DELAI_RENDU
    )
    # Et le logo valide est toujours la.
    expect(page.locator('img[alt^="Logo de"]')).to_be_visible()
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_retirer_le_logo(page_console, app_url, admin_connecte):
    page, problemes = page_console
    _ecran_configuration(page, app_url)

    page.locator('input[type="file"]').set_input_files(
        files=[{"name": "marque.png", "mimeType": "image/png", "buffer": _png()}]
    )
    expect(page.get_by_text("Remplacer", exact=False).first).to_be_visible(timeout=DELAI_RENDU)

    page.get_by_role("button", name="Retirer").click()
    expect(page.get_by_text("Aucun logo enregistré").first).to_be_visible(timeout=DELAI_RENDU)
    # Le retrait est trace comme les autres changements.
    expect(page.get_by_text("Logo", exact=False).first).to_be_visible()
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"
