"""Verrouille le fait que le tableau de bord ne decorre plus l'etat.

La carte « Moteur de Deliberation » affichait « Operationnel » en dur, quel
que soit l'etat reel du reglement. Un badge qui ne peut pas avoir tort n'informe
rien : c'est la decoration qui donne l'illusion d'un controle.

Ce test verifie donc deux choses :

1. un reglement **jamais confirme** est annonce comme tel — la donnee manque,
   l'ecran le dit ;
2. la carte **mene** a l'ecran de deliberation, ou le reglement se reglable.
"""

from playwright.sync_api import expect

from conftest import DELAI_RENDU, journal_erreurs


def test_le_tableau_de_bord_signale_un_reglement_non_confirme(
    page_console, app_url, admin_connecte
):
    page, problemes = page_console
    page.goto(app_url)

    # Le reglement de l'instance de test n'est jamais confirme : la carte doit
    # le dire, et non afficher un badge d'operationnel invérifiable.
    expect(page.get_by_text("À confirmer").first).to_be_visible(timeout=DELAI_RENDU)
    expect(
        page.get_by_text("jamais confirmés par l'établissement").first
    ).to_be_visible()

    # Et l'ancien libelle decoratif a disparu.
    expect(page.get_by_text("Opérationnel")).to_have_count(0)
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_la_carte_mene_a_l_ecran_de_deliberation(page_console, app_url, admin_connecte):
    page, problemes = page_console
    page.goto(app_url)

    lien = page.get_by_role("link", name="Moteur de Délibération LMD/ECTS")
    expect(lien).to_be_visible(timeout=DELAI_RENDU)
    expect(lien).to_have_attribute("href", "/deliberation")

    # Le lien mene bien a un ecran qui fonctionne.
    lien.click()
    expect(
        page.get_by_role("heading", name="Délibération", exact=True)
    ).to_be_visible(timeout=DELAI_RENDU)
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"
