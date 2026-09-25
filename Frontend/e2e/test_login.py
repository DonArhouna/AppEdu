"""Page de connexion : lisibilite, mode clair/sombre, et absence de defaut.

Ces verifications correspondent a des retours reels : contenu du bas de page
invisible, et un ecran concu pour le mode sombre uniquement.
"""

from playwright.sync_api import Page, expect

from conftest import ADMIN_EMAIL, ADMIN_PASSWORD, journal_erreurs


def test_tout_le_contenu_est_visible_sans_defilement(page_console, app_url):
    """Le login est concu pour tenir dans la hauteur : rien ne doit deborder."""

    page, problemes = page_console
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(f"{app_url}/login")

    # Les deux cartes du bas doivent etre presentes ET dans le cadre.
    for titre in ("Pilotage pédagogique", "Finances structurées"):
        carte = page.get_by_text(titre, exact=False).first
        expect(carte).to_be_visible()
        boite = carte.bounding_box()
        assert boite is not None, f"{titre} n'est pas rendu"
        assert boite["y"] + boite["height"] <= 900, (
            f"« {titre} » déborde sous la hauteur de 900 px : "
            f"bas = {boite['y'] + boite['height']:.0f}px"
        )

    # La page ne doit pas défiler : pas de scrollbar.
    defilement = page.evaluate(
        "() => document.documentElement.scrollHeight - document.documentElement.clientHeight"
    )
    assert defilement <= 2, f"La page de connexion défile de {defilement}px"

    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_bascule_de_theme(page_console, app_url):
    """Le mode clair doit exister et rester persistant."""

    page, problemes = page_console
    page.goto(f"{app_url}/login")

    def theme() -> str:
        return page.evaluate("() => document.documentElement.classList.contains('dark') ? 'dark' : 'light'")

    theme_initial = theme()
    bouton = page.get_by_role("button", name="Activer le mode").first
    expect(bouton).to_be_visible()
    bouton.click()

    theme_apres = theme()
    assert theme_apres != theme_initial, "La bascule de thème n'a rien changé"

    # Diagnostic : la valeur reellement ecrite dans le navigateur.
    stocke = page.evaluate("() => window.localStorage.getItem('theme')")
    assert stocke == theme_apres, (
        f"Le thème affiché est « {theme_apres} » mais localStorage contient « {stocke} »."
    )

    # Le thème survit a un rechargement. Le classe est applique par un effet
    # React : l'assertion réessaie plutot que d'attendre une durée arbitraire.
    page.reload()
    page.wait_for_function(
        "attendu => document.documentElement.classList.contains('dark') === attendu",
        arg=(theme_apres == "dark"),
        timeout=10000,
    )
    assert theme() == theme_apres, (
        f"Thème non persistant : attendu « {theme_apres} », obtenu « {theme()} »."
    )

    # Le contenu reste lisible : le titre est toujours present.
    expect(page.get_by_text("Le pilotage de votre établissement")).to_be_visible()
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_connexion_et_redirection(page_console, app_url):
    """Une connexion reussie mene a l'accueil et charge le profil RBAC."""

    page, problemes = page_console
    page.goto(f"{app_url}/login")
    page.fill("#email", ADMIN_EMAIL)
    page.fill("#password", ADMIN_PASSWORD)
    page.get_by_role("button", name="Se connecter").click()

    page.wait_for_url(lambda url: "/login" not in url, timeout=25000)
    expect(page.locator("aside, nav").first).to_be_visible()
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_identifiants_refuses(page_console, app_url):
    """Un mauvais mot de passe reste sur la page de connexion."""

    page, _ = page_console
    page.goto(f"{app_url}/login")
    page.fill("#email", "inexistant@ecole-ci.org")
    page.fill("#password", "MauvaisMotDePasse-2026!")
    page.get_by_role("button", name="Se connecter").click()

    page.wait_for_timeout(2500)
    assert "/login" in page.url, "Une connexion invalide a mène hors de la page de connexion"
