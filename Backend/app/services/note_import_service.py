"""Import de notes depuis un tableur.

Le fichier porte une ligne par etudiant et une colonne par evaluation :

    | Matricule | Nom | Prénom | Devoir 1 | Examen |
    |----------|-----|--------|----------|--------|
    | ISI-0001  | Ba  | Amadou | 14,5     | 12     |

Les colonnes d'identite designent l'etudiant ; **toutes les autres colonnes
sont des evaluations**, nommees par leur en-tete. Une colonne
``Examen:2`` porte son propre coefficient apres deux-points ; a defaut, le
coefficient saisi dans le formulaire s'applique a toutes.

Quatre choix qui meritent d'etre explicites :

1. **Une cellule vide n'est pas un zero.** Elle signifie « non evalue » :
   aucune note n'est creee. Confondre les deux importerait des zeros chez tous
   les absents et fausserait toutes les moyennes. Un zero saisi
   explicitement reste un zero.

2. **Une note hors borne est une erreur de ligne, pas un blocage.** Le rapport
   la signale et le reste du lot est importe : un tableur saisi a la main
   contient presque toujours une cellule parasite.

3. **Le compte rendu est ligne a ligne.** L'import d'etudiants a pose le
   principe : un secretariat doit pouvoir dire « ces 12 lignes ont echoue »
   sans annuler les 300 autres.

4. **L'import est idempotent.** Une note deja enregistree pour le meme
   triplet etudiant / evaluation est **mise a jour**, et le rapport le dit.
   Reimporter le meme fichier ne double pas les notes — ce qui serait le pire
   defaut possible pour une moyenne.

Les evaluations sont enregistrees comme des ``Examen`` : le modele existe,
``Note.examen_id`` le reference, et ``type_examen`` distingue deja le controle
continu d'un examen final. Un devoir est un controle continu. Creer un modele
``Evaluation`` separe aurait touche la moyennes, le carnet de notes et la
deliberation, pour un besoin que le modele courant couvre.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.academic import Classe
from app.models.etudiant import Etudiant
from app.models.pedagogie import Examen, Note
from app.models.session_academique import SessionAcademique
from app.models.structure import Matiere
from app.services.etudiant_import_service import (
    ImportFormatInvalide,
    normalize_cell,
    normalize_header,
    read_table,
)

#: Note maximale. C'est la borne du schema `Note.valeur`, pas une convention de
#: ce module : l'import ne peut pas enregistrer ce que la saisie refuse.
NOTE_MAX = 20.0

#: En-tetes qui identifient l'etudiant. Tout le reste est une evaluation.
COLONNES_IDENTITE = frozenset(
    {"matricule", "code_etudiant", "code", "nom", "nom_de_famille", "prenom", "prenoms"}
)

#: Un en-tete qui parle d'examen est un examen ; tout le reste est du
#: controle continu. Un devoir n'a pas de date d'examen ni de duree : le
#: confondre avec un « Examen Final » fausserait le suivi des sessions.
#:
#: « cc » est **absent** de la liste, volontairement : en abreviation, il
#: designe le controle continu. Le lire comme un examen lui donnerait une
#: duree de 120 minutes et le ferait compter comme epreuve terminale.
MOTS_EXAMEN = ("examen", "exam", "final", "partiel", "rattrapage")

SEPARATEUR_COEFFICIENT = ":"


class ImportNotesInvalide(ValueError):
    """Le fichier ou les parametres ne permettent pas d'importer."""


@dataclass(frozen=True)
class Evaluation:
    """Une colonne du tableur, interpretee comme evaluation."""

    nom: str
    colonne: int
    coefficient: float
    type_examen: str

    def cle(self) -> str:
        """Cle unique d'une evaluation.

        Une **seule** fonction normalise,partout. Coder l'analyse avec
        ``nom.lower()`` et la validation avec ``normalize_header`` faisait
        disparaitre silencieusement toute colonne dont le nom contenait une
        espace : « Devoir 1 » devenait deux cles differentes, et ses notes
        n'etaient jamais ecrites.
        """

        return normalize_header(self.nom)


def _type_pour(nom: str) -> str:
    normalise = normalize_header(nom)
    if any(mot in normalise for mot in MOTS_EXAMEN):
        return "Examen Final"
    return "CC"


def _parse_evaluation(entete: str, colonne: int, coefficient_defaut: float) -> Evaluation:
    """Decoupe ``Examen:2`` en nom et coefficient.

    Le coefficient dans l'en-tete est une **convention de fichier**, pas une
    donnee inventee : sans lui, tous les devoirs vaudraient le meme poids que
    l'examen, et la moyenne ne voudrait rien dire.
    """

    nom = entete.strip()
    coefficient = coefficient_defaut
    if SEPARATEUR_COEFFICIENT in nom:
        nom, _, brut = nom.partition(SEPARATEUR_COEFFICIENT)
        nom = nom.strip()
        try:
            coefficient = float(str(brut).strip().replace(",", "."))
        except ValueError:
            raise ImportNotesInvalide(
                f"Colonne {entete!r} : le coefficient « {brut} » n'est pas un "
                "nombre. Écrivez « Examen:2 », ou retirez les deux-points pour "
                f"utiliser le coefficient du formulaire ({coefficient_defaut:g})."
            ) from None
    if coefficient <= 0:
        raise ImportNotesInvalide(
            f"Colonne {entete!r} : un coefficient de {coefficient:g} ne pèserait "
            "rien dans la moyenne."
        )
    if not nom:
        raise ImportNotesInvalide(
            f"Colonne {entete!r} : il manque le nom de l'évaluation."
        )
    return Evaluation(
        nom=nom,
        colonne=colonne,
        coefficient=coefficient,
        type_examen=_type_pour(nom),
    )


def _parse_note(brut: str, entete: str) -> Tuple[Optional[float], Optional[str]]:
    """Lecture d'une cellule de note. Retourne ``(valeur, erreur)``.

    ``(None, None)`` = non evalue. C'est distinct de ``(0.0, None)`` : zero est
    une note, l'absence n'en est pas une.
    """

    texte = normalize_cell(brut)
    if not texte:
        return None, None
    # Les separateurs de milliers cassent la lecture : « 1 250 » n'est pas une
    # note sur 20, et « 12,5 » doit etre lu comme douze virgule cinq.
    nettoye = texte.replace(" ", "").replace("\u00a0", "").replace("\u202f", "")
    nettoye = nettoye.replace(",", ".")
    try:
        valeur = float(nettoye)
    except ValueError:
        return None, (
            f"Colonne {entete!r} : « {texte} » n'est pas un nombre. Laissez la "
            "cellule vide si l'étudiant n'a pas été évalué."
        )
    if valeur < 0:
        return None, f"Colonne {entete!r} : une note ne peut pas être négative ({texte})."
    if valeur > NOTE_MAX:
        return None, (
            f"Colonne {entete!r} : {texte} dépasse {NOTE_MAX:g}. La note est "
            "sur 20 — sauf si l'échelle de votre institut est differente, auquel "
            "cas la saisie directe reste possible."
        )
    return round(valeur, 2), None


@dataclass
class LigneNote:
    """Ce que dit le fichier d'une ligne, avant toute ecriture."""

    numero: int
    etudiant: Optional[Etudiant] = None
    matricule: str = ""
    nom_complet: str = ""
    notes: Dict[str, Optional[float]] = field(default_factory=dict)
    a_creer: int = 0
    a_modifier: int = 0
    erreurs: List[str] = field(default_factory=list)
    ignoree: bool = False


@dataclass
class RapportImportNotes:
    """Rapport ligne a ligne, comme l'import d'etudiants."""

    evaluations: List[Dict[str, Any]] = field(default_factory=list)
    lignes: List[LigneNote] = field(default_factory=list)
    classe: Optional[Dict[str, Any]] = None
    matiere: Optional[Dict[str, Any]] = None
    session: Optional[Dict[str, Any]] = None

    @property
    def total_notes(self) -> int:
        return sum(ligne.a_creer + ligne.a_modifier for ligne in self.lignes)

    @property
    def total_erreurs(self) -> int:
        return sum(len(ligne.erreurs) for ligne in self.lignes)

    @property
    def lignes_en_erreur(self) -> int:
        return sum(1 for ligne in self.lignes if ligne.erreurs)

    def resume(self) -> Dict[str, Any]:
        return {
            "evaluations": len(self.evaluations),
            "lignes": len(self.lignes),
            # Ce que l'import ecrira, en un coup d'oeil. C'est le chiffre que
            # l'agent cherche avant de valider.
            "total_notes": self.total_notes,
            "notes_creees": sum(ligne.a_creer for ligne in self.lignes),
            "notes_modifiees": sum(ligne.a_modifier for ligne in self.lignes),
            "lignes_en_erreur": self.lignes_en_erreur,
            "total_erreurs": self.total_erreurs,
        }


# ---------------------------------------------------------------------------
# Referentiels
# ---------------------------------------------------------------------------
async def _etudiants_de_la_classe(db: AsyncSession, classe_id: str) -> List[Etudiant]:
    resultat = await db.execute(
        select(Etudiant)
        .options(selectinload(Etudiant.classe))
        .where(Etudiant.classe_id == classe_id)
        .order_by(Etudiant.nom, Etudiant.prenom)
    )
    return list(resultat.scalars().all())


def _indexer(etudiants: Sequence[Etudiant]) -> Tuple[Dict[str, Etudiant], Dict[Tuple[str, str], List[Etudiant]]]:
    """Index de resolution, tolerant aux homonymes.

    « Amadou Ba » n'identifie personne : plusieurs eleves peuvent porter ce
    nom dans une meme promotion. Le rapport dit alors « plusieurs eleves
    portent ce nom » plutot que d'en choisir un.
    """

    par_matricule: Dict[str, Etudiant] = {}
    par_nom: Dict[Tuple[str, str], List[Etudiant]] = {}
    for etudiant in etudiants:
        if etudiant.matricule:
            par_matricule[normalize_cell(etudiant.matricule).lower()] = etudiant
        cle = (
            normalize_cell(etudiant.nom).lower(),
            normalize_cell(etudiant.prenom).lower(),
        )
        par_nom.setdefault(cle, []).append(etudiant)
    return par_matricule, par_nom


async def _evaluations_existantes(
    db: AsyncSession, *, matiere_id: str, session_id: str
) -> Dict[str, Examen]:
    resultat = await db.execute(
        select(Examen).where(
            Examen.matiere_id == matiere_id, Examen.session_id == session_id
        )
    )
    index: Dict[str, Examen] = {}
    for examen in resultat.scalars().all():
        index[normalize_header(examen.nom)] = examen
    return index


async def _notes_existantes(
    db: AsyncSession, *, matiere_id: str, session_id: str
) -> Dict[Tuple[str, str], Note]:
    """Notes deja enregistrees, indexees par ``(etudiant, evaluation)``."""

    resultat = await db.execute(
        select(Note)
        .options(selectinload(Note.etudiant))
        .where(Note.matiere_id == matiere_id, Note.session_id == session_id)
    )
    index: Dict[Tuple[str, str], Note] = {}
    for note in resultat.scalars().all():
        etudiant = note.etudiant
        if etudiant is None or not etudiant.matricule:
            continue
        index[(etudiant.matricule, note.examen_id or "")] = note
    return index


# ---------------------------------------------------------------------------
# Analyse : lecture seule, aucune ecriture
# ---------------------------------------------------------------------------
def _analyser_entetes(
    entetes: Sequence[str], coefficient_defaut: float
) -> Tuple[Dict[str, int], List[Evaluation], List[str]]:
    """Separe les colonnes d'identite des colonnes d'evaluation."""

    if not entetes:
        raise ImportNotesInvalide("Le fichier ne comporte aucune ligne d'en-tête.")

    identite: Dict[str, int] = {}
    evaluations: List[Evaluation] = []
    ignorees: List[str] = []

    for index, brut in enumerate(entetes):
        cle = normalize_header(brut)
        if not cle:
            ignorees.append(f"colonne {index + 1} sans intitulé")
            continue
        if cle in COLONNES_IDENTITE:
            if cle in identite:
                raise ImportNotesInvalide(
                    f"Deux colonnes d'identité portent le nom « {brut} ». "
                    "Gardez-en une seule."
                )
            identite[cle] = index
            continue
        evaluations.append(_parse_evaluation(brut, index, coefficient_defaut))

    if not evaluations:
        raise ImportNotesInvalide(
            "Aucune colonne d'évaluation reconnue. Le fichier doit comporter au "
            "moins une colonne de note, nommée par l'évaluation : « Devoir 1 », "
            "« Examen », « Examen:2 »…"
        )
    if "matricule" not in identite and not {"nom", "prenom"} <= set(identite):
        raise ImportNotesInvalide(
            "Le fichier ne permet pas d'identifier les étudiants. Il faut soit une "
            "colonne « Matricule », soit les colonnes « Nom » et « Prénom »."
        )
    return identite, evaluations, ignorees


async def analyser(
    db: AsyncSession,
    *,
    filename: str,
    raw: bytes,
    classe_id: str,
    matiere_id: str,
    session_id: str,
) -> RapportImportNotes:
    """Analyse le fichier **sans rien ecrire**.

    Le coefficient par defaut n'est pas demande : il vient de la **matiere**.
    Le saisir dans l'ecran ouvrait la voie a deux poids concurrents pour la
    meme matiere — celui de la fiche et celui du fichier — et la moyenne aurait
    obeit au choix de l'agent plutot qu'a la regle de l'institut. Une
    colonne peut toujours porter le sien (``Examen:2``) : c'est une exception
    explicite, pas un defaut.

    Le rapport renvoye est exactement ce que l'ecrangera l'import : l'agent peut
    donc le lire avant de valider, et corriger le tableur s'il le faut.
    """

    classe = await db.get(Classe, classe_id)
    if classe is None:
        raise ImportNotesInvalide("Cette classe n'existe pas.")
    matiere = await db.get(Matiere, matiere_id)
    if matiere is None:
        raise ImportNotesInvalide("Cette matière n'existe pas.")
    if not matiere.coefficient or matiere.coefficient <= 0:
        raise ImportNotesInvalide(
            f"La matière {matiere.nom} n'a pas de coefficient. C'est lui qui "
            "pèse dans la moyenne : il doit être renseigné sur la fiche de la "
            "matière avant d'importer des notes."
        )
    session = await db.get(SessionAcademique, session_id)
    if session is None:
        raise ImportNotesInvalide("Cette session académique n'existe pas.")

    # Le coefficient de la matiere est l'unique source du poids par defaut.
    coefficient_defaut = float(matiere.coefficient)

    entetes, corps, _format, _separateur = read_table(filename, raw)
    identite, evaluations, ignorees = _analyser_entetes(entetes, coefficient_defaut)

    etudiants = await _etudiants_de_la_classe(db, classe_id)
    par_matricule, par_nom = _indexer(etudiants)

    if not etudiants:
        raise ImportNotesInvalide(
            f"La classe {classe.nom} n'a aucun étudiant inscrit. Rien à importer : "
            "les notes se saisissent par dossier, pas par promotions vide."
        )

    existantes = await _evaluations_existantes(
        db, matiere_id=matiere_id, session_id=session_id
    )
    par_cle = {evaluation.cle(): evaluation for evaluation in evaluations}
    deja_creees = {
        cle: examen.id
        for cle, examen in (
            (normalize_header(examen.nom), examen) for examen in existantes.values()
        )
        if cle in par_cle
    }

    # La classe n'a pas de code propre : c'est la filiere qui en porte un. Le
    # rapport l'annonce tel quel plutot que d'inventer un code.
    filiere = getattr(classe, "filiere", None)
    rapport = RapportImportNotes(
        evaluations=[
            {
                "nom": evaluation.nom,
                "colonne": evaluation.colonne + 1,
                "coefficient": evaluation.coefficient,
                "type": evaluation.type_examen,
                "nouvelle": evaluation.cle() not in deja_creees,
            }
            for evaluation in evaluations
        ],
        classe={
            "id": classe.id,
            "nom": classe.nom,
            "code": getattr(filiere, "code", None),
        },
        matiere={"id": matiere.id, "nom": matiere.nom, "code": matiere.code},
        session={"id": session.id, "nom": session.nom},
    )

    for numero, cellules in enumerate(corps, start=2):
        ligne = LigneNote(numero=numero)
        # Les colonnes d'identite sont lues une fois, puis rangees : les
        # landmarks « __matricule__ » ne sont pas des notes et ne doivent
        # jamais survivre au comptage.
        matricule_brut = ""
        nom_brut = ""
        prenom_brut = ""
        for cle, index in identite.items():
            valeur = normalize_cell(cellules[index]) if index < len(cellules) else ""
            if cle in ("nom", "nom_de_famille"):
                nom_brut = valeur.lower()
            elif cle in ("prenom", "prenoms"):
                prenom_brut = valeur.lower()
            else:
                matricule_brut = valeur

        ligne.matricule = matricule_brut
        ligne.nom_complet = " ".join(
            partie.capitalize() for partie in (prenom_brut, nom_brut) if partie
        ) or f"ligne {numero}"

        # --- Resolution de l'etudiant -----------------------------------
        etudiant = None
        if matricule_brut:
            etudiant = par_matricule.get(matricule_brut.lower())
            if etudiant is None:
                ligne.erreurs.append(
                    f"Aucun étudiant de la classe ne porte le matricule "
                    f"« {matricule_brut} »."
                )
        else:
            candidats = par_nom.get((nom_brut, prenom_brut), [])
            if not candidats:
                ligne.erreurs.append(
                    f"Aucun étudiant de la classe ne s'appelle "
                    f"{ligne.nom_complet or '(nom vide)'}."
                )
            elif len(candidats) > 1:
                matricules = ", ".join(
                    str(c.matricule or "?") for c in candidats
                )
                ligne.erreurs.append(
                    f"{len(candidats)} étudiants portent le nom "
                    f"{ligne.nom_complet} ({matricules}). Ajoutez la colonne "
                    "« Matricule » au fichier."
                )
            else:
                etudiant = candidats[0]

        ligne.etudiant = etudiant

        # --- Lecture des notes ------------------------------------------
        for evaluation in evaluations:
            brut = (
                cellules[evaluation.colonne]
                if evaluation.colonne < len(cellules)
                else ""
            )
            valeur, erreur = _parse_note(brut, evaluation.nom)
            if erreur:
                ligne.erreurs.append(erreur)
                continue
            ligne.notes[evaluation.cle()] = valeur

        # Une ligne entierement vide n'est pas une erreur : c'est une ligne
        # laissée en trop dans le tableur, et la sanctionner décourage de
        # nettoyer le fichier.
        if not any(valeur is not None for valeur in ligne.notes.values()):
            ligne.ignoree = True
            ligne.erreurs = []
            rapport.lignes.append(ligne)
            continue

        if etudiant is not None and not ligne.erreurs:
            comptees = 0
            for evaluation in evaluations:
                if ligne.notes.get(evaluation.cle()) is None:
                    continue
                comptees += 1
                if deja_creees.get(evaluation.cle()):
                    ligne.a_modifier += 1
                else:
                    ligne.a_creer += 1
            if comptees == 0:
                ligne.ignoree = True

        rapport.lignes.append(ligne)

    if ignorees:
        rapport.lignes.insert(
            0,
            LigneNote(
                numero=0,
                nom_complet="Colonnes sans intitulé",
                erreurs=ignorees,
            ),
        )
    return rapport


# ---------------------------------------------------------------------------
# Validation : l'ecriture
# ---------------------------------------------------------------------------
async def valider(
    db: AsyncSession,
    *,
    rapport: RapportImportNotes,
    matiere_id: str,
    session_id: str,
    semestre_id: Optional[str] = None,
    rattrapage: bool = False,
) -> Dict[str, Any]:
    """Ecrit les notes annoncees par le rapport, et renvoie le bilan reel.

    Le rapport d'analyse sert de contrat : l'import n'interprete pas le
    fichier une seconde fois. Il ne peut donc pas ecrire autre chose que ce
    qui a ete montre a l'agent juste avant — un ecran qui montre autre chose
    que ce qu'il enregistre est un ecran qui ment.

    Les lignes en erreur sont **sautees, pas bloquees** : 300 notes correctes
    ne doivent pasdependre d'une cellule erronee dans un fichier de 320 lignes.

    ``semestre_id`` et ``rattrapage`` sont deux parametres, et non deux
    options cachees :

    - le semestre **est ecrit sur chaque note**. Sans lui, les notes d'un
      enseignement annuel — evalue sur chaque semestre — seraient
      indiscernables, et le moteur ne pourrait pas les repartir ;
    - ``rattrapage`` marque les notes comme **remplaçant** une premiere
      tentative. Le moteur ecarte alors les notes precedentes de la meme
      matiere sur le meme semestre. C'est ce qui evite d'afficher (12 + 15) / 2
      sur le bulletin, une moyenne que personne n'a notee.
    """

    if not rapport.evaluations:
        raise ImportNotesInvalide(
            "Aucune évaluation à importer : le fichier ne contient aucune "
            "colonne de note."
        )

    evaluations_existantes = await _evaluations_existantes(
        db, matiere_id=matiere_id, session_id=session_id
    )
    session = await db.get(SessionAcademique, session_id)
    if session is None:
        raise ImportNotesInvalide("Cette session académique n'existe plus.")

    par_cle: Dict[str, Examen] = dict(evaluations_existantes)
    for evaluation in rapport.evaluations:
        cle = normalize_header(evaluation["nom"])
        if cle in par_cle:
            continue
        # En rattrapage, l'evaluation porte ce type. Ce n'est pas un
        # detail d'intitule : c'est ce qui distingue l'epreuvre de seconde
        # chance d'une nouvelle epreuve ordinaire, sur le releve comme sur le
        # dossier de l'etudiant.
        type_examen = "Rattrapage" if rattrapage else evaluation["type"]
        db.add(Examen(
            id=str(uuid.uuid4()),
            nom=evaluation["nom"],
            session_id=session_id,
            matiere_id=matiere_id,
            type_examen=type_examen,
            # ``date_examen`` est obligatoire en base. On prend le debut de la
            # session : c'est une **borne reelle** du perimeter, pas une date
            # inventee. Mettre la date du jour ferait dependre la moyenne d'un
            # jour de saisie.
            date_examen=session.date_debut,
            duree_minutes=0 if type_examen == "CC" else 120,
            coefficient=float(evaluation["coefficient"]),
        ))
        par_cle[cle] = None  # type: ignore[assignment]
    await db.flush()

    # Apres flush, les exams creats sont en base : on relit l'index pour
    # disposer de leurs identifiants, que les notes doivent referencer.
    par_cle = {
        normalize_header(examen.nom): examen
        for examen in (
            (await db.execute(
                select(Examen).where(
                    Examen.matiere_id == matiere_id,
                    Examen.session_id == session_id,
                )
            ))
            .scalars()
            .all()
        )
    }

    existantes = await _notes_existantes(
        db, matiere_id=matiere_id, session_id=session_id
    )

    creees = 0
    modifiees = 0
    ignorees = 0
    for ligne in rapport.lignes:
        if ligne.ignoree or ligne.etudiant is None or ligne.erreurs:
            ignorees += 1
            continue
        for evaluation in rapport.evaluations:
            cle = normalize_header(evaluation["nom"])
            # Meme normalisation que l'analyse : la cle du dictionnaire de
            # notes est celle de l'evaluation, pas une autre.
            valeur = ligne.notes.get(cle)
            if valeur is None:
                continue
            examen = par_cle.get(cle)
            if examen is None:
                continue
            existante = existantes.get((ligne.etudiant.matricule, examen.id))
            if existante is not None:
                existante.valeur = valeur
                existante.coefficient = float(evaluation["coefficient"])
                modifiees += 1
            else:
                db.add(Note(
                    id=str(uuid.uuid4()),
                    etudiant_id=ligne.etudiant.id,
                    matiere_id=matiere_id,
                    examen_id=examen.id,
                    session_id=session_id,
                    semestre_id=semestre_id,
                    valeur=valeur,
                    coefficient=float(evaluation["coefficient"]),
                    statut="Rattrapage" if rattrapage else "Validé",
                ))
                creees += 1

    await db.commit()

    bilan = rapport.resume()
    bilan.update({
        "creees": creees,
        "modifiees": modifiees,
        "lignes_ignorees": ignorees,
    })
    return bilan


__all__ = [
    "COLONNES_IDENTITE",
    "Evaluation",
    "ImportNotesInvalide",
    "LigneNote",
    "NOTE_MAX",
    "RapportImportNotes",
    "analyser",
    "normalize_header",
    "read_table",
    "valider",
]
