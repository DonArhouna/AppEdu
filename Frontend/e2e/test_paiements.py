"""Paiements : ouverture du modal de guichet et selectabilite des periodes.

Ce test cible le chemin exact qui plantait (``Maximum update depth
exceeded``). Le jeu de donnees de la suite cree une session avec des
periodes de paiement, afin que la tuile de periode soit reellement rendue.
"""

import re

from playwright.sync_api import expect

from conftest import journal_erreurs


def test_le_modal_de_paiement_s_ouvre(page_console, app_url, admin_connecte):
    page, problemes = page_console
    page.goto(f"{app_url}/paiements")

    bouton = page.get_by_role("button", name="Nouveau paiement").first
    expect(bouton).to_be_visible()
    bouton.click()

    # Le dialogue s'ouvre et charge les données de reference.
    expect(page.get_by_text("Nouveau paiement au guichet")).to_be_visible(timeout=20000)
    page.wait_for_timeout(2500)  # laisse le temps aux appels API

    # La liste des etudiants est proposee.
    expect(page.locator("#payment-student")).to_be_visible()

    # Le point cle : aucune boucle de rendu pendant l'ouverture.
    assert not problemes, (
        f"Le modal de paiement a produit des erreurs :\n{journal_erreurs(problemes)}"
    )

    # La tuile de periode existe (session avec periodes) et est cliquable.
    tuiles = page.locator('button[role="checkbox"]')
    nombre = tuiles.count()
    assert nombre > 0, (
        "Aucune periode de paiement n'est proposee alors que la session de "
        "test en contient trois. Verifiez que les periodes sont chargees."
    )
    premiere = tuiles.first
    expect(premiere).to_be_enabled()
    premiere.click()
    page.wait_for_timeout(500)

    # Le total est recalcule et affiche dans la devise de l'etablissement.
    expect(page.get_by_text("Total à encaisser")).to_be_visible()
    # La selection produit un montant : un « 0 XOF » signalerait un calcul
    # qui ne reagit pas.
    zone_total = page.locator(r"text=/\d[\d\u00a0\u202f\s]*\s*XOF/").last
    expect(zone_total).to_be_visible()
    brut = (zone_total.inner_text() or "").replace("\u202f", " ").replace("\u00a0", " ")
    montant = float(re.sub(r"[^0-9,]", "", brut).replace(",", ".") or 0)
    assert montant > 0, f"Le total n'a pas bouge apres selection : {brut!r}"

    assert not problemes, (
        f"Apres selection d'une periode :\n{journal_erreurs(problemes)}"
    )


def test_selection_multiple_de_periodes(page_console, app_url, admin_connecte):
    page, problemes = page_console
    page.goto(f"{app_url}/paiements")
    page.get_by_role("button", name="Nouveau paiement").first.click()
    expect(page.get_by_text("Nouveau paiement au guichet")).to_be_visible(timeout=20000)
    page.wait_for_timeout(2500)

    tout = page.get_by_role("button", name="Tout sélectionner")
    expect(tout).to_be_visible()
    tout.click()
    page.wait_for_timeout(400)

    cochees = page.locator('button[role="checkbox"][aria-checked="true"]')
    assert cochees.count() >= 2, (
        f"« Tout sélectionner » n'a coche que {cochees.count()} periode(s)."
    )
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_fermeture_du_modal(page_console, app_url, admin_connecte):
    page, problemes = page_console
    page.goto(f"{app_url}/paiements")
    page.get_by_role("button", name="Nouveau paiement").first.click()
    expect(page.get_by_text("Nouveau paiement au guichet")).to_be_visible(timeout=20000)

    page.get_by_role("button", name="Annuler").first.click()
    page.wait_for_timeout(600)
    assert page.get_by_text("Nouveau paiement au guichet").count() == 0, (
        "Le modal ne s'est pas fermé."
    )
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"
