"""Export de la liste des etudiants.

Le fichier produit est un **reflet de la base**, jamais une reconstruction
cote client : un export construit dans le navigateur partirait de la liste
affichee, donc de la page courante, et l'institut croirait avoir exporte toute
la promotion alors qu'il n'en aurait sorti que dix lignes.

Deux formats, parce que les usages reels different : le.tableur pour
l'archivage et le traitement, le CSV pour les outils en ligne de commande qui
n'attendent pas un .xlsx.

Le classeur est produit **sans donnee d'etudiant** lorsqu'il n'y en a aucun, et
l'en-tete est toujours present. Un fichier vide sans en-tete n'est pas
devinable, et l'institut ne saurait pas s'il a exporte la mauvaise classe.
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

#: Colonnes du classeur, dans l'ordre. Le nom est celui que l'institut voit
#: dans ses registres, pas celui de la colonne en base : « Prénom » et non
#: « prenom ». C'est ce fichier qui sera relu par un humain.
COLONNES: Sequence[Dict[str, str]] = (
    {"cle": "prenom", "entete": "Prénom", "largeur": 18},
    {"cle": "nom", "entete": "Nom", "largeur": 22},
    {"cle": "matricule", "entete": "Matricule", "largeur": 18},
    {"cle": "sexe", "entete": "Sexe", "largeur": 8},
    {"cle": "date_naissance", "entete": "Date de naissance", "largeur": 18},
    {"cle": "filiere", "entete": "Filière", "largeur": 24},
    {"cle": "niveau", "entete": "Niveau", "largeur": 16},
    {"cle": "classe", "entete": "Classe", "largeur": 22},
    {"cle": "session", "entete": "Session", "largeur": 22},
    {"cle": "statut", "entete": "Statut", "largeur": 14},
    {"cle": "telephone", "entete": "Téléphone", "largeur": 16},
    {"cle": "email", "entete": "Courriel", "largeur": 28},
)

ENTETES = [colonne["entete"] for colonne in COLONNES]


def _valeur(etudiant, cle: str) -> Any:
    """Lecture defensive : une valeur absente ne doit pas faire echouer l'export.

    Un export qui echoue en raison d'un telephone manquant serait pire
    qu'une cellule vide : l'institut n'aurait aucun fichier, et le secretariat
    ne pourrait pas servir la promotion.
    """

    if cle == "classe":
        classe = getattr(etudiant, "classe", None)
        return classe.nom if classe is not None else None
    if cle == "session":
        session = getattr(etudiant, "session", None)
        return session.nom if session is not None else None
    if cle == "niveau":
        # Le niveau est porte par l'etudiant ; la classe ne l'a pas toujours.
        return getattr(etudiant, "niveau", None)
    valeur = getattr(etudiant, cle, None)
    if isinstance(valeur, (date, datetime)):
        return valeur.strftime("%d/%m/%Y")
    if cle == "sexe" and valeur:
        # Le code est stocke en majuscule dans l'import, mais une saisie
        # manuelle peut avoir laisse la minuscule.
        return {
            "M": "Masculin",
            "F": "Féminin",
        }.get(str(valeur).strip().upper(), str(valeur))
    return valeur


def _lignes(etudiants: Iterable[Any]) -> List[List[Any]]:
    return [
        [_valeur(etudiant, colonne["cle"]) for colonne in COLONNES]
        for etudiant in etudiants
    ]


def vers_csv(etudiants: Iterable[Any]) -> bytes:
    """CSV avec BOM UTF-8 et point-virgule.

    Le BOM n'est pas decoratif : sans lui, Excel en francais lit un CSV UTF-8 en
    page de codes locale et affiche « Ma��le Dupont ». Le point-virgule est le
    separateur attendu par Excel **francais** ; la virgule casse des lignes
    des que le nom contient « Nkrumah, Michael ».
    """

    tampon = io.StringIO()
    graveur = csv.writer(tampon, delimiter=";", lineterminator="\r\n")
    graveur.writerow(ENTETES)
    for ligne in _lignes(etudiants):
        graveur.writerow(["" if valeur is None else valeur for valeur in ligne])
    return tampon.getvalue().encode("utf-8-sig")


def vers_xlsx(etudiants: Iterable[Any], *, titre: str = "Liste des étudiants") -> bytes:
    """Classeur formate, lisible sans manipulation prealable."""

    lignes = _lignes(etudiants)
    classeur = Workbook()
    feuille = classeur.active
    feuille.title = "Étudiants"

    remplissage = PatternFill("solid", fgColor="1F3A5F")
    police = Font(color="FFFFFF", bold=True)

    feuille.append(ENTETES)
    for cellule in feuille[1]:
        cellule.fill = remplissage
        cellule.font = police
        cellule.alignment = Alignment(vertical="center")

    for ligne in lignes:
        feuille.append(["" if valeur is None else valeur for valeur in ligne])

    for index, colonne in enumerate(COLONNES, start=1):
        feuille.column_dimensions[get_column_letter(index)].width = colonne["largeur"]

    # Une cellule vide en tete de colonne se lit « non renseigne » dans un
    # tableur ; sans froze, la premiere ligne disparait a defilement.
    feuille.freeze_panes = "A2"
    if lignes:
        feuille.auto_filter.ref = (
            f"A1:{get_column_letter(len(COLONNES))}{len(lignes) + 1}"
        )

    tampon = io.BytesIO()
    classeur.save(tampon)
    return tampon.getvalue()


def nom_fichier(*, classe: Optional[str], format_: str) -> str:
    """Nom de fichier explicite et sans caractere problematic.

    Un nom generique (« export.xlsx ») ne dit pas quelle promotion a ete
    exportee ; et un accent non normalise cree des fichiers illisibles sur
    certains postes.
    """

    def _assainir(valeur: str) -> str:
        garder = [
            caractere
            for caractere in (valeur or "")
            if caractere.isalnum() or caractere in " -_"
        ]
        return "".join(garder).strip().replace(" ", "-") or "sans-nom"

    suffixe = "xlsx" if format_ == "xlsx" else "csv"
    return f"etudiants_{_assainir(classe or 'toutes')}.{suffixe}"


__all__ = [
    "COLONNES",
    "ENTETES",
    "nom_fichier",
    "vers_csv",
    "vers_xlsx",
]
