"""
Deliberation : proposition du moteur, decision du jury.

Separation des deux roles, et c'est l'essentiel de cet increment :

- le **moteur** calcule une proposition a partir des notes reellement
  enregistrees. Il ne decide de rien, et sa proposition n'est jamais
  presentee comme un verdict ;
- le **jury** tranche. Rien n'est enregistre tant qu'il n'a pas confirme une
  decision, et tout ecart avec la proposition doit porter un motif.

Une deliberation close est **immuable** : c'est ce qui rend l'attestation de
reussite legitimate, puisque l'attestation ne peut plus s'appuyer sur un
verdict que l'on pourrait modifier apres coup.

Les regles appliquees sont celles **figees dans la seance** au moment de sa
creation, pas celles en vigueur a la lecture : changer le reglement plus tard
ne doit pas reecrire l'historique d'un jury deja tenu.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.academic import Classe, Inscription
from app.models.deliberation import Deliberation, DeliberationDecision, ReglesDeliberation
from app.models.etudiant import Etudiant
from app.models.pedagogie import Note
from app.models.structure import Matiere, UniteEnseignement

#: Statuts possibles d'une decision de jury. Le vocabulaire reprend celui
#: deja employe par le moteur existant : ces libelles sont les **valeurs
#: possibles** d'une decision, pas un reglement.
STATUT_ADMIS = "Admis"
STATUT_RATTRAPAGE = "Rattrapage"
STATUT_AJOURNE = "Ajourné"

STATUTS = (STATUT_ADMIS, STATUT_RATTRAPAGE, STATUT_AJOURNE)

#: Les trois etats d'une unite d'enseignement. Ce ne sont pas troissiecles
#: hiatus : ce sont les trois seules reponses possibles du jury a « que devient
#: cette UE ? », et toute autre valeur signifie que la decision n'a pas ete
#: prise.
#:
#: ``Validée en SR`` se distingue de ``Validée`` parce qu'elle dit *comment* le
#: credit a ete obtenu : apres une session de rattrapage. Sur un bulletin, les
#: deux se lisent pareil pour l'etudiant mais pas pour le dossier — et c'est le
#: dossier qui distingue un diplome sans reserve d'une admission apres
#: epreuve.
VALIDATION_UE_VALIDEE = "Validée"
VALIDATION_UE_RATTRAPAGE = "Validée en SR"
VALIDATION_UE_A_REPRENDRE = "À reprendre"

VALIDATIONS_UE = (
    VALIDATION_UE_VALIDEE,
    VALIDATION_UE_RATTRAPAGE,
    VALIDATION_UE_A_REPRENDRE,
)

#: Bareme de repli, uniquement si la base ne contient aucune ligne de regles.
#: Il reprend les usages de l'institut et reste **non confirme** tant que
#: celui-ci ne l'a pas valide.
#:
#: Il doit etre identique a ``BAREME_CORRECT`` de la migration 0021, qui
#: corrige les lignes deja presentes. Les deux listes sont volontairement
#: dupliquees : une migration ne peut pas importer le service — elle figerait
#: une valeur qui doit rester historique — et le service ne peut pas lire la
#: migration. ``test_semestre_e2e.py`` les compare, et c'est cette comparaison
#: qui empeche les deux de diverger en silence.
BAREME_REPLI: Dict[str, Any] = {
    "seuil_validation_moyenne": 10.0,
    "seuil_eliminatoire": 7.0,
    "seuil_rattrapage_minimale": 8.5,
    "seuil_passage_conditionnel_ects": 18,
    "compensation_autorisee": True,
    "bareme_mentions": [
        {"libelle": "Très Bien", "seuil_min": 16.0},
        {"libelle": "Bien", "seuil_min": 14.0},
        {"libelle": "Assez Bien", "seuil_min": 12.0},
        {"libelle": "Passable", "seuil_min": 10.0},
        {"libelle": "Insuffisant", "seuil_min": 0.0},
    ],
    "confirme_par": None,
    "confirme_le": None,
    "confirmee": False,
}


class DeliberationInvalide(Exception):
    """La demande ne peut pas aboutir : la cause est expliquee."""


# ---------------------------------------------------------------------------
# Regles
# ---------------------------------------------------------------------------
async def charger_regles(db: AsyncSession) -> Dict[str, Any]:
    """Regles en vigueur, et leur etat de confirmation.

    Retourne un dictionnaire serialisable : il est fige dans la deliberation
    et doit donc survivre a une edition ulterieure des regles.
    """

    resultat = await db.execute(select(ReglesDeliberation).limit(1))
    regles = resultat.scalars().first()
    if regles is None:
        return dict(BAREME_REPLI)

    return {
        "seuil_validation_moyenne": float(regles.seuil_validation_moyenne),
        "seuil_eliminatoire": float(regles.seuil_eliminatoire),
        "seuil_rattrapage_minimale": float(regles.seuil_rattrapage_minimale),
        "seuil_passage_conditionnel_ects": int(regles.seuil_passage_conditionnel_ects),
        "compensation_autorisee": bool(regles.compensation_autorisee),
        "bareme_mentions": list(regles.bareme_mentions or []),
        "confirme_par": regles.confirme_par_email,
        "confirme_le": regles.confirme_le.isoformat() if regles.confirme_le else None,
        # Une ligne existe mais n'a jamais ete validee : ce sont des valeurs
        # de depart, pas le reglement de l'institut.
        "confirmee": regles.confirmees,
    }


def mention_pour(moyenne: float, bareme: List[Dict[str, Any]]) -> Optional[str]:
    """Mention correspondant a une moyenne, d'apres le bareme fourni."""

    for entree in sorted(
        bareme or [], key=lambda e: float(e.get("seuil_min", 0)), reverse=True
    ):
        if moyenne >= float(entree.get("seuil_min", 0)):
            libelle = str(entree.get("libelle") or "").strip()
            if libelle:
                return libelle
    return None


def mentions_connues(regles: Dict[str, Any]) -> List[str]:
    """Libelles de mention acceptes par le bareme en vigueur."""

    return sorted(
        {
            str(entree.get("libelle") or "").strip()
            for entree in (regles.get("bareme_mentions") or [])
            if str(entree.get("libelle") or "").strip()
        }
    )


# ---------------------------------------------------------------------------
# Collecte des donnees reelles
# ---------------------------------------------------------------------------
async def etudiants_promotion(
    db: AsyncSession, classe_id: str, session_id: str
) -> List[Inscription]:
    """Inscrits actifs de la promotion : les seuls concernes par le jury.

    Une inscription ajournee ou annulee n'a pas de verdict. Sans ce filtre, le
    PV contiendrait des etudiants que le jury n'a pas examines.
    """

    stmt = (
        select(Inscription)
        .options(
            selectinload(Inscription.etudiant),
            selectinload(Inscription.classe).selectinload(Classe.filiere),
            selectinload(Inscription.classe).selectinload(Classe.niveau),
        )
        .where(
            Inscription.classe_id == classe_id,
            Inscription.session_id == session_id,
            Inscription.statut == "active",
        )
    )
    return list((await db.execute(stmt)).scalars().all())


async def moyennes_par_ue(
    db: AsyncSession, etudiant_id: str, session_id: str
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    """Moyennes par UE et matieres sans UE, pour un etudiant.

    Le regroupement suit les donnees : une matiere est rattachee a son UE,
    l'UE a ses credits. Une matiere **sans UE** — donnee residuelle d'une
    migration — est signalee puis ignoree : on ne peut pas lui attribuer
    d'ECTS, et la compter au hasard fausserait la moyenne generale.

    Une UE sans aucune note n'apparait pas et n'est jamais comptee comme zero :
    la moyenne porte sur ce qui est reellement saisi.
    """

    stmt = (
        select(Note, Matiere, UniteEnseignement)
        .join(Matiere, Note.matiere_id == Matiere.id)
        .outerjoin(UniteEnseignement, Matiere.ue_id == UniteEnseignement.id)
        .where(Note.etudiant_id == etudiant_id, Note.session_id == session_id)
    )

    par_ue: Dict[str, Dict[str, Any]] = {}
    sans_ue: List[Dict[str, Any]] = []
    for note, matiere, ue in (await db.execute(stmt)).all():
        coefficient = float(note.coefficient or 1.0)
        if ue is None:
            sans_ue.append(
                {"matiere": matiere.nom, "code": matiere.code, "note": float(note.valeur)}
            )
            continue
        entree = par_ue.setdefault(
            str(ue.id),
            {
                "ue": ue.nom,
                "code": ue.code,
                "ects": int(ue.credits or 0),
                "somme_ponderee": 0.0,
                "somme_coefficients": 0.0,
                "nb_notes": 0,
            },
        )
        entree["somme_ponderee"] += float(note.valeur) * coefficient
        entree["somme_coefficients"] += coefficient
        entree["nb_notes"] += 1

    moyennes: Dict[str, Dict[str, Any]] = {}
    for identifiant, entree in par_ue.items():
        if entree["somme_coefficients"] <= 0:
            continue
        moyennes[identifiant] = {
            "ue": entree["ue"],
            "code": entree["code"],
            "ects": entree["ects"],
            "nb_notes": entree["nb_notes"],
            "moyenne": round(entree["somme_ponderee"] / entree["somme_coefficients"], 2),
        }
    return moyennes, sans_ue


async def notes_eliminatoires(
    db: AsyncSession, etudiant_id: str, session_id: str, seuil: float
) -> List[Dict[str, Any]]:
    """Notes sous le seuil eliminatoire, avec la matiere concernee."""

    stmt = (
        select(Note, Matiere)
        .join(Matiere, Note.matiere_id == Matiere.id)
        .where(
            Note.etudiant_id == etudiant_id,
            Note.session_id == session_id,
            Note.valeur < seuil,
        )
    )
    return [
        {"matiere": matiere.nom, "code": matiere.code, "note": float(note.valeur)}
        for note, matiere in (await db.execute(stmt)).all()
    ]


# ---------------------------------------------------------------------------
# Proposition du moteur
# ---------------------------------------------------------------------------
async def proposer(
    db: AsyncSession, etudiant: Etudiant, session_id: str, regles: Dict[str, Any]
) -> Dict[str, Any]:
    """Proposition du moteur pour un etudiant. Ce n'est **pas** une decision.

    La compensation est un choix **global** de reglement, applique apres le
    calcul des moyennes, et jamais UE par UE : c'est la moyenne generale qui
    autorise a compenser, pas chaque matiere isolement.

    Regle de decision, explicite et reglee par l'institut :

        moyenne >= seuil_validation  ET  tous les ECTS acquis -> Admis
        note eliminatoire  OU  moyenne >= seuil_rattrapage_minimale
        OU  ECTS valides >= seuil_conditionnel                 -> Rattrapage
        sinon                                                    -> Ajourné
    """

    moyennes, sans_ue = await moyennes_par_ue(db, etudiant.id, session_id)
    eliminatoires = await notes_eliminatoires(
        db, etudiant.id, session_id, float(regles["seuil_eliminatoire"])
    )

    if not moyennes:
        raise DeliberationInvalide(
            f"Aucune note enregistree pour {etudiant.matricule} sur cette session : "
            "il n'y a rien a deliberer. Un etudiant sans note n'est ni admis ni "
            "ajourne, il n'est pas evalue."
        )

    seuil_validation = float(regles["seuil_validation_moyenne"])

    # 1. Moyenne generale, ponderee par les ECTS — independante de la
    #    compensation, qui ne fait qu'acter sur l'acquisition des credits.
    total_ects = sum(int(entree.get("ects") or 0) for entree in moyennes.values())
    somme_ponderee = sum(
        float(entree["moyenne"]) * int(entree.get("ects") or 0)
        for entree in moyennes.values()
    )
    moyenne_generale = round(somme_ponderee / total_ects, 2) if total_ects else 0.0

    # 2. Validation de chaque UE **sur son seul merit**.
    total_ects_valides = 0
    for entree in moyennes.values():
        entree["validee_sur_merite"] = float(entree["moyenne"]) >= seuil_validation
        entree["eliminatoire"] = False
        if entree["validee_sur_merite"]:
            total_ects_valides += int(entree.get("ects") or 0)

    # 3. Compensation : si — et seulement si — le reglement l'autorise, que la
    #    moyenne generale est bonne et qu'aucune note n'est eliminatoire, les
    #    UE non validees sont compensees.
    compensation_possible = (
        bool(regles.get("compensation_autorisee"))
        and moyenne_generale >= seuil_validation
        and not eliminatoires
    )
    for entree in moyennes.values():
        if compensation_possible:
            entree["validee"] = True
            entree["validee_par_compensation"] = not entree["validee_sur_merite"]
        else:
            entree["validee"] = entree["validee_sur_merite"]
            entree["validee_par_compensation"] = False
    if compensation_possible:
        total_ects_valides = total_ects

    # 3 bis. Proposition **par unite d'enseignement**, dans les trois etats que
    # le jury peut confirmer ou corriger.
    #
    # Le systeme ne decide pas : il propose. La proposition est stockee a cote
    # de la decision, jamais a sa place, et le bulletin n'affiche que la
    # decision — la proposition seulement en la marquant comme telle. Sans
    # cela, deux documents se contrediraient : l'un portant une decision
    # inventee, l'autre portant le silence du jury.
    for entree in moyennes.values():
        if entree.get("validee"):
            entree["proposition_validation"] = VALIDATION_UE_VALIDEE
            entree["proposition_credits"] = int(entree.get("ects") or 0)
        else:
            entree["proposition_validation"] = VALIDATION_UE_A_REPRENDRE
            # A reprendre, l'etudiant conserve zero credit de cette UE. C'est
            # ce qui rend le rattrapage possible : une UE a reprendre ne peut
            # pas compter dans le total deja acquis.
            entree["proposition_credits"] = 0
        entree["proposition_mention"] = mention_pour(
            float(entree["moyenne"]), regles.get("bareme_mentions") or []
        )

    # 4. Decision proposee.
    if moyenne_generale >= seuil_validation and total_ects_valides >= total_ects:
        statut = STATUT_ADMIS
    elif (
        eliminatoires
        or moyenne_generale >= float(regles["seuil_rattrapage_minimale"])
        or total_ects_valides >= int(regles["seuil_passage_conditionnel_ects"])
    ):
        statut = STATUT_RATTRAPAGE
    else:
        statut = STATUT_AJOURNE

    mention = (
        mention_pour(moyenne_generale, regles.get("bareme_mentions") or [])
        if statut == STATUT_ADMIS
        else statut
    )

    avertissements: List[str] = []
    if sans_ue:
        avertissements.append(
            f"{len(sans_ue)} matiere(s) sans unite d'enseignement rattachée, "
            "non ponderee(s) en ECTS et exclue(s) du calcul."
        )
    if total_ects == 0:
        avertissements.append(
            "Aucune UE porteuse de credits sur cette session : la moyenne "
            "generale ne peut pas etre ponderee."
        )

    return {
        "moyenne_generale": moyenne_generale,
        "ects_acquis": total_ects_valides,
        "ects_total": total_ects,
        "moyennes_ue": moyennes,
        "notes_eliminatoires": eliminatoires,
        "proposition_statut": statut,
        "proposition_mention": mention,
        "matieres_hors_ue": sans_ue,
        "avertissements": avertissements,
    }


async def proposer_promotion(
    db: AsyncSession, classe_id: str, session_id: str, regles: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Propositions pour toute la promotion, dans l'ordre des matricules.

    Un etudiant sans note est **ignore**, avec un avertissement : le produire
    dans la liste ferait croire qu'il a ete evalue.
    """

    inscriptions = await etudiants_promotion(db, classe_id, session_id)
    resultats: List[Dict[str, Any]] = []
    ignores: List[str] = []
    for inscription in inscriptions:
        etudiant = inscription.etudiant
        try:
            proposition = await proposer(db, etudiant, session_id, regles)
        except DeliberationInvalide:
            ignores.append(str(etudiant.matricule))
            continue
        resultats.append(
            {"etudiant": etudiant, "inscription": inscription, **proposition}
        )
    resultats.sort(key=lambda item: str(item["etudiant"].matricule or ""))
    if ignores:
        resultats.append(
            {
                "etudiant": None,
                "inscription": None,
                "sans_note": sorted(ignores),
                "avertissements": [
                    f"{len(ignores)} inscrit(s) sans aucune note sur cette session, "
                    f"exclu(s) de la deliberation : {', '.join(sorted(ignores))}."
                ],
            }
        )
    return resultats


# ---------------------------------------------------------------------------
# Seance
# ---------------------------------------------------------------------------
async def deliberation_promotion(
    db: AsyncSession, classe_id: str, session_id: str
) -> Optional[Deliberation]:
    resultat = await db.execute(
        select(Deliberation).where(
            Deliberation.classe_id == classe_id,
            Deliberation.session_id == session_id,
        )
    )
    return resultat.scalars().first()


async def deliberation_id(
    db: AsyncSession, identifiant: str
) -> Optional[Deliberation]:
    resultat = await db.execute(
        select(Deliberation)
        .options(
            selectinload(Deliberation.decisions).selectinload(DeliberationDecision.etudiant)
        )
        .where(Deliberation.id == identifiant)
    )
    return resultat.scalars().first()


async def creer_deliberation(
    db: AsyncSession,
    *,
    etablissement_id: str,
    classe_id: str,
    session_id: str,
    date_deliberation: date,
    president: str,
    membres: List[Dict[str, str]],
    lieu: Optional[str] = None,
) -> Deliberation:
    """Ouvre une seance de jury pour une promotion.

    Les regles en vigueur sont figees dans la seance. Une seconde seance pour
    la meme promotion et la meme session est refusee : deux proces-verbaux
    contradictoires ne peuvent pas coexister.
    """

    existante = await deliberation_promotion(db, classe_id, session_id)
    if existante is not None:
        raise DeliberationInvalide(
            "Une seance de jury existe deja pour cette promotion et cette session. "
            "Deux seances produiraient deux proces-verbaux contradictoires."
        )

    if not (president or "").strip():
        raise DeliberationInvalide(
            "Le president de jury est obligatoire : un proces-verbal sans president "
            "n'a aucune valeur."
        )

    roster = [
        {
            "nom": str(membre.get("nom") or "").strip(),
            "qualite": str(membre.get("qualite") or "").strip(),
        }
        for membre in (membres or [])
        if str(membre.get("nom") or "").strip()
    ]
    if not roster:
        raise DeliberationInvalide(
            "Le jury doit comporter au moins un membre nomme : une seance a "
            "seul n'est pas un jury."
        )

    deliberation = Deliberation(
        id=str(uuid.uuid4()),
        etablissement_id=etablissement_id,
        classe_id=classe_id,
        session_id=session_id,
        date_deliberation=date_deliberation,
        lieu=(lieu or "").strip() or None,
        president=president.strip(),
        membres=roster,
        statut="brouillon",
        regles=await charger_regles(db),
    )
    db.add(deliberation)
    await db.flush()
    return deliberation


# ---------------------------------------------------------------------------
# Decision du jury
# ---------------------------------------------------------------------------
def controler_decision(
    statut: str,
    mention: Optional[str],
    proposition: Dict[str, Any],
    regles: Dict[str, Any],
) -> Optional[str]:
    """Verifie une decision. Retourne la raison du refus, ou ``None``."""

    if statut not in STATUTS:
        return (
            f"Statut de decision inconnu : « {statut} ». "
            f"Valeurs acceptees : {', '.join(STATUTS)}."
        )

    if mention:
        if statut != STATUT_ADMIS:
            if mention != statut:
                return (
                    f"La mention « {mention} » ne correspond pas au statut "
                    f"« {statut} » : un etudiant {statut.lower()} porte la "
                    f"mention « {statut} »."
                )
        else:
            acceptees = mentions_connues(regles)
            if mention not in acceptees:
                return (
                    f"La mention « {mention} » ne figure pas au bareme de "
                    f"l'etablissement. Mentions admises : {', '.join(acceptees)}."
                )

    return None


def decalage(
    statut: str, mention: Optional[str], proposition: Dict[str, Any]
) -> bool:
    """La decision s'ecarte-t-elle de la proposition du moteur ?"""

    return statut != proposition["proposition_statut"] or (mention or "") != (
        proposition.get("proposition_mention") or ""
    )


def decrire_decalage(
    statut: str, mention: Optional[str], proposition: Dict[str, Any]
) -> str:
    """Description lisible de l'ecart, pour le message d'erreur."""

    proposition_mention = proposition.get("proposition_mention")
    depart = proposition["proposition_statut"] + (
        f" / {proposition_mention}" if proposition_mention else ""
    )
    arrivee = statut + (f" / {mention}" if mention else "")
    return f"{depart} -> {arrivee}"


async def enregistrer_decision(
    db: AsyncSession,
    deliberation: Deliberation,
    *,
    etudiant_id: str,
    statut: str,
    mention: Optional[str],
    proposition: Dict[str, Any],
    motif_ecart: Optional[str],
    auteur_id: Optional[int],
) -> DeliberationDecision:
    """Enregistre la decision du jury, avec la proposition et l'ecart motive."""

    if deliberation.close:
        raise DeliberationInvalide(
            "Cette seance de jury est close : son verdict est arrete et ne peut "
            "plus etre modifie."
        )

    regles = deliberation.regles or {}
    raison = controler_decision(statut, mention, proposition, regles)
    if raison is None and decalage(statut, mention, proposition) and not (
        motif_ecart or ""
    ).strip():
        raison = (
            "La decision s'ecarte de la proposition du moteur ("
            f"{decrire_decalage(statut, mention, proposition)}) sans etre motivee. "
            "Un ecart non explique laisserait le verdict inexplicable : "
            "indiquez pourquoi le jury a decide autrement."
        )
    if raison:
        raise DeliberationInvalide(raison)

    resultat = await db.execute(
        select(DeliberationDecision).where(
            DeliberationDecision.deliberation_id == deliberation.id,
            DeliberationDecision.etudiant_id == etudiant_id,
        )
    )
    decision = resultat.scalars().first()
    if decision is None:
        decision = DeliberationDecision(
            id=str(uuid.uuid4()),
            deliberation_id=deliberation.id,
            etudiant_id=etudiant_id,
        )
        db.add(decision)

    decision.proposition_statut = proposition["proposition_statut"]
    decision.proposition_mention = proposition.get("proposition_mention")
    decision.statut = statut
    decision.mention = mention
    decision.motif_ecart = (motif_ecart or "").strip() or None
    decision.moyenne_generale = float(proposition["moyenne_generale"])
    decision.ects_acquis = int(proposition["ects_acquis"])
    decision.ects_total = int(proposition["ects_total"])
    decision.moyennes_ue = proposition["moyennes_ue"]
    decision.notes_eliminatoires = proposition["notes_eliminatoires"]
    decision.decide_le = datetime.now(timezone.utc)
    decision.decide_par_id = auteur_id
    await db.flush()
    return decision


async def cloturer(
    db: AsyncSession, deliberation: Deliberation, *, auteur_id: Optional[int]
) -> Deliberation:
    """Arrete le verdict d'une seance.

    Condition : **une decision pour chaque inscrit**. Une seance close sans
    verdict pour un etudiant laisserait celui-ci sans droit, et
    l'attestation de reussite ne pourrait pas dire s'il a ete examine.
    """

    if deliberation.close:
        raise DeliberationInvalide("Cette seance est deja close.")

    inscrits = await etudiants_promotion(db, deliberation.classe_id, deliberation.session_id)
    if not inscrits:
        raise DeliberationInvalide(
            "Aucun inscrit actif dans cette promotion : il n'y a pas de jury a tenir."
        )

    tranchees = {
        str(identifiant)
        for identifiant in (
            await db.execute(
                select(DeliberationDecision.etudiant_id).where(
                    DeliberationDecision.deliberation_id == deliberation.id
                )
            )
        ).scalars()
        .all()
    }

    manquants = sorted(
        str(inscription.etudiant.matricule)
        for inscription in inscrits
        if str(inscription.etudiant_id) not in tranchees
    )
    if manquants:
        raise DeliberationInvalide(
            f"{len(manquants)} etudiant(s) n'ont pas de decision enregistree "
            f"({', '.join(manquants[:10])}"
            + ("…" if len(manquants) > 10 else "")
            + "). Une seance ne peut pas etre close tant que le jury n'a pas "
            "statue sur chacun."
        )

    deliberation.statut = "close"
    deliberation.close_le = datetime.now(timezone.utc)
    deliberation.close_par_id = auteur_id
    await db.flush()
    return deliberation


# ---------------------------------------------------------------------------
# Verification pour l'attestation de reussite
# ---------------------------------------------------------------------------
async def decision_admis(
    db: AsyncSession, etudiant_id: str, session_id: str
) -> Optional[DeliberationDecision]:
    """Decision ``Admis`` prononcee par un jury **close**.

    Une seance en brouillon ne suffit pas : tant que le verdict n'est pas
    arrete, il n'existe aucun droit acquis.
    """

    stmt = (
        select(DeliberationDecision)
        .join(Deliberation, DeliberationDecision.deliberation_id == Deliberation.id)
        .where(
            DeliberationDecision.etudiant_id == etudiant_id,
            Deliberation.session_id == session_id,
            DeliberationDecision.statut == STATUT_ADMIS,
            Deliberation.statut == "close",
        )
        .order_by(Deliberation.date_deliberation.desc())
    )
    return (await db.execute(stmt)).scalars().first()


__all__ = [
    "BAREME_REPLI",
    "STATUTS",
    "STATUT_ADMIS",
    "STATUT_AJOURNE",
    "STATUT_RATTRAPAGE",
    "DeliberationInvalide",
    "charger_regles",
    "cloturer",
    "controler_decision",
    "creer_deliberation",
    "decalage",
    "decision_admis",
    "deliberation_id",
    "deliberation_promotion",
    "enregistrer_decision",
    "etudiants_promotion",
    "mention_pour",
    "mentions_connues",
    "moyennes_par_ue",
    "notes_eliminatoires",
    "proposer",
    "proposer_promotion",
]


async def derniere_decision(
    db, *, etudiant_id: str, session_id: Optional[str]
):
    """La derniere decision **arretee** du jury sur cette session.

    Elle vit dans le service et pas dans l'endpoint : l'endpoint en a besoin
    pour le bulletin, la liste de rattrapage en a besoin aussi, et un service
    qui importerait un endpoint ne ferait plus un cycle — il formerait une
    boucle d'import impossible a resoudre.

    La session est **joined**, pas devinee. Une decision d'une autre session ne
    doit pas finir sur ce bulletin : l'imprimer reviendrait a dire que le jury
    s'est prononce sur ce semestre alors qu'il s'est prononce ailleurs.

    ``decide_le`` est null tant que la decision n'est pas arretee, d'ou
    ``nullslast`` : une decision en cours de saisie ne cohabite pas avec une
    decision arretee sur le meme etudiant, et c'est l'arretee qui fait foi.
    """

    if session_id is None:
        return None

    return (
        await db.execute(
            select(DeliberationDecision)
            .join(Deliberation, DeliberationDecision.deliberation_id == Deliberation.id)
            .where(
                DeliberationDecision.etudiant_id == etudiant_id,
                Deliberation.session_id == session_id,
            )
            .order_by(
                DeliberationDecision.decide_le.desc().nullslast(),
                DeliberationDecision.created_at.desc(),
            )
            .limit(1)
        )
    ).scalars().first()


async def matieres_a_reprendre(
    db, *, etudiant_id: str, session_id: str
) -> List[Dict[str, Any]]:
    """Les matieres que le jury a decidees « a reprendre », par UE.

    C'est la liste de travail du rattrapage : une UE a reprendre donne droit a
    une **seconde epreuve sur ses matieres**, pas sur l'UE entiere. L'institut
    en decide comme il l'entend ; ce module se contente de deduire la liste du
    journal du jury, pour que l'agent n'ait pas a redécouvrir ce que la
    deliberation a deja prononce.

    Elle se lit dans les **decisions enregistrees**, jamais dans la proposition
    du moteur : tant que le jury n'a pas tranche, rien n'est a reprendre. Une
    liste issue des propositions proposerait des rattrapages que personne
    n'a decides.
    """

    decision = await derniere_decision(
        db, etudiant_id=etudiant_id, session_id=session_id
    )
    if decision is None:
        return []

    a_reprendre = [
        identifiant
        for identifiant, entree in (decision.moyennes_ue or {}).items()
        if isinstance(entree, dict) and entree.get("validation") == VALIDATION_UE_A_REPRENDRE
    ]
    if not a_reprendre:
        return []

    lignes = (
        await db.execute(
            select(Matiere, UniteEnseignement)
            .join(UniteEnseignement, Matiere.ue_id == UniteEnseignement.id)
            .where(UniteEnseignement.id.in_(a_reprendre))
            .order_by(UniteEnseignement.code, Matiere.nom)
        )
    ).all()

    return [
        {
            "ue_id": ue.id,
            "ue_code": ue.code,
            "ue_nom": ue.nom,
            "credits_ue": int(ue.credits or 0),
            "matiere_id": matiere.id,
            "matiere_code": matiere.code,
            "matiere_nom": matiere.nom,
            "coefficient": float(matiere.coefficient or 1.0),
        }
        for matiere, ue in lignes
    ]

