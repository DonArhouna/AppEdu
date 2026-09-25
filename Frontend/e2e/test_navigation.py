"""
Navigation complete : chaque page principale doit s'afficher sans erreur.

Ce test rattrape les defauts de rendu qui avaient ete signales a la main
(login illisible, crash du modal de paiement, cartes divergentes). Il
s'appuie sur deux signaux :

1. le titre attendu est present ;
2. **aucune erreur ni avertissement console** pendant la navigation — c'est
   ce second point qui detecte un ecran blanc ou un HTML invalide, la ou une
   simple verification de presence d'element passerait.

Note sur les attentes : apres un ``goto``, l'application recharge le contexte
React puis retablit la session aupres de l'API avant d'afficher la page.
Interroger immediatement verrait l'etat de chargement — c'est normal, pas un
defaut. On attend donc le titre, avec reprise automatique.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from conftest import DELAI_RENDU, journal_erreurs

#: (chemin, titre attendu ; None = page sans titre interne explicite)
PAGES = [
    ("/", None),
    ("/etudiants", "Étudiants"),
    ("/etudiants/import", "Import d'étudiants"),
    ("/pre-inscription", "Pré-inscriptions"),
    ("/validation", "Validation des dossiers"),
    ("/filieres", "Filières"),
    ("/academic-structure", "Cycles, Niveaux & Classes"),
    ("/promotions", None),
    ("/sessions", "Sessions Académiques"),
    ("/ue", None),
    ("/matieres", None),
    ("/emplois-du-temps", "Emplois du temps"),
    ("/notes", "Carnet de Notes"),
    ("/absences", "Suivi des Absences"),
    ("/enseignants", None),
    ("/personnel", None),
    ("/frais-scolarite", "Frais de Scolarité"),
    ("/factures", "Facturation & Échéanciers"),
    ("/paiements", "Paiements"),
    ("/reporting-financier", "Reporting Financier"),
    ("/analytics", "Analytics & Business Intelligence"),
    ("/documents", "Documents officiels"),
    ("/utilisateurs", "Comptes utilisateurs"),
    ("/roles-permissions", "Rôles & permissions"),
    ("/journal-audit", "Journal d'audit"),
    ("/parametrage", "Paramétrage Général"),
    ("/campus", "Campus"),
    ("/departements", "Départements"),
    ("/parametres-compte", None),
]


def _ouvrir(page: Page, app_url: str, chemin: str) -> None:
    """Navigue vers une page et attend qu'elle soit reellement rendue."""

    page.goto(f"{app_url}{chemin}")
    assert chemin in page.url, f"Redirection inattendue vers {page.url}"
    # Une page chargee expose soit un titre, soit un titre de document.
    expect(
        page.locator("h1, h2[data-slot='card-title'], [role='status']").first
    ).to_be_visible(timeout=DELAI_RENDU)


def _titre_present(page: Page, titre: str) -> bool:
    """Cherche le titre, en tolérant les apostrophes typographiques."""

    variantes = {titre, titre.replace("'", "’")}
    motif = re.compile("|".join(re.escape(v) for v in variantes), re.IGNORECASE)
    return any(motif.search(texte or "") for texte in page.locator("h1").all_inner_texts())


@pytest.mark.parametrize("chemin,titre", PAGES, ids=[c for c, _ in PAGES])
def test_page_se_charge_sans_erreur(page_console, app_url, admin_connecte, chemin, titre):
    page, problemes = page_console
    _ouvrir(page, app_url, chemin)

    if titre:
        assert _titre_present(page, titre), (
            f"Titre « {titre} » absent de {chemin}. "
            f"Titres rendus : {page.locator('h1').all_inner_texts()}"
        )

    assert not problemes, (
        f"{chemin} a produit des messages console :\n{journal_erreurs(problemes)}"
    )


def test_les_pages_rendent_au_moins_un_titre(page_console, app_url, admin_connecte):
    """Filet de securite : aucune page ne doit rester vide."""

    page, problemes = page_console
    sans_titre = []
    for chemin, _ in PAGES:
        page.goto(f"{app_url}{chemin}")
        try:
            expect(page.locator("h1").first).to_be_visible(timeout=DELAI_RENDU)
        except Exception:
            sans_titre.append(chemin)
        assert not problemes, f"{chemin} :\n{journal_erreurs(problemes)}"
    assert not sans_titre, f"Pages sans titre : {sans_titre}"


def test_aucune_entree_de_menu_cassee(page_console, app_url, admin_connecte):
    """Chaque entree de menu doit mener a une page reellement rendue.

    Une entree qui affiche « service non configure » est un defaut
    commercial : elle vend une promesse que le produit ne tient pas.
    """

    page, problemes = page_console
    page.goto(app_url)
    liens = page.locator("aside a[href^='/'], nav a[href^='/']")
    expect(liens.first).to_be_visible(timeout=DELAI_RENDU)
    total = liens.count()
    assert total > 10, f"Navigation suspecte : {total} liens detectes."

    casses = []
    for index in range(total):
        lien = liens.nth(index)
        href = lien.get_attribute("href") or ""
        if href in ("/deconnexion", "/profil"):
            continue
        texte = (lien.inner_text() or "").strip().splitlines()
        libelle = texte[0] if texte else href

        page.goto(f"{app_url}{href}")
        try:
            expect(page.locator("h1").first).to_be_visible(timeout=DELAI_RENDU)
        except Exception:
            casses.append(f"{libelle} ({href}) : rien n'est rendu")
            continue
        if "n'a pas pu s'afficher" in page.content():
            casses.append(f"{libelle} ({href}) : module en erreur")

    assert not casses, "Entrees de menu non fonctionnelles :\n  - " + "\n  - ".join(casses)
