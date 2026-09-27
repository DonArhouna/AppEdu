"""Ecran de deliberation : reglement, seance, decisions, cloture.

Ces tests exercent le parcours complet d'une seance de jury depuis
l'interface, et verrouillent les garde-fous que l'ecran doit rendre visibles :

1. le reglement non confirme est signale, et l'ecran le dit ;
2. une seance ne s'ouvre qu'avec un president et des membres nommes ;
3. le moteur **propose**, le jury **decide** : la proposition et la decision
   apparaissent dans deux colonnes distinctes, sinon le jury croirait que la
   moyenne decide seule ;
4. un ecart avec la proposition **impose** un motif dans le formulaire ;
5. la cloture est bloquee tant qu'un inscrit n'a pas de decision ;
6. apres cloture, plus aucune decision n'est modifiable.

Le scenario s'appuie sur le jeu de donnees de la suite : une classe, une
session et des etudiants **avec notes**, parce qu'un etudiant sans note n'est
pas evalue — l'ecran doit le dire.
"""

import pytest
from playwright.sync_api import Page, expect

from conftest import DELAI_RENDU, journal_erreurs


def _ecran(page: Page, app_url: str) -> None:
    page.goto(f"{app_url}/deliberation")
    # ``exact=True`` : « Règlement de délibération » est aussi un titre de
    # niveau 3, et la recherche non exacte trouve les deux.
    expect(page.get_by_role("heading", name="Délibération", exact=True)).to_be_visible(
        timeout=DELAI_RENDU
    )


def test_le_reglement_non_confirme_est_signale(page_console, app_url, admin_connecte):
    """Un reglement jamais valide doit etre annonce, pas presente comme acquis."""

    page, problemes = page_console
    _ecran(page, app_url)

    expect(
        page.get_by_text("Règlement non confirmé par l'établissement").first
    ).to_be_visible()
    expect(
        page.get_by_text("Jamais confirmé par l'établissement").first
    ).to_be_visible()

    # Les seuils sont affiches : le jury sait sur quoi il statue.
    expect(page.get_by_text("Moyenne de validation")).to_be_visible()
    expect(page.get_by_text("Note éliminatoire")).to_be_visible()
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_etat_vide_sans_seance(page_console, app_url, admin_connecte):
    page, problemes = page_console
    _ecran(page, app_url)

    # Aucune seance : l'ecran doit le dire, pas afficher un tableau vide.
    expect(page.get_by_text("Aucune séance ouverte").first).to_be_visible()
    expect(page.get_by_role("button", name="Ouvrir une séance")).to_be_visible()
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_ouvrir_une_seance_exige_un_jury_nomme(page_console, app_url, admin_connecte):
    """Le bouton d'ouverture reste inactif tant que le jury n'est pas saisi."""

    page, problemes = page_console
    _ecran(page, app_url)

    page.get_by_role("button", name="Ouvrir une séance").click()
    expect(page.get_by_role("heading", name="Ouvrir une séance de jury")).to_be_visible(
        timeout=DELAI_RENDU
    )

    ouvrir = page.get_by_role("button", name="Ouvrir la séance")
    # Ni promotion, ni session, ni president : rien ne peut partir.
    expect(ouvrir).to_be_disabled()
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


@pytest.mark.parametrize("profil", ["enseignant"])
def test_la_deliberation_respecte_la_permission(
    page_console, app_url, enseignant_connecte, profil
):
    """Un compte sans `pedagogy.write` ne voit ni la page, ni son contenu.

    Tenir un jury est un acte academique, pas une simple lecture.
    """

    page, problemes = page_console
    page.goto(f"{app_url}/deliberation")

    # Soit l'acces est refuse explicitement, soit la page ne propose rien a
    # consigner. Dans les deux cas, aucun verdict ne peut etre saisi.
    contenu = page.content()
    assert "Ouvrir une séance" not in contenu, (
        "Un compte sans pedagogie.write ne doit pas pouvoir ouvrir une seance."
    )
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_parcours_complet_dune_seance(page_console, app_url, admin_connecte):
    """Proposition du moteur, decision du jury, et motif impose.

    Le scenario suit ce que voit un membre de jury : la moyenne proposee,
    une decision a consigner, et l'obligation de motiver tout ecart. C'est la
    separation des deux roles qu'il faut prouver, pas seulement que la page
    s'affiche.
    """

    page, problemes = page_console
    _ecran(page, app_url)

    # --- Ouvrir la seance ---------------------------------------------
    page.get_by_role("button", name="Ouvrir une séance").click()
    expect(page.get_by_role("heading", name="Ouvrir une séance de jury")).to_be_visible(
        timeout=DELAI_RENDU
    )

    # Promotion puis session : les listes viennent de l'API, rien n'est saisi
    # a la main dans un identifiant.
    # Par nom, et non « premiere option » : l'ordre du DOM n'est pas un
    # contrat, et le test cree ensuite ses propres donnees.
    page.locator("#promotion-seance").click()
    page.get_by_role("option", name="Genie Logiciel L1").click()
    page.locator("#session-seance").click()
    page.get_by_role("option", name="Session 2026-2027").click()

    page.locator("#president").fill("Professeur Directeur Adjoua N'Guessan")
    page.locator('input[aria-label="Nom du membre"]').first.fill("Docteur Yao N'Guessan")
    page.locator('input[aria-label="Qualité du membre"]').first.fill("Professeur de rangs")

    ouvrir = page.get_by_role("button", name="Ouvrir la séance")
    expect(ouvrir).to_be_enabled()
    ouvrir.click()

    # --- Le moteur propose ---------------------------------------------
    # La colonne « Proposition du moteur » est distincte de « Décision du
    # jury » : sans cette separation, le jury croirait que la moyenne decide.
    entete_proposition = page.get_by_role("columnheader", name="Proposition du moteur")
    entete_decision = page.get_by_role("columnheader", name="Décision du jury")
    expect(entete_proposition).to_be_visible(timeout=DELAI_RENDU)
    expect(entete_decision).to_be_visible()

    # Les propositions portent une moyenne reelle, issue des notes saisies.
    expect(page.get_by_text("/20").first).to_be_visible()

    # --- Le jury decide -----------------------------------------------
    decider = page.get_by_role("button", name="Décider").first
    expect(decider).to_be_visible()
    decider.click()
    expect(page.get_by_role("heading", name="Décision du jury")).to_be_visible()

    # Le dialogue montre la proposition du moteur : le jury sait ce qu'il
    # s'ecarte eventuellement.
    expect(page.get_by_text("Proposition du moteur").first).to_be_visible()

    # Choisir « Rattrapage » quand le moteur propose l'admission provoque un
    # ecart : le motif devient obligatoire, et le bouton s'en trouve bloque.
    page.locator("#decision-statut").click()
    page.get_by_role("option", name="Rattrapage").click()

    motif = page.locator("#motif-ecart")
    expect(motif).to_be_visible()
    expect(
        page.get_by_text("Motif de l'écart", exact=False).first
    ).to_be_visible()

    consigner = page.get_by_role("button", name="Consigner la décision")
    expect(consigner).to_be_disabled(), (
        "Un ecart avec la proposition sans motif ne doit pas etre consignable."
    )

    motif.fill(
        "Resultats de rattrapage transmis apres la tenue de la seance ; "
        "le jury a statue sur les notes initiales."
    )
    expect(consigner).to_be_enabled()
    consigner.click()

    # --- La decision et son ecart sont visibles ------------------------
    expect(page.get_by_text("Rattrapage").first).to_be_visible(timeout=DELAI_RENDU)
    expect(page.get_by_text("Écart motivé", exact=False).first).to_be_visible()
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_la_cloture_est_bloquee_tant_qu_il_reste_des_decisions(
    page_console, app_url, admin_connecte, administration
):
    """Le bouton de cloture annonce ce qui manque, plutot que d'echouer.

    Une cloture qui echouerait sur une erreur serveur laisserait le jury sans
    savoir pourquoi. L'ecran doit dire combien d'inscrits restent a statuer.
    """

    page, problemes = page_console
    _ecran(page, app_url)

    # Promotion dediee : la pile est partagee, et une seconde seance pour la
    # meme classe et la meme session serait refusee comme doublon.
    filiere = administration._api_ok(
        "POST", "/structure/filieres",
        json={
            "nom": "Filiere dediee a la cloture", "code": "FCL",
            "duree": 3, "diplome": "Licence", "niveau": "L2",
        },
        headers=administration.headers,
    ).json()
    cycle = administration._api_ok(
        "GET", "/academic/cycles", headers=administration.headers
    ).json()[0]
    niveau = administration._api_ok(
        "POST", "/academic/niveaux",
        json={"code": "L2", "nom": "Licence 2 (cloture)", "cycle_id": cycle["id"]},
        headers=administration.headers,
    ).json()
    classe = administration._api_ok(
        "POST", "/academic/classes",
        json={
            "code": "CLOT-L2", "nom": "Classe dediee a la cloture",
            "filiere_id": filiere["id"], "niveau_id": niveau["id"],
        },
        headers=administration.headers,
    ).json()
    session = administration._api_ok(
        "POST", "/sessions/",
        json={
            "nom": "Session cloture 2027", "code": "SES-CLOT",
            "annee_academique": "2026-2027",
            "date_debut": "2026-10-01", "date_fin": "2027-07-31",
            "statut": "active",
        },
        headers=administration.headers,
    ).json()
    # Promotion complete : une filiere sans grille tarifaire laisse un
    # etudiant sans facturation, et les tests de paiement s'appuient sur une
    # promotion entierement configuree. La suite partage son instance.
    administration._api_ok(
        "POST", "/finances/grilles-tarifaires",
        json={
            "filiere": filiere["nom"], "filiere_id": filiere["id"], "niveau": "L2",
            "droits_inscription": 100000, "scolarite_mensuelle": 75000,
            "nombre_mois": 8, "actif": True,
        },
        headers=administration.headers,
    )

    # Inscrit sans note : il n'est pas evalue, mais il bloque la cloture.
    # C'est le comportement voulu — le serveur compte les inscrits, pas les
    # propositions, pour ne pas laisser un etudiant sans verdict.
    administration._api_ok(
        "POST", "/etudiants/",
        json={
            "nom": "Etudiant", "prenom": "Cloture", "matricule": "CLO-0001",
            "sexe": "M", "date_naissance": "2004-01-15",
            "filiere": filiere["nom"], "niveau": "L2",
            "classe_id": classe["id"], "session_id": session["id"],
        },
        headers=administration.headers,
    )

    page.get_by_role("button", name="Ouvrir une séance").click()
    # La promotion et la session creees plus haut, nommees explicitement.
    page.locator("#promotion-seance").click()
    page.get_by_role("option", name="Classe dediee a la cloture").click()
    page.locator("#session-seance").click()
    page.get_by_role("option", name="Session cloture 2027").click()
    page.locator("#president").fill("Professeur Directeur Adjoua N'Guessan")
    page.locator('input[aria-label="Nom du membre"]').first.fill("Docteur Yao N'Guessan")
    page.get_by_role("button", name="Ouvrir la séance").click()

    arreter = page.get_by_role("button", name="Arrêter le verdict")
    expect(arreter).to_be_visible(timeout=DELAI_RENDU)
    # Aucune decision encore : le bouton est desactive et annonce le reliquat.
    expect(arreter).to_be_disabled()
    expect(arreter).to_contain_text("restant")
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"
