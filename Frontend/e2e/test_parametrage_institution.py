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


def test_modifier_un_champ_deja_rempli(
    page_console, app_url, admin_connecte, administration
):
    """Corriger un champ qui contient deja une valeur : le cas le plus courant.

    L'etat est prepare par l'API puis l'ecran recharge, comme le ferait un
    etablissement dont le Setup Wizard a deja saisi l'adresse. On ne remplace
    pas le contenu par un appel programmatique : on tape **par-dessus**, a la
    maniere de quelqu'un qui corrige une adresse.
    """

    adresse_initiale = "Cocody Riviera, Boulevard de France, Abidjan"
    administration._api_ok(
        "PUT", "/institution/configuration",
        json={"adresse": adresse_initiale}, headers=administration.headers,
    )

    page, problemes = page_console
    _ecran_configuration(page, app_url)

    champ = page.locator("#champ-Adresse")
    valeur_initiale = champ.input_value()
    assert valeur_initiale == adresse_initiale, (
        f"Le champ affiche {valeur_initiale!r} au lieu de {adresse_initiale!r} : "
        "la valeur enregistree n'est pas relue dans le formulaire."
    )

    avant = _version_affchee(page)
    nouvelle = f"{valeur_initiale} — Marcory"

    # Saisie progressive : on place le curseur en fin de champ et on tape, sans
    # passer par fill() qui remplacerait la valeur d'un seul bloc.
    champ.click()
    champ.press("End")
    champ.type(" — Marcory", delay=25)

    assert champ.input_value() == nouvelle, (
        f"Le champ affiche {champ.input_value()!r} au lieu de {nouvelle!r} : "
        "la saisie est perdue avant l'enregistrement."
    )

    page.get_by_role("button", name="Enregistrer l'identité").click()
    _attendre_version(page, avant + 1)

    # La valeur soumise est bien celle de la base...
    relu = page.locator("#champ-Adresse").input_value()
    assert relu == nouvelle, (
        f"Apres enregistrement, le champ affiche {relu!r} au lieu de {nouvelle!r}. "
        "C'est le symptome que vous avez decrit."
    )
    # ...et l'historique conserve l'ancienne valeur.
    expect(page.get_by_text(valeur_initiale, exact=False).first).to_be_visible()
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def _vider_le_pays(administration) -> None:
    """Ramene le pays a l'etat vide, par l'API.

    Le formulaire renvoie `""` pour un champ vide alors que la colonne vaut
    `NULL` : c'est l'ecart que le test doit exercer. On le provoque donc au
    lieu de dependre du seed.
    """

    reponse = administration._api_ok(
        "PUT", "/institution/configuration", json={"pays": ""}
    )
    assert reponse.json()["configuration"]["pays"] in (None, ""), (
        f"Le pays n'a pas ete vide : {reponse.json()['configuration']['pays']!r}"
    )


def test_un_champ_vide_ne_cree_pas_de_faux_changement(
    page_console, app_url, admin_connecte, administration
):
    """Renseigner un champ deja vide ne doit pas creer de version fantome.

    Le formulaire renvoie `""` pour un champ vide alors que la colonne vaut
    `NULL`. Sans normalisation, chaque enregistrement creeait une version pour
    un faux changement — l'historique devenait illisible.
    """

    page, problemes = page_console
    _ecran_configuration(page, app_url)

    # Le test a besoin d'un champ **vraiment** vide. Il ne doit pas dependre
    # d'un etat fortuit du jeu de donnees : la suite partage son instance, et
    # un seed qui renseignait le pays rendait cette premisse fausse sans que
    # le defaut couvert change. On etablit donc la condition explicitement.
    _vider_le_pays(administration)
    page.reload()
    expect(page.get_by_role("heading", name="Identité de l'établissement")).to_be_visible(
        timeout=DELAI_RENDU
    )
    expect(page.locator("#champ-Pays")).to_have_value("")

    avant = _version_affchee(page)
    page.locator("#champ-Téléphone").fill("+225 05 55 55 55 55")
    page.locator("#champ-Adresse").fill("Rue des Jardins, Cocody")
    page.get_by_role("button", name="Enregistrer l'identité").click()
    _attendre_version(page, avant + 1)

    # L'historique ne mentionne que le telephone modifie, pas le pays.
    #
    # On scope la lecture a la carte d'historique : ``table tbody tr`` a l'ecran
    # entier visait aussi la table des sessions, et le test echouait alors sur
    # une ligne qui n'avait rien a voir — un echec qui ne disait pas la cause.
    historique = page.locator("table").filter(
        has=page.get_by_role("columnheader", name="Modifications")
    )
    lignes = historique.locator("tbody tr").first.inner_text()
    assert "Pays" not in lignes, (
        f"L'historique mentionne un changement de Pays alors qu'il n'a pas "
        f"change : {lignes!r}"
    )
    assert "Téléphone" in lignes, lignes
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_un_historique_qui_echoue_ne_paie_pas_vide(
    page_console, app_url, admin_connecte
):
    """Une panne de l'historique ne doit pas se lire comme  rien n'a change .

    Le cas est réel : la carte traitait un echec de `GET /institution/versions`
    comme une liste vide. L'agent lisait alors  aucune modification
    enregistrée  et concluait que personne n'avait jamais touche a la
    configuration — alors que l'ecran, lui, n'avait rien charge. Un etat vide
    affirme une absence de donnees ; une panne en est une autre, et doit se
    voir.
    """

    page, _ = page_console
    _ecran_configuration(page, app_url)

    # Une seule requete tombe : l'identite reste lisible, l'historique non.
    page.route(
        "**/api/v1/institution/versions",
        lambda route: route.fulfill(
            status=503,
            content_type="application/json",
            body='{"detail":"Service temporairement indisponible."}',
        ),
    )
    page.reload()
    expect(page.get_by_role("heading", name="Identité de l'établissement")).to_be_visible(
        timeout=DELAI_RENDU
    )

    panne = page.get_by_test_id("erreur-historique")
    expect(panne).to_be_visible()
    expect(panne).to_contain_text("Historique indisponible")
    # Le libelle  aucune modification enregistree  ne doit surtout pas
    # apparaitre : c'est l'affirmation fausse qu'on remplace.
    assert page.get_by_text("Aucune modification enregistrée").count() == 0, (
        "L'ecran affiche un etat vide alors que l'historique a echoue au "
        "chargement : l'agent lirait une absence de modifications."
    )


def test_entree_enregistre_autant_que_le_bouton(
    page_console, app_url, admin_connecte
):
    """Entree doit declencher l'enregistrement, comme un clic.

    C'est le geste le plus naturel sur un formulaire. Avant, il ne se passait
    rien : aucune requete, aucun message. Le clic et la touche empruntaient
    deux chemins distincts, dont un muet.
    """

    page, problemes = page_console
    _ecran_configuration(page, app_url)

    avant = _version_affchee(page)
    champ = page.locator("#champ-Adresse")
    champ.fill("Adresse saisie puis validee par Entree")
    champ.press("Enter")

    _attendre_version(page, avant + 1)
    assert champ.input_value() == "Adresse saisie puis validee par Entree"
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_les_modifications_en_attente_sont_annoncees(
    page_console, app_url, admin_connecte
):
    """Taper sans enregistrer doit etre visible.

    Sans cet indicateur, l'utilisateur ne peut pas distinguer une saisie en
    attente d'une valeur enregistree — c'est l'ambiguite qui donne
    l'impression que l'enregistrement a ete ignore.
    """

    page, problemes = page_console
    _ecran_configuration(page, app_url)

    # Rien de saisi : rien a signaler.
    expect(page.get_by_text("Modifications non enregistrées")).to_have_count(0)

    page.locator("#champ-Adresse").fill("Une adresse encore en cours de saisie")
    expect(page.get_by_text("Modifications non enregistrées").first).to_be_visible()

    # Le message nomme le champ, et propose les deux'issue possibles.
    expect(page.get_by_text("Adresse", exact=False).first).to_be_visible()
    expect(page.get_by_text("Appuyez sur").first).to_be_visible()
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_rien_a_change_reste_affiche_dans_le_formulaire(
    page_console, app_url, admin_connecte
):
    """Un enregistrement sans modification doit etre dit, et le rester.

    Le toast disparait en quelques secondes. Rate, il ne restait rien a l'ecran
    et l'utilisateur conclut que le clic a ete perdu.
    """

    page, problemes = page_console
    _ecran_configuration(page, app_url)

    # Une vraie modification d'abord, pour disposer d'une version de depart.
    avant = _version_affchee(page)
    page.locator("#champ-Téléphone").fill("+225 07 11 11 11 11")
    page.get_by_role("button", name="Enregistrer l'identité").click()
    _attendre_version(page, avant + 1)

    # Puis exactement la meme valeur.
    page.get_by_role("button", name="Enregistrer l'identité").click()

    message = page.get_by_text("Aucun changement enregistré", exact=False)
    expect(message).to_be_visible(timeout=DELAI_RENDU)
    # Il est toujours la apres une pause : il ne disparait pas tout seul.
    page.wait_for_timeout(4000)
    expect(message).to_be_visible()
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_le_retour_disparait_des_la_nouvelle_saisie(
    page_console, app_url, admin_connecte
):
    """ Version enregistree  ne doit pas rester affiche apres une retouche.

    Un message de confirmation persistant pendant qu'on edite un champ est
    faux : il pretend que l'etat affiche correspond a l'etat enregistre.
    """

    page, problemes = page_console
    _ecran_configuration(page, app_url)

    avant = _version_affchee(page)
    page.locator("#champ-Adresse").fill("Adresse confirmee")
    page.get_by_role("button", name="Enregistrer l'identité").click()
    _attendre_version(page, avant + 1)
    expect(page.get_by_text("enregistrée", exact=False).first).to_be_visible()

    # Des que l'on retouche un champ, le retour doit s'effacer.
    page.locator("#champ-Adresse").fill("Adresse en cours de retouche")
    expect(page.get_by_text("Modifications non enregistrées").first).to_be_visible()
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"
