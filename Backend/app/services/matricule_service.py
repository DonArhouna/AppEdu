"""Regle de fabrication des matricules.

Le matricule n'est plus produit par une formule ecrite en dur : il vient d'un
**modele** que l'etablissement regle dans Parametre General, avec une largeur
de compteur et un demarrage.

Le modele par defaut reproduit exactement la regle precedente
(``{annee}-{filiere}-{numero}``, quatre chiffres, demarrage a 1) : ajouter une
table de parametres ne doit pas changer les matricules d'une instance deja en
service.

Trois garanties :

1. **Le modele par defaut ne change rien** — les dossiers existants restent
   lisibles, et les familles ont deja recu leurs matricules.
2. **Le compteur ne reutilise jamais un numero.** Un ``count() + 1`` est
   insuffisant : une suppression laisse un trou et un compteur dense
   repartirait de zero. On cherche le premier numero libre.
3. **Un jeton inconnu est refuse.** Un modele contenant ``{foo}`` produirait un
   matricule avec la chaine ``{foo}`` dedans, imprime ensuite sur des
   certificats.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.etudiant import Etudiant
from app.models.parametres_matricule import ParametresMatricule

#: Reproduit la regle codee en dur d'avant ce parametre.
MODELE_DEPART = "{annee}-{filiere}-{numero}"
LARGEUR_DEPART = 4
DEMARRAGE_DEPART = 1

#: Jetons acceptes dans un modele. Liste fermee : un jeton inconnu produirait un
#: matricule contenant litteralement la brace, imprime sur les documents.
JETONS = ("annee", "filiere", "numero")

LARGEUR_MIN, LARGEUR_MAX = 1, 8
DEMARRAGE_MIN, DEMARRAGE_MAX = 1, 99999999


class ParametreMatriculeInvalide(ValueError):
    """La regle demandee ne peut pas produire de matricule."""


@dataclass(frozen=True)
class Nomenclature:
    """Regle de fabrication d'un matricule, suchitee et validee."""

    modele: str = MODELE_DEPART
    largeur_numero: int = LARGEUR_DEPART
    demarrage: int = DEMARRAGE_DEPART

    def rendre(self, *, annee: int, filiere: str, numero: int) -> str:
        return (
            self.modele.replace("{annee}", str(annee))
            .replace("{filiere}", (filiere or "").upper().strip())
            .replace("{numero}", str(numero).zfill(self.largeur_numero))
        )

    def apercu(self, *, filiere: str = "GL", annee: int = 2026) -> str:
        """Exemple lisible, pour que l'etablissement verifie avant d'enregistrer.

        Sans aperçu, un modele mal saisi n'est decouvert qu'a la creation du
        prochain dossier — c'est-a-dire sur un etudiant reel.
        """

        return self.rendre(annee=annee, filiere=filiere, numero=self.demarrage)

    def motif_de_recherche(self, *, annee: int, filiere: str) -> str:
        """La partie fixe, pour ne chercher que les matricules de meme serie."""

        return (
            self.modele.replace("{annee}", str(annee))
            .replace("{filiere}", (filiere or "").upper().strip())
            .replace("{numero}", "")
        )


def valider(modele: str, largeur_numero: int, demarrage: int) -> Nomenclature:
    """Verifie une nomenclature avant de l'enregistrer.

    Le modele est nettoye de ses espaces exterieurs mais conserve sa ponctuation
    : le separateur fait partie de l'identite affichee aux familles.
    """

    nettoye = (modele or "").strip()
    if not nettoye:
        raise ParametreMatriculeInvalide("Le modèle de matricule ne peut pas être vide.")
    if len(nettoye) > 120:
        raise ParametreMatriculeInvalide("Le modèle de matricule dépasse 120 caractères.")

    jetons = set(re.findall(r"\{(\w+)\}", nettoye))
    inconnus = jetons - set(JETONS)
    if inconnus:
        raise ParametreMatriculeInvalide(
            f"Jeton inconnu dans le modèle : {', '.join(sorted(inconnus))}. "
            f"Jetons acceptés : {', '.join('{' + j + '}' for j in JETONS)}."
        )
    if "numero" not in jetons:
        raise ParametreMatriculeInvalide(
            "Le modèle doit contenir {numero}. Sans compteur, deux étudiants "
            "porteraient le même matricule."
        )
    if not isinstance(largeur_numero, int) or not (LARGEUR_MIN <= largeur_numero <= LARGEUR_MAX):
        raise ParametreMatriculeInvalide(
            f"La largeur du compteur doit être un entier compris entre "
            f"{LARGEUR_MIN} et {LARGEUR_MAX}."
        )
    if not isinstance(demarrage, int) or not (DEMARRAGE_MIN <= demarrage <= DEMARRAGE_MAX):
        raise ParametreMatriculeInvalide(
            f"Le premier numéro doit être un entier compris entre "
            f"{DEMARRAGE_MIN} et {DEMARRAGE_MAX}."
        )
    return Nomenclature(
        modele=nettoye, largeur_numero=largeur_numero, demarrage=demarrage
    )


async def charger(db: AsyncSession) -> Nomenclature:
    """La regle en vigueur, ou celle de depart si rien n'est enregistre.

    L'absence de ligne n'est pas une erreur : elle correspond a une instance qui
    n'a jamais enregistre de nomenclature, c'est-a-dire au comportement
    d'avant le parametre.
    """

    resultat = await db.execute(select(ParametresMatricule).limit(1))
    ligne = resultat.scalars().first()
    if ligne is None:
        return Nomenclature()
    try:
        return valider(ligne.modele, ligne.largeur_numero, ligne.demarrage)
    except ParametreMatriculeInvalide:
        # Une regle devenue illisible en base ne doit pas rendre l'application
        # inutilisable : on retombe sur la regle de depart, qui est valide.
        return Nomenclature()


async def enregistrer(
    db: AsyncSession,
    *,
    modele: str,
    largeur_numero: int,
    demarrage: int,
    auteur_id: Optional[int] = None,
) -> Tuple[ParametresMatricule, Dict[str, Any]]:
    """Enregistre la nomenclature et retourne ``(ligne, resume)``."""

    regle = valider(modele, largeur_numero, demarrage)

    resultat = await db.execute(select(ParametresMatricule).limit(1))
    ligne = resultat.scalars().first()
    if ligne is None:
        from app.models.etablissement import Etablissement

        etablissement = (
            await db.execute(select(Etablissement).order_by(Etablissement.created_at.asc()).limit(1))
        ).scalars().first()
        if etablissement is None:
            raise ParametreMatriculeInvalide(
                "Aucun établissement n'est configuré : la nomenclature de "
                "matricule n'a pas d'étudiant à qui s'appliquer."
            )
        import uuid

        ligne = ParametresMatricule(
            id=str(uuid.uuid4()),
            etablissement_id=etablissement.id,
            modele=regle.modele,
            largeur_numero=regle.largeur_numero,
            demarrage=regle.demarrage,
            maj_par_id=auteur_id,
        )
        db.add(ligne)
    else:
        ligne.modele = regle.modele
        ligne.largeur_numero = regle.largeur_numero
        ligne.demarrage = regle.demarrage
        ligne.maj_par_id = auteur_id
    await db.flush()

    return ligne, {
        "modele": regle.modele,
        "largeur_numero": regle.largeur_numero,
        "demarrage": regle.demarrage,
        "exemple": regle.apercu(),
    }


async def generer(db: AsyncSession, filiere_code: str, annee: Optional[int] = None) -> str:
    """Produit le prochain matricule disponible selon la regle en vigueur.

    Premier numero libre, jamais ``count() + 1`` : une suppression laisse un
    trou, et un compteur dense le réaffecterait a un autre etudiant.
    """

    if not filiere_code or not filiere_code.strip():
        raise ValueError("Un code de filière est requis pour générer un matricule.")

    regle = await charger(db)
    if annee is None:
        annee = datetime.now().year

    motif = regle.motif_de_recherche(annee=annee, filiere=filiere_code)
    stmt = select(Etudiant.matricule).where(Etudiant.matricule.like(f"{motif}%"))
    resultat = await db.execute(stmt)
    utilises: Set[str] = {str(valeur) for valeur in resultat.scalars().all()}

    numero = regle.demarrage
    # Garde-fou : au-dela, la recherche du premier libre ne terminerait pas.
    for _ in range(DEMARRAGE_MAX):
        candidat = regle.rendre(annee=annee, filiere=filiere_code, numero=numero)
        if candidat not in utilises:
            return candidat
        numero += 1
    raise ValueError(
        "Aucun numéro de matricule disponible pour cette filière et cette année. "
        "Augmentez la largeur du compteur dans Paramétrage Général."
    )


#: Nom historique conserve : trois appelants l'utilisent.
generate_matricule = generer


__all__ = [
    "DEMARRAGE_DEPART",
    "JETONS",
    "LARGEUR_DEPART",
    "MODELE_DEPART",
    "Nomenclature",
    "ParametreMatriculeInvalide",
    "charger",
    "enregistrer",
    "generer",
    "generate_matricule",
    "valider",
]
