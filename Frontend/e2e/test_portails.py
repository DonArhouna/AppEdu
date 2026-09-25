"""Portails personnels : le menu ne doit vendre que ce que la route accorde.

Defaut reel trouve par cette suite : `hasAccess` accorde tout a
l'administrateur, alors que `/portail-enseignant` et `/espace-etudiant` sont
declares `allowSuperuser={false}`. Le menu affichait donc a l'administrateur
deux entrees qui ne menaient qu'a un ecran « Acces reserve ».

Ces tests verrouillent les deux moities du comportement :

1. l'administrateur ne voit pas les portails d'autrui ;
2. chaque profil voit le sien, avec de vraies donnees, et pas celui de l'autre.
"""

from playwright.sync_api import Page, expect

from conftest import DELAI_RENDU, journal_erreurs


def _liens_menu(page: Page) -> list[str]:
    return page.locator("aside a[href^='/'], nav a[href^='/']").evaluate_all(
        "noeuds => noeuds.map(n => n.getAttribute('href'))"
    )


def test_le_menu_admin_ne_propose_pas_les_portails_d_autrui(
    page_console, app_url, admin_connecte
):
    page, problemes = page_console
    page.goto(app_url)
    expect(page.locator("aside a[href^='/'], nav a[href^='/']").first).to_be_visible(
        timeout=DELAI_RENDU
    )

    liens = _liens_menu(page)
    assert "/portail-enseignant" not in liens, (
        "Le menu propose le Portail Enseignant a un administrateur, alors que "
        "la route refuse explicitement ce profil."
    )
    assert "/espace-etudiant" not in liens, (
        "Le menu propose l'Espace Etudiant a un administrateur, alors que "
        "la route refuse explicitement ce profil."
    )
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_acces_direct_refuse_avec_un_message_explicite(
    page_console, app_url, admin_connecte
):
    """Un acces direct doit etre refuse proprement, pas sur un ecran vide."""

    page, problemes = page_console
    page.goto(f"{app_url}/espace-etudiant")

    expect(page.get_by_text("Accès réservé", exact=False).first).to_be_visible(
        timeout=DELAI_RENDU
    )
    # Le message doit nommer le profil autorise : un refus opaque sert a rien.
    expect(page.get_by_text("Étudiant", exact=False).first).to_be_visible()
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_portail_enseignant_pour_un_enseignant(
    page_console, app_url, enseignant_connecte
):
    page, problemes = page_console
    page.goto(f"{app_url}/portail-enseignant")

    expect(page.get_by_role("heading", name="Portail enseignant")).to_be_visible(
        timeout=DELAI_RENDU
    )
    assert page.get_by_text("Accès réservé", exact=False).count() == 0

    page.goto(app_url)
    expect(page.locator("aside a[href='/portail-enseignant']").first).to_be_visible(
        timeout=DELAI_RENDU
    )
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_portail_etudiant_pour_un_etudiant(page_console, app_url, etudiant_connecte):
    page, problemes = page_console
    page.goto(f"{app_url}/espace-etudiant")

    expect(page.get_by_role("heading", name="Espace étudiant")).to_be_visible(
        timeout=DELAI_RENDU
    )
    assert page.get_by_text("Accès réservé", exact=False).count() == 0

    # Le dossier est resolu et alimente : le matricule du compte est affiche,
    # et la note reellement enregistree apparait dans l'onglet Notes.
    expect(page.get_by_text("E2E-0001", exact=False).first).to_be_visible()
    page.get_by_role("tab", name="Notes").click()
    expect(page.get_by_text("Tri et recurrence").first).to_be_visible()

    page.goto(app_url)
    expect(page.locator("aside a[href='/espace-etudiant']").first).to_be_visible(
        timeout=DELAI_RENDU
    )
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_etudiant_refuse_le_portail_enseignant(page_console, app_url, etudiant_connecte):
    """Le portail de l'autre profil est refuse, et le dit clairement."""

    page, _ = page_console
    page.goto(f"{app_url}/portail-enseignant")

    expect(page.get_by_text("Accès réservé", exact=False).first).to_be_visible(
        timeout=DELAI_RENDU
    )
    # Le message nomme le seul profil autorise.
    expect(page.get_by_text("Enseignant", exact=False).first).to_be_visible()


def test_enseignant_refuse_le_portail_etudiant(page_console, app_url, enseignant_connecte):
    """Cas symetrique du precedent."""

    page, _ = page_console
    page.goto(f"{app_url}/espace-etudiant")

    expect(page.get_by_text("Accès réservé", exact=False).first).to_be_visible(
        timeout=DELAI_RENDU
    )
    expect(page.get_by_text("Étudiant", exact=False).first).to_be_visible()
