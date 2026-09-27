"""Setup Wizard : le pays part dans sa colonne, et l'adresse n'a plus de trou.

Le wizard n'est atteignable que sur une instance vierge. On le rend donc
atteignable en interceptant `GET /setup/status` : le composant exerce est le
vrai, seule la porte d'entree est simulee.

Ce qui est verrouille, et qui etait faux :

1. le champ **Pays** existe et se saisit ;
2. `pays` est envoye comme champ, et non concatene dans l'adresse ;
3. l'adresse ne se termine plus par `", , "`. Le payload assemblait
   `` `${adresse}, ${ville}, ${pays}` `` alors que `ville` et `pays` n'avaient
   **aucun champ de formulaire** : tout le monde obtenait une adresse
   malformee, imprimee sur chaque document officiel ;
4. le pays est annonce dans le recapitulatif avant validation.

Le pays manquant est le point le plus serieux : une installation neuve
demarrait sans pays, et les attestations sortaient incompletes.
"""

import json

from playwright.sync_api import expect

from conftest import DELAI_RENDU, journal_erreurs

#: Ce que le wizard enverrait pour une adresse, une ville et un pays saisis.
#: Les trois se distinguent dans l'adresse finale : c'est ce qui permet de
#: verifier qu'aucune partie ne disparait et qu'aucune partie vide ne s'y glisse.
ADRESSE = "Rue des Jardins"
VILLE = "Cocody"
PAYS = "Sénégal"
DEVISE = "XOF"


def _statut_vierge(route):
    route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({
            "is_configured": False,
            "etablissement_nom": None,
            "etablissement_code": None,
            "devise": None,
            "version": "1.0.0",
            "tenant_mode": "standalone",
            "database_connected": True,
            "details": None,
        }),
    )


def test_le_wizard_exige_et_transmet_le_pays(page_console, app_url):
    page, problemes = page_console
    envoye: dict = {}

    page.route("**/api/v1/setup/status", _statut_vierge)

    def _capture_init(route):
        envoye.update(route.request.post_data_json or {})
        route.fulfill(
            status=201,
            content_type="application/json",
            body=json.dumps({
                "success": True,
                "message": "Configuration terminee.",
                "access_token": "jeton-de-test",
                "token_type": "bearer",
                "user": {
                    "id": 1, "email": "admin@wizard-e2e.org", "nom": "Admin",
                    "prenom": "Wizard", "role": "ADMIN", "is_active": True,
                },
            }),
        )

    page.route("**/api/v1/setup/initialize", _capture_init)

    page.goto(f"{app_url}/setup")
    # L'etape 1 ne propose de continuer que si la base est joignable.
    expect(page.get_by_role("button", name="Continuer")).to_be_visible(timeout=DELAI_RENDU)
    page.get_by_role("button", name="Continuer").click()

    # --- Etape 2 : l'etablissement -------------------------------------
    champs = page.locator("input:visible")
    # nom, code, email, telephone, adresse, devise, pays
    champs.nth(0).fill("Institut Wizard E2E")
    champs.nth(1).fill("WIZ")
    champs.nth(2).fill("contact@wizard-e2e.org")
    champs.nth(3).fill("+22500000000")
    champs.nth(4).fill(ADRESSE)
    champs.nth(5).fill(DEVISE)

    # Ville et pays composent l'adresse postale. Le pays est aussi une colonne
    # de l'identite, exploitable separement.
    page.locator("#setup-ville").fill(VILLE)
    pays = page.locator("#setup-pays")
    expect(pays).to_be_visible()
    pays.fill(PAYS)

    # Le recapitulatif annonce le pays **avant** validation : l'agent doit
    # voir ce qu'il valide. Il se trouve a l'etape 4.
    page.get_by_role("button", name="Continuer").click()

    # --- Etape 3 : le compte Super-Administrateur -----------------------
    admin = page.locator("input:visible")
    admin.nth(0).fill("Admin")
    admin.nth(1).fill("Wizard")
    admin.nth(2).fill("admin@wizard-e2e.org")
    admin.nth(3).fill("+22500000001")
    admin.nth(4).fill("Wizard-Admin-2026!")
    admin.nth(5).fill("Wizard-Admin-2026!")
    page.get_by_role("button", name="Continuer").click()

    recap = page.locator("strong", has_text=PAYS)
    expect(recap.first).to_be_visible(timeout=DELAI_RENDU)

    # --- Etape 4 : finalisation ----------------------------------------
    page.get_by_role("button", name="Initialiser EduManagePro").click()

    expect(page.get_by_text("sont prêts", exact=False).first).to_be_visible(
        timeout=DELAI_RENDU
    )

    # --- Ce qui a ete reellement transmis ------------------------------
    etablissement = envoye.get("etablissement", {})

    assert etablissement.get("pays") == PAYS, (
        "Le pays n'a pas ete transmis comme champ : "
        f"{etablissement.get('pays')!r}. Une installation neuve demarrerait "
        "sans pays, et les documents officiels sortiraient incomplets."
    )

    adresse = etablissement.get("adresse", "")
    # L'adresse postale reprend les trois parties, dans l'ordre, sans trou.
    assert adresse == f"{ADRESSE}, {VILLE}, {PAYS}", (
        f"L'adresse transmise est {adresse!r} au lieu de "
        f"{f'{ADRESSE}, {VILLE}, {PAYS}'!r}."
    )
    # Le piege exact du defaut : des morceaux vides concatenes, parce que
    # `ville` et `pays` n'avaient aucun champ de formulaire.
    assert ",," not in adresse.replace(" ", ""), (
        f"L'adresse contient des morceaux vides : {adresse!r}. Elle est "
        "imprimee telle quelle sur les documents officiels."
    )
    assert not adresse.endswith(","), (
        f"L'adresse se termine par une virgule : {adresse!r}."
    )

    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"
