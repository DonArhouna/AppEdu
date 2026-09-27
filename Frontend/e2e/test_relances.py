"""Échéances & relances : qui relancer, et ce qui a déjà été fait.

L'écran repose sur une distinction que le recouvrement impose, et ces tests
la verrouillent :

1. une **créance** est un fait calculé — la ligne porte le montant réellement
   dû et l'ancienneté réelle, jamais un total décoratif ;
2. une **relance** est un **acte constaté** — le dialogue ne promet aucun
   envoi, et le moyen vient du serveur ;
3. le **niveau** progresse depuis l'historique réellement enregistré, et
   l'écran **désactive** la relance quand la précédente date de moins de
   sept jours : relancer deux fois de suite décrédibilise l'établissement ;
4. une recherche sans correspondance **dit pourquoi** l'écran est vide, au
   lieu d'afficher un tableau sans ligne ;
5. un profil sans `finance.read` est refusé, comme la route l'annonce.

Le jeu de données est celui du module lui-même : la pile est partagée entre
modules, donc on **retrouve** ses données au lieu d'en recréer — sans quoi le
deuxième test échouerait sur un doublon.
"""

import re
from datetime import date, timedelta

import pytest
from playwright.sync_api import Locator, Page, expect

from conftest import DELAI_RENDU, journal_erreurs

CODE_FILIERE = "REL"
CODE_NIVEAU = "L1R"
CODE_CLASSE = "REL-L1"
CODE_SESSION = "SES-2627"
MATRICULE = "E2E-REL-0001"
NOM = "Dossier"
PRENOM = "Retard"
MONTANT_DU = 175000.0
RETARD_JOURS = 75
DESCRIPTION_FACTURE = "Echeance E2E relances"

#: Séparateurs que `toLocaleString("fr-FR")` peut employer : espace fine
#: insécable, espace insécable, ou rien selon la version d'ICU du navigateur.
#: On ne les énumère pas : le test lit le nombre affiché et le compare en
#: valeur. Un test qui échoue sur une typographie alors que le montant est juste
#: apprend à tout le monde à ignorer les tests.
ESPACE = re.compile(r"[\s\u00a0\u202f\u2009]")


def montant_affiche(texte: str) -> float:
    """Le montant réellement rendu à l'écran, lu sans se fier au séparateur."""

    return float(ESPACE.sub("", texte).replace("XOF", "").strip())


def _premier(items: list, cle: str, valeur: str) -> dict | None:
    return next((item for item in items if item.get(cle) == valeur), None)


@pytest.fixture
def creance(administration) -> dict:
    """Un étudiant et une facture échue non soldée, propres à ce module."""

    filiere = _premier(
        administration._api_ok("GET", "/structure/filieres").json(), "code", CODE_FILIERE
    )
    if filiere is None:
        filiere = administration._api_ok(
            "POST", "/structure/filieres",
            json={
                "nom": "Genie Logiciel Relances", "code": CODE_FILIERE,
                "duree": 3, "diplome": "Licence", "niveau": "L1",
            },
        ).json()

    cycle = administration._api_ok("GET", "/academic/cycles").json()[0]
    niveau = _premier(
        administration._api_ok("GET", "/academic/niveaux").json(), "code", CODE_NIVEAU
    )
    if niveau is None:
        niveau = administration._api_ok(
            "POST", "/academic/niveaux",
            json={
                "code": CODE_NIVEAU, "nom": "Licence 1 Relances",
                "cycle_id": cycle["id"],
            },
        ).json()

    # L'identite d'une classe est le couple filiere/niveau, et sa reponse ne
    # porte pas de ``code`` : chercher par code ne reverrait jamais rien, et le
    # second appel serait refuse en doublon.
    classes = administration._api_ok("GET", "/academic/classes").json()
    classe = next(
        (
            c
            for c in classes
            if c.get("filiere_id") == filiere["id"] and c.get("niveau_id") == niveau["id"]
        ),
        None,
    )
    if classe is None:
        classe = administration._api_ok(
            "POST", "/academic/classes",
            json={
                "code": CODE_CLASSE, "nom": "Classe relances E2E",
                "filiere_id": filiere["id"], "niveau_id": niveau["id"],
            },
        ).json()

    session = _premier(
        administration._api_ok("GET", "/sessions/").json(), "code", CODE_SESSION
    )
    if session is None:
        pytest.skip(f"Session {CODE_SESSION} absente du jeu de donnees de la suite.")

    # Le backend refuse un melange silencieux entre la classe choisie et le
    # libelle de niveau saisi : il compare au **nom** du niveau de la classe.
    niveau_attendu = niveau.get("nom") or niveau["code"]
    etudiant = _premier(
        administration._api_ok("GET", "/etudiants/").json(), "matricule", MATRICULE
    )
    if etudiant is None:
        etudiant = administration._api_ok(
            "POST", "/etudiants/",
            json={
                "nom": NOM, "prenom": PRENOM, "matricule": MATRICULE, "sexe": "M",
                "date_naissance": "2004-02-08",
                "filiere": filiere["nom"], "niveau": niveau_attendu,
                "classe_id": classe["id"], "session_id": session["id"],
            },
        ).json()

    # Facture echue et non soldee : c'est la creance que l'ecran doit montrer.
    factures = administration._api_ok(
        "GET", "/finances/factures", params={"etudiant_id": etudiant["id"]}
    ).json()
    facture = next(
        (f for f in factures if f.get("description") == DESCRIPTION_FACTURE), None
    )
    if facture is None:
        facture = administration._api_ok(
            "POST", "/finances/factures",
            json={
                "etudiant_id": etudiant["id"], "session_id": session["id"],
                "montant_total": MONTANT_DU,
                "date_emission": (
                    date.today() - timedelta(days=RETARD_JOURS + 30)
                ).isoformat(),
                "date_echeance": (
                    date.today() - timedelta(days=RETARD_JOURS)
                ).isoformat(),
                "description": DESCRIPTION_FACTURE,
            },
        ).json()

    return {"etudiant": etudiant, "facture": facture, "session": session}


def _ecran(page: Page, app_url: str) -> None:
    page.goto(f"{app_url}/relances")
    expect(page.get_by_role("heading", name="Échéances & relances")).to_be_visible(
        timeout=DELAI_RENDU
    )


def _ligne_de(page: Page) -> Locator:
    """La ligne du dossier de ce module, pas la premiere ligne du tableau."""

    return page.locator("tr", has=page.get_by_text(MATRICULE, exact=True)).first


def test_la_creance_echue_apparait_avec_son_montant_et_son_anciennete(
    page_console, app_url, admin_connecte, creance
):
    """La ligne doit porter la dette reelle, pas un total de facade."""

    page, problemes = page_console
    _ecran(page, app_url)

    ligne = _ligne_de(page)
    expect(ligne).to_be_visible(timeout=DELAI_RENDU)

    # Le montant du, dans la devise de l'etablissement.
    affiche = montant_affiche(ligne.get_by_test_id("montant-du").inner_text())
    assert affiche == MONTANT_DU, (
        f"L'ecran annonce {affiche} au lieu de {MONTANT_DU:.0f} : le montant "
        "de la creance n'est pas celui de la dette reelle."
    )

    # L'anciennete reelle : le badge porte le nombre de jours, pas un libelle
    # generique.
    expect(ligne.get_by_text(f"{RETARD_JOURS} j", exact=True)).to_be_visible()

    # Le numero de facture est cite : l'agent sait quelle echeance relancer.
    expect(ligne.get_by_text(creance["facture"]["numero_facture"])).to_be_visible()

    # Aucune relance encore : l'ecran le dit plutot que de laisser croire a un
    # suivi deja fait.
    expect(ligne.get_by_text("Jamais relancé")).to_be_visible()
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_une_recherche_sans_correspondance_dit_pourquoi(
    page_console, app_url, admin_connecte, creance
):
    """Un ecran vide doit s'expliquer, pas laisser un tableau sans ligne."""

    page, problemes = page_console
    _ecran(page, app_url)
    expect(page.get_by_text(MATRICULE, exact=True)).to_be_visible(timeout=DELAI_RENDU)

    page.get_by_label("Rechercher").fill("ZZZ-AUCUN-DOSSIER")
    expect(page.get_by_text("Aucune créance", exact=False).first).to_be_visible()
    # Le message reprend le critere : l'agent sait quoi modifier.
    expect(page.get_by_text("ZZZ-AUCUN-DOSSIER", exact=False).first).to_be_visible()
    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_le_parcours_complet_de_relance_est_tracable(
    page_console, app_url, admin_connecte, creance
):
    """Consigner une relance doit se voir dans l'historique, et bloquer la suivante.

    C'est le cœur du module : sans trace, le secrétariat relance trois fois
    sans le savoir. Sans garde-fou, il relance aussi le lendemain.
    """

    page, problemes = page_console
    _ecran(page, app_url)

    ligne = _ligne_de(page)
    expect(ligne).to_be_visible(timeout=DELAI_RENDU)
    ligne.get_by_role("button", name="Relancer").click()

    # Le dialogue annonce la dette et son anciennete avant toute saisie, et
    # ne promet aucun envoi.
    expect(page.get_by_role("dialog")).to_be_visible()
    expect(page.get_by_text("Constater une relance")).to_be_visible()
    expect(page.get_by_text("elle n'envoie rien", exact=False)).to_be_visible()
    annonce = montant_affiche(
        page.get_by_role("dialog").get_by_test_id("montant-reclame").inner_text()
    )
    assert annonce == MONTANT_DU, (
        f"Le dialogue annonce {annonce} au lieu de {MONTANT_DU:.0f} : "
        "l'agent relancerait sur une base fausse."
    )
    # L'anciennete annoncee. On vise le paragraphe de synthese : le message
    # pre-rempli cite la meme valeur, et matcher les deux echouerait.
    expect(
        page.get_by_role("dialog").locator(
            "p", has_text=f"{RETARD_JOURS} jour(s)"
        )
    ).to_be_visible()

    # Le moyen vient du serveur : la liste n'est pas ecrite en dur dans l'ecran.
    selecteur = page.locator("#moyen-relance")
    expect(selecteur).to_be_visible()
    selecteur.click()
    expect(page.get_by_role("option", name="Courrier")).to_be_visible()
    page.get_by_role("option", name="Courrier").click()

    # Le message pre-rempli est une proposition, pas une decision : il reste
    # editable, et c'est ce qui sera conserve.
    message = page.get_by_label("Message transmis")
    expect(message).to_be_editable()
    expect(message).not_to_have_value("")

    # Le bouton annonce le niveau ; l'ordre d'execution peut deja avoir
    # consigne une relance, donc on ne fige pas l'ordinal.
    page.get_by_role("button", name=re.compile(r"Consigner la \d+")).click()

    # La relance atterrit dans l'historique, avec son montant fige.
    onglet = page.get_by_role("tab", name=re.compile(r"Historique"))
    expect(onglet).to_contain_text("1")
    onglet.click()

    ligne = _ligne_de(page)
    expect(ligne).to_be_visible(timeout=DELAI_RENDU)
    fige = montant_affiche(ligne.get_by_test_id("montant-reclame-historique").inner_text())
    assert fige == MONTANT_DU, (
        f"L'historique annonce {fige} au lieu de {MONTANT_DU:.0f} : "
        "l'instantane de la relance n'est pas ce qui a ete reclame."
    )
    # Le solde n'est pas invente : il n'est constate qu'apres un encaissement.
    expect(ligne.get_by_text("Non constaté")).to_be_visible()

    # La lettre est le document que l'agent remet : il doit pouvoir le
    # telecharger depuis l'historique, sans repasser par l'API.
    with page.expect_download() as telechargement:
        ligne.get_by_role("button", name="Lettre").click()
    fichier = telechargement.value
    assert fichier.suggested_filename.endswith(".pdf"), fichier.suggested_filename
    # Le contenu doit etre un PDF, pas une page d'erreur enregistree sous
    # l'extension du document.
    with open(fichier.path(), "rb") as ouvert:
        entete = ouvert.read(5)
    assert entete.startswith(b"%PDF"), f"Le fichier telecharge n'est pas un PDF : {entete!r}"

    # Retour sur la liste : une relance faite il y a moins de sept jours ne se
    # refait pas, et l'ecran dit pourquoi le bouton est inactif.
    page.get_by_role("tab", name=re.compile(r"À relancer")).click()
    ligne = _ligne_de(page)
    expect(ligne.get_by_text("1e relance")).to_be_visible()

    bouton = ligne.get_by_role("button", name=re.compile(r"Relancer \(2"))
    expect(bouton).to_be_disabled()
    assert "moins de 7 jours" in (bouton.get_attribute("title") or ""), (
        "Le bouton desactive sans dire pourquoi laisse l'agent dans le doute."
    )

    assert not problemes, f"Console :\n{journal_erreurs(problemes)}"


def test_enseignant_refuse_l_ecran_de_recouvrement(
    page_console, app_url, enseignant_connecte
):
    """L'ecran suit la meme permission que la route, et le refus se dit."""

    page, _ = page_console
    page.goto(f"{app_url}/relances")

    expect(page.get_by_text("Accès réservé", exact=False).first).to_be_visible(
        timeout=DELAI_RENDU
    )
    assert (
        page.get_by_role("heading", name="Échéances & relances").count() == 0
    ), (
        "L'enseignant a acces a l'ecran de recouvrement alors que la route "
        "exige finance.read."
    )
