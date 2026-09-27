"""Instance neuve : ce que l'ecran doit faire quand rien n'est configure encore.

La suite sème toujours une session, des filieres et des classes avant le
premier test. Cette suite-la ne peut donc pas voir l'etat dans lequel un
institut se trouve **juste apres** le Setup Wizard : etablissement cree,
compte cree, et aucune session.

C'est pourtant le premier ecran que voit un administrateur. Deux defauts
reels y separaient :

1. ``GET /sessions/active`` repond 404 faute de session, et le tableau de bord
   traitait cela comme une erreur **fatale** : il affichait « Impossible de
   charger les donnees » alors que les etudiants, filieres et paiements
   etaient charges. Le repli « Non definie » prevu deux lignes plus bas
   etait donc mort — il ne pouvait pas s'executer.

2. ``GET /context/academique`` repondait 409, et l'ecran de Parametrage
   l'avalait : il affichait un etat « non configure » **sans dire que l'API
   n'avait pas repondu**. Les deux se ressemblent a l'ecran et n'ont rien de
   commun.

Ces tests reproduisent l'etat en interceptant les reponses, avec les statuts
et les corps que le backend renvoie reellement — verifies par
``test_institution_e2e.py``.
"""

import json

from playwright.sync_api import expect

from conftest import DELAI_RENDU, journal_erreurs


def _repondre(route, statut: int, corps: dict) -> None:
    route.fulfill(
        status=statut,
        content_type="application/json",
        body=json.dumps(corps),
    )


def test_le_tableau_de_bord_survit_a_l_absence_de_session(
    page_console, app_url, admin_connecte
):
    """Pas de session n'est pas une panne : le tableau de bord doit s'afficher."""

    page, problemes = page_console

    # Le 404 du backend sur une instance sans session active.
    page.route(
        "**/api/v1/sessions/active",
        lambda route: _repondre(
            route,
            404,
            {"detail": "Aucune session académique active n'est définie."},
        ),
    )
    page.goto(f"{app_url}/")

    expect(page.get_by_role("heading", name="Tableau de Bord Global")).to_be_visible(
        timeout=DELAI_RENDU
    )
    # **Garde de fin de chargement.** Les cartes KPI ne sont rendues que si
    # ``setData`` a eu lieu, c'est-a-dire si le chargement a reussi. Sans
    # cette garde, les assertions d'absence portaient sur une page encore en
    # cours de chargement : elles passaient avec le bug.
    #
    # « Non definie » ne convient pas : le badge l'affiche en repli meme quand
    # rien n'a ete charge. C'est ce qui rendait ce test vide.
    expect(page.get_by_text("Total Étudiants", exact=False).first).to_be_visible(
        timeout=DELAI_RENDU
    )

    # L'echec general ne doit pas etre affiche : le reste des donnees est bon.
    #
    # On vise le marqueur de l'encart d'erreur du tableau de bord, et le
    # message du backend. Les deux avaient ete rates : le premier parce que le
    # libelle reel est « Erreur de synchronisation backend », le second parce
    # que le code affichait le message de l'API, pas celui de repli.
    assert page.get_by_text("Erreur de synchronisation backend", exact=False).count() == 0, (
        "Le tableau de bord affiche un encart d'erreur alors que seule la "
        "session active manquait. Tout le reste etait charge."
    )
    assert page.get_by_text("Aucune session", exact=False).count() == 0, (
        "Le message d'erreur du backend fuite a l'ecran : l'administrateur "
        "lit « aucune session » comme une panne, alors que c'est un etat "
        "normal d'une instance neuve."
    )
    # Le repli prevu par le code doit etre visible : c'est lui qui evite
    # d'inventer une session.
    assert page.get_by_text("Non définie", exact=True).count() >= 1, (
        "Le tableau de bord n'affiche aucune valeur de repli pour la session."
    )
    # Et le reste du tableau de bord est bien alimente.
    expect(page.get_by_text("Étudiants", exact=False).first).to_be_visible()
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_le_parametrage_dit_ce_qu_il_faut_creer_en_premier(
    page_console, app_url, admin_connecte
):
    """Sans session, l'ecran doit dire quoi creer — pas laisser un formulaire vide."""

    page, problemes = page_console

    page.route(
        "**/api/v1/sessions/",
        lambda route: _repondre(route, 200, []),
    )
    page.route(
        "**/api/v1/sessions/active",
        lambda route: _repondre(route, 404, {"detail": "Aucune session active."}),
    )
    # Reponse reelle du backend sur une instance neuve : 200 et non configure.
    page.route(
        "**/api/v1/context/academique",
        lambda route: _repondre(
            route,
            200,
            {
                "annee_academique": "",
                "session_id": None,
                "session": None,
                "configuree": False,
                "updated_at": "2026-09-26T00:00:00Z",
            },
        ),
    )

    page.goto(f"{app_url}/parametrage")
    expect(
        page.get_by_role("heading", name="Paramétrage Général")
    ).to_be_visible(timeout=DELAI_RENDU)

    # L'instruction doit etre actionnable : creer une session, pas activer un
    # contexte qui n'a rien a activer.
    expect(page.get_by_text("Créez d'abord une session", exact=False).first).to_be_visible()
    # Aucune erreur de chargement : le contexte a bien repondu « non configure ».
    assert page.get_by_text("Erreur de chargement").count() == 0, (
        "L'ecran signale une erreur alors que l'API a repondu normalement : "
        "un etat « non configure » n'est pas une panne."
    )
    # Le bouton d'activation reste desactive : il n'y a rien a activer.
    expect(page.get_by_role("button", name="Activer ce contexte")).to_be_disabled()
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_une_echec_de_lecture_du_contexte_est_signale(
    page_console, app_url, admin_connecte
):
    """Un echec de l'API ne doit pas se confondre avec « non configure ».

    Les deux affichent le meme ecran. Les confondre revient a dire a
    l'administrateur que tout va bien — ou, pire, que son reglement
    n'existe pas.
    """

    page, _ = page_console

    page.route(
        "**/api/v1/context/academique",
        lambda route: _repondre(
            route, 500, {"detail": "Le contexte académique est momentanément indisponible."}
        ),
    )
    page.goto(f"{app_url}/parametrage")
    expect(
        page.get_by_role("heading", name="Paramétrage Général")
    ).to_be_visible(timeout=DELAI_RENDU)

    expect(page.get_by_text("Erreur de chargement")).to_be_visible()
    expect(
        page.get_by_text("momentanément indisponible", exact=False).first
    ).to_be_visible()
