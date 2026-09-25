"""Le secretariat voit l'identite qu'il imprime, sans pouvoir la modifier.

C'est le partage voulu cote API : `academic.read` pour lire,
`institution.settings` pour ecrire. L'ecran de parametrage lui est donc
ferme — il ne doit y trouver que ce qu'il peut faire.

Ou alors l'identite doit etre visible **la ou il travaille** : c'est
l'ecran Documents. Un secretariat qui emet un certificat sans voir le nom de
l'etablissement qui y figurera emet a l'aveugle.
"""

from playwright.sync_api import expect

from conftest import DELAI_RENDU, journal_erreurs


def test_le_secretariat_voit_l_identite_sur_l_ecran_documents(
    page_console, app_url, secretariat_connecte
):
    page, problemes = page_console
    page.goto(f"{app_url}/documents")

    # La bande d'identite est presente et nomme l'etablissement.
    expect(page.get_by_text("Institut E2E Frontend").first).to_be_visible(timeout=DELAI_RENDU)

    # Aucun lien d'edition : le secretariat n'a pas la permission, un lien
    # qui mènerait a un ecran refuse serait une promesse rompue.
    expect(page.get_by_role("link", name="Modifier l'identité")).to_have_count(0)

    # Le module Documents reste pleinement fonctionnel pour lui.
    expect(page.get_by_role("heading", name="Documents officiels")).to_be_visible()
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_le_parametrage_reste_ferme_au_secretariat(
    page_console, app_url, secretariat_connecte
):
    """L'ecran de configuration est reserve : il doit le dire clairement.

    Un refus explicite vaut mieux qu'un acces partiellement masque : on sait
    qu'il faut demander la permission, plutôt que de croire que le réglage
    n'existe pas.
    """

    page, problemes = page_console
    page.goto(f"{app_url}/parametrage")

    expect(page.get_by_text("Accès réservé", exact=False).first).to_be_visible(
        timeout=DELAI_RENDU
    )
    expect(page.get_by_text("institution.settings", exact=False).first).to_be_visible()
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_l_administrateur_voit_le_lien_vers_le_parametrage(
    page_console, app_url, admin_connecte
):
    page, problemes = page_console
    page.goto(f"{app_url}/documents")

    lien = page.get_by_role("link", name="Modifier l'identité")
    expect(lien).to_be_visible(timeout=DELAI_RENDU)
    # Et le lien mene bien a l'ecran de configuration, pas a une page morte.
    expect(lien).to_have_attribute("href", "/parametrage")
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"
