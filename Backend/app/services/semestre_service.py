"""Moyennes par semestre, calculees comme sur les releves de l'institut.

Les formules ci-dessous ne sont pas des conventions de ce module : elles sont
**verifiees sur les releves de l'institut**, et le test de bout en bout reprend
leurs chiffres.

    MEC  = somme(note x coefficient) / somme(coefficients)      [par matiere]
    MUE  = somme(MEC x CEC) / somme(CEC)                        [par UE]
    Moyenne du semestre = somme(MUE x CUE) / somme(CUE)
    Moyenne generale   = somme(moyenne_semestre x credits) / somme(credits)

Deux points que les releves tranchent, et qu'il serait facile de se tromper :

1. **CUE n'est pas la somme des CEC.** Sur UE1.2.1, les CEC valent 1 + 2 + 2
   = 5, mais le CUE porte 6. Le CUE est le **credit propre de l'UE** — notre
   ``UniteEnseignement.credits``. La moyenne de semestre se pondere donc par les
   credits d'UE, et non par la somme des coefficients de matiere. Confondre les
   deux decale la moyenne de plusieurs points.

2. **Un semestre sur deux porte un recapitulatif annuel.** Les semesters
   **pairs** (2, 4, 6) le montrent, les impairs (1, 3, 5) non. Une annee de
   diplome vaut deux semestres : c'est la parite du numero, et non une
   option de l'ecran, qui decide.

Ce module **calcule**. Il ne decide pas du sort de l'etudiant : la validation,
elle, appartient au jury et passe par la deliberation, dont ce module lit les
decisions sans jamais les recalculer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import Inscription
from app.models.pedagogie import Examen, Note
from app.models.structure import (
    REGIME_ANNUELLE,
    Matiere,
    Semestre,
    UniteEnseignement,
)

#: Types d'evaluation qui produisent les colonnes de moyenne controlee et de
#: moyenne d'examen. Ce sont les valeurs du modele ``Examen.type_examen``.
TYPE_CONTROLE = "CC"
TYPES_EXAMEN = ("Examen Final", "Partiel", "Rattrapage")


def _moyenne_ponderee(valeurs: Sequence[Tuple[float, float]]) -> Optional[float]:
    """Moyenne ponderee, ou ``None`` s'il n'y a rien a moyenner.

    ``None`` et non 0 : une matiere sans note n'a pas une moyenne de zero, elle
    n'a pas de moyenne. Confondre les deux ferait echouer l'etudiant au lieu
    de signaler que sa saisie est incomplete.
    """

    total = sum(coefficient for _, coefficient in valeurs)
    if not total:
        return None
    return sum(valeur * coefficient for valeur, coefficient in valeurs) / total


def _arrondi(valeur: float) -> float:
    """Deux decimales, comme sur les releves.

    ``round`` de Python applique l'arrondi au plus proche pair : 10,835 donne
    10,83 et 12,9967 donne 13,00 — exactement les valeurs des releves. Un
    arrondi commercial donnerait 10,84, et le bulletin ne concorderait plus
    avec lui-meme d'une annee sur l'autre.
    """

    return round(valeur, 2)


@dataclass
class MoyenneMatiere:
    """Une matiere et ses evaluations."""

    matiere_id: str
    nom: str
    code: str
    #: Coefficient de l'element constitutif dans son UE — la colonne CEC.
    cec: float
    #: Moyenne des notes de la matiere — la colonne MEC, **arrondie** a
    #: l'affichage. Pour la moyenne de l'UE, c'est ``mec_exact`` qui compte.
    mec: Optional[float] = None
    #: MEC sans arrondi. C'est cette valeur que la MUE pondere : moyenne des
    #: valeurs reelles, et non de leurs representations affichees. Sur UE1.2.2
    #: du releve, la moyenne des MEC affiches (12,67 et 9,00) donne 10,84, alors
    #: que le releve imprime 10,83 — parce qu'il a moyenne 12,6667 et 9,00.
    mec_exact: Optional[float] = None
    #: Moyenne controlee : moyenne simple des evaluations de type CC. Deux
    #: devoirs donnent (devoir1 + devoir2) / 2 — regle confirmee par
    #: l'institut, qui ne pondere pas a l'interieur d'un groupe.
    mcc: Optional[float] = None
    #: Moyenne d'examen : moyenne simple des evaluations d'examen.
    exam: Optional[float] = None
    #: Detail des evaluations : sans lui, un MEC de 12,00 est invérifiable.
    evaluations: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def notee(self) -> bool:
        return self.mec is not None


@dataclass
class MoyenneUE:
    """Une unite d'enseignement et son bilan."""

    ue_id: str
    code: str
    nom: str
    #: Credit de l'UE — la colonne CUE. **Pas** la somme des CEC.
    cue: int
    semestre_id: Optional[str] = None
    semestre_libelle: Optional[str] = None
    #: L'enseignement est annuel : il figure sur chaque semestre. Le bulletin
    #: s'en sert pour le signaler, car deux UE identiques sur deux bulletins
    #: meritent une explication.
    annuelle: bool = False
    matieres: List[MoyenneMatiere] = field(default_factory=list)
    #: Moyenne de l'UE — la colonne MUE, **arrondie** a l'affichage. Pour la
    #: moyenne du semestre, c'est ``mue_exact`` qui compte.
    mue: Optional[float] = None
    #: MUE sans arrondi. La moyenne du semestre la pondere, pour la meme
    #: raison que la MUE pondere ``mec_exact``.
    mue_exact: Optional[float] = None
    #: Somme des CEC, pour le controle. Differe volontairement de ``cue``.
    somme_cec: float = 0.0
    #: Decision du jury, si la deliberation existe. Jamais recalculee ici.
    validation: Optional[str] = None
    credits_obtenus: Optional[int] = None
    mention: Optional[str] = None

    @property
    def notee(self) -> bool:
        return self.mue is not None


@dataclass
class BilanSemestre:
    """Le bilan d'un semestre, tel qu'un bulletin doit le porter."""

    semestre_id: str
    numero: int
    libelle: str
    date_debut: Optional[date] = None
    date_fin: Optional[date] = None
    session_id: Optional[str] = None
    #: UE du semestre : elles seules comptent dans la moyenne du semestre.
    #: Y figurent aussi les UE **annuelles** notees sur ce semestre — une UE
    #: annuelle se retrouve sur chaque semestre, c'est sa definition.
    unites: List[MoyenneUE] = field(default_factory=list)
    #: UE annuelles **sans aucune note sur ce semestre**. Elles n'ont rien a
    #: afficher ici, et le silence serait trompeur : il se lirait comme une UE
    #: semestrielle disparue, alors qu'elle est bien annuelle.
    annuelles_sans_note: List[Dict[str, Any]] = field(default_factory=list)
    #: UE sans semestre : ni semestrielle, ni annuelle. C'est une donnee
    #: manquante, pas un choix, et elle se rattrape autrement qu'une annuelle.
    unites_exclues: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def moyenne(self) -> Optional[float]:
        """Moyenne du semestre, ponderee par les credits d'UE.

        Elle pondere les MUE **sans arrondi** (``mue_exact``), jamais les MUE
        affichees : arrondir a chaque niveau ferait deriver la moyenne du
        semestre de celle que l'institut calcule.

        Les UE annuelles y entrent comme les autres, avec **leurs** notes de ce
        semestre. C'est ce qui les fait figurer sur les deux bulletins, et ce
        qui rend le recapitulatif annuel juste sans traitement particulier :
        il n'est que la moyenne ponderee des deux semestres.
        """

        notees = [ue for ue in self.unites if ue.mue_exact is not None and ue.cue]
        valeurs = [(ue.mue_exact, float(ue.cue)) for ue in notees]
        moyenne = _moyenne_ponderee(valeurs)
        return _arrondi(moyenne) if moyenne is not None else None

    @property
    def moyenne_exacte(self) -> Optional[float]:
        """La moyenne du semestre sans arrondi, pour le recapitulatif annuel."""

        notees = [ue for ue in self.unites if ue.mue_exact is not None and ue.cue]
        return _moyenne_ponderee([(ue.mue_exact, float(ue.cue)) for ue in notees])

    @property
    def credits_prevus(self) -> int:
        """Credits du semestre, UE annuelles comprises.

        Une UE annuelle porte ses credits dans **chaque** semestre ou elle
        figure. L'institut choisit ce qu'il y inscrit : l'entier, ou la part
        correspondant au semestre. Le recapitulatif annuel, moyenne ponderee des
        deux bulletins, reste juste dans les deux cas — c'est pourquoi rien ici
        ne dedouble ni ne deduit.
        """

        return sum(ue.cue for ue in self.unites)

    @property
    def credits_obtenus(self) -> int:
        return sum(ue.credits_obtenus or 0 for ue in self.unites)

    @property
    def porte_recapitulatif(self) -> bool:
        """Un semestre pair porte le recapitulatif de l'impair qui precede.

        Le regle tient a la parite du numero, pas a un reglage : les annees de
        diplome LMD couvrent deux semestres, et le recapitulatif se lit sur le
        second. Un semestre 4 recapitule le 3, un semestre 6 le 5.
        """

        return self.numero % 2 == 0

    def resume(self) -> Dict[str, Any]:
        return {
            "semestre_id": self.semestre_id,
            "numero": self.numero,
            "libelle": self.libelle,
            "moyenne": self.moyenne,
            "credits_prevus": self.credits_prevus,
            "credits_obtenus": self.credits_obtenus,
            "unites": len(self.unites),
            "unites_annuelles": sum(1 for ue in self.unites if ue.annuelle),
            "annuelles_sans_note": len(self.annuelles_sans_note),
            "unites_exclues": len(self.unites_exclues),
            "porte_recapitulatif": self.porte_recapitulatif,
        }


# ---------------------------------------------------------------------------
# Chargement
# ---------------------------------------------------------------------------
async def _notes_de_la_session(
    db: AsyncSession, *, etudiant_id: str, session_id: str
) -> List[Tuple[Note, Matiere, Optional[UniteEnseignement]]]:
    """Toutes les notes de l'etudiant sur la session, UE comprise ou non.

    Le tri par semestre se fait **en Python**, apres le chargement, et non dans
    la clause ``WHERE`` : filtrer sur ``UniteEnseignement.semestre_id`` dans le
    SQL transformerait la jointure externe en jointure interne, et les matieres
    hors unite disparaitraient du resultat. Elles finiraient dans
    ``unites_exclues`` — une liste vide, qui se lit comme « tout va bien ».
    """
    stmt = (
        select(Note, Matiere, UniteEnseignement)
        .join(Matiere, Note.matiere_id == Matiere.id)
        .outerjoin(UniteEnseignement, Matiere.ue_id == UniteEnseignement.id)
        .where(Note.etudiant_id == etudiant_id, Note.session_id == session_id)
    )
    return list((await db.execute(stmt)).all())


def _construire_ue(
    ue: UniteEnseignement,
    semestre: Optional[Semestre],
    *,
    annuel: bool = False,
) -> MoyenneUE:
    return MoyenneUE(
        ue_id=ue.id,
        code=ue.code,
        nom=ue.nom,
        cue=int(ue.credits or 0),
        # Une UE annuelle appartient a tous les semestres : c'est le semestre
        # consulte qu'on porte ici, pas un rattachement unique.
        semestre_id=semestre.id if semestre is not None else None,
        semestre_libelle=semestre.libelle if semestre is not None else None,
        annuelle=annuel,
    )


def _ajouter_note(
    entree: MoyenneUE,
    matiere: Matiere,
    note: Note,
    examens: Dict[str, Examen],
) -> None:
    """Range une note dans la matiere correspondante et met a jour ses moyennes."""

    matiere_ue = next((m for m in entree.matieres if m.matiere_id == matiere.id), None)
    if matiere_ue is None:
        matiere_ue = MoyenneMatiere(
            matiere_id=matiere.id,
            nom=matiere.nom,
            code=matiere.code,
            cec=float(matiere.coefficient or 1.0),
            evaluations=[],
        )
        entree.matieres.append(matiere_ue)

    coefficient = float(note.coefficient or matiere.coefficient or 1.0)
    examen = examens.get(note.examen_id or "")
    libelle = examen.nom if examen is not None else "Note directe"
    type_examen = examen.type_examen if examen is not None else None
    matiere_ue.evaluations.append({
        "id": note.id,
        "libelle": libelle,
        "type": type_examen,
        "valeur": float(note.valeur),
        "coefficient": coefficient,
    })


def _calculer_matiere(matiere_ue: MoyenneMatiere) -> None:
    """MEC, puis les moyennes de groupe.

    Le **MEC** pondere chaque evaluation par son coefficient. Les colonnes MCC
    et EXAM sont des **moyennes simples de leur groupe** : deux devoirs
    donnent ``(devoir1 + devoir2) / 2``, sans ponderation interne. C'est la
    regle de l'institut, confirmee le 26/09 — le cas se presente rarement, et
    il ne presente pas d'interet a le sur ponderer.

    Consequence a garder en tete : la ponderation vit au niveau du **MEC**, la
    moyenne de groupe est une simple information. Deux devoirs a l'interieur
    d'un groupe n'ont donc pas le meme poids dans la moyenne de groupe, meme
    si le MEC, lui, les pondere. Le detail des evaluations est joint pour que
    cette lecture reste verifiable.
    """

    couples = [
        (entree["valeur"], float(entree["coefficient"] or 1.0))
        for entree in matiere_ue.evaluations
    ]
    mecane = _moyenne_ponderee(couples)
    if mecane is not None:
        matiere_ue.mec_exact = mecane
        matiere_ue.mec = _arrondi(mecane)

    controles = [
        entree["valeur"] for entree in matiere_ue.evaluations
        if entree["type"] == TYPE_CONTROLE
    ]
    if controles:
        matiere_ue.mcc = _arrondi(sum(controles) / len(controles))

    examens = [
        entree["valeur"] for entree in matiere_ue.evaluations
        if entree["type"] in TYPES_EXAMEN
    ]
    if examens:
        matiere_ue.exam = _arrondi(sum(examens) / len(examens))


def _calculer_ue(entree: MoyenneUE) -> None:
    for matiere_ue in entree.matieres:
        _calculer_matiere(matiere_ue)
        entree.somme_cec += matiere_ue.cec
    couples = [
        (m.mec_exact, m.cec) for m in entree.matieres if m.mec_exact is not None
    ]
    moyenne = _moyenne_ponderee(couples)
    if moyenne is not None:
        entree.mue_exact = moyenne
        entree.mue = _arrondi(moyenne)


async def bilan_semestre(
    db: AsyncSession,
    *,
    etudiant_id: str,
    session_id: str,
    semestre_id: str,
    decisions: Optional[Dict[str, Dict[str, Any]]] = None,
) -> BilanSemestre:
    """Bilan d'un etudiant pour un semestre.

    ``decisions`` vient de la deliberation : ``{cle_ue: {validation,
    credits_obtenus, mention}}``. Ce module ne les recalcule pas — le jury
    tranche, le bulletin se contente de les imprimer.
    """

    semestre = await db.get(Semestre, semestre_id)
    if semestre is None:
        raise ValueError(
            f"Le semestre {semestre_id} n'existe pas. Un bulletin sans semestre "
            "n'a pas de perimetre."
        )

    lignes = await _notes_de_la_session(
        db, etudiant_id=etudiant_id, session_id=session_id
    )
    if not lignes:
        raise ValueError(
            "Aucune note pour cet étudiant sur cette session : il n'y a rien à "
            "publier. Un bulletin sans notes ferait croire à un zéro."
        )

    # Un seul aller-retour pour les evaluations partagees par plusieurs notes.
    ids_examen = {note.examen_id for note, _, _ in lignes if note.examen_id}
    examens: Dict[str, Examen] = {}
    if ids_examen:
        examens = {
            examen.id: examen
            for examen in (await db.execute(
                select(Examen).where(Examen.id.in_(ids_examen))
            )).scalars().all()
        }

    par_ue: Dict[str, Tuple[MoyenneUE, UniteEnseignement]] = {}
    # Les UE annuelles vues sur ce semestre, et celles ecartees de la periode
    # parce que leur note appartient a un autre semestre.
    annuelles_totales: List[str] = []
    annuelles_sans_note: List[Dict[str, Any]] = []
    exclues: List[Dict[str, Any]] = []
    vues: set = set()

    for note, matiere, ue in lignes:
        if ue is None:
            # Une matiere hors UE n'a ni CEC ni CUE : elle ne peut pas peser
            # dans une moyenne d'UE. Elle est signalee, pas comptee au hasard.
            exclues.append({
                "matiere": matiere.nom,
                "code": matiere.code,
                "note": float(note.valeur),
                "raison": "La matière n'est rattachée à aucune unité d'enseignement.",
            })
            continue

        if ue.regime == REGIME_ANNUELLE:
            # Une UE annuelle est notee sur **chaque** semestre. C'est la note
            # qui dit a quel semestre elle appartient : sans elle, les notes de
            # S1 et de S2 se confondraient en une moyenne qui ne correspondrait
            # a aucun des deux.
            if ue.id not in annuelles_totales:
                annuelles_totales.append(ue.id)
            if note.semestre_id is not None and note.semestre_id != semestre_id:
                # Note d'un autre semestre : c'est le fonctionnement attendu.
                # Aucune UE n'est signalee, mais le silence n'est pas complet —
                # ``annuelles_sans_note`` dira que cette UE annuelle n'a rien
                # a afficher sur ce semestre, plutot que de laisser croire
                # qu'elle est evaluee une fois pour l'annee.
                continue

            entree = par_ue.get(ue.id)
            if entree is None:
                entree = (_construire_ue(ue, semestre, annuel=True), ue)
                par_ue[ue.id] = entree
            _ajouter_note(entree[0], matiere, note, examens)
            continue

        if ue.semestre_id is None:
            # Semestrielle sans semestre : ni sur ce bulletin ni sur un autre.
            # C'est une donnee manquante, et non un regime — d'ou le signalement.
            if ue.id not in vues:
                vues.add(ue.id)
                exclues.append({
                    "matiere": ue.nom,
                    "code": ue.code,
                    "note": None,
                    "raison": (
                        "L'unité d'enseignement est semestrielle mais n'est "
                        "rattachée à aucun semestre."
                    ),
                })
            continue
        if ue.semestre_id != semestre_id:
            # Elle appartient a un autre semestre : c'est le comportement
            # attendu, pas une anomalie. Aucun signalement.
            continue

        entree = par_ue.get(ue.id)
        if entree is None:
            entree = (_construire_ue(ue, semestre), ue)
            par_ue[ue.id] = entree
        _ajouter_note(entree[0], matiere, note, examens)

    # Une UE annuelle dont aucune note ne tombe sur ce semestre n'apparait pas
    # dans ``unites`` — et c'est correct. Mais l'agent doit pouvoir distinguer
    # « pas notee ici » de « pas annuelle du tout » : sans cette liste, une UE
    # annuelle entierement notee en S2 laisserait le bulletin de S1 muet, ce
    # qui se lirait comme une UE semestrielle qui aurait disparu.
    par_code = {entree.ue_id: entree for entree, _ in par_ue.values()}
    for note, matiere, ue in lignes:
        if ue is None or ue.regime != REGIME_ANNUELLE:
            continue
        if ue.id in par_code or ue.id in [e["ue_id"] for e in annuelles_sans_note]:
            continue
        entree = _construire_ue(ue, semestre, annuel=True)
        annuelles_sans_note.append({
            "ue_id": ue.id,
            "unite": entree.nom,
            "code": entree.code,
            "raison": (
                "Enseignement annuel : aucune note ne porte sur ce semestre. "
                "Le rattachement de la note au semestre est manquant."
            ),
        })

    for entree, _ue in par_ue.values():
        _calculer_ue(entree)
        if decisions:
            cle = f"{entree.ue_id}"
            decision = decisions.get(cle) or decisions.get(entree.code) or {}
            entree.validation = decision.get("validation")
            credits = decision.get("credits_obtenus")
            entree.credits_obtenus = int(credits) if credits is not None else None
            entree.mention = decision.get("mention")

    # Le code de l'UE est l'ordre de lecture du bulletin : UE1.2.1 avant
    # UE1.2.10, comme sur les releves.
    ordered = sorted(par_ue.values(), key=lambda paire: paire[1].code)

    return BilanSemestre(
        semestre_id=semestre.id,
        numero=semestre.numero,
        libelle=semestre.libelle,
        date_debut=semestre.date_debut,
        date_fin=semestre.date_fin,
        session_id=semestre.session_id,
        unites=[entree for entree, _ue in ordered],
        annuelles_sans_note=annuelles_sans_note,
        unites_exclues=exclues,
    )


async def recap_annuel(
    db: AsyncSession,
    *,
    etudiant_id: str,
    session_id: str,
    semestre_id: str,
    decisions: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """Bilan des deux semestres d'une annee, ou ``None`` sur un semestre impair.

    Le recapitulatif n'existe que sur les semestres pairs. Sur un impair, le
    rendre vide laisserait croire que l'etudiant n'a pas d'historique annuel —
    alors que le document n'en prevoyait simplement pas.
    """

    courant = await bilan_semestre(
        db,
        etudiant_id=etudiant_id,
        session_id=session_id,
        semestre_id=semestre_id,
        decisions=decisions,
    )
    if not courant.porte_recapitulatif:
        return None

    semestre = await db.get(Semestre, semestre_id)
    assert semestre is not None  # garantie par bilan_semestre
    precedent = (
        await db.execute(
            select(Semestre).where(
                Semestre.session_id == semestre.session_id,
                Semestre.numero == semestre.numero - 1,
            )
        )
    ).scalars().first()
    if precedent is None:
        # Un semestre 2 sans semestre 1 : le recapitulatif ne peut pas etre
        # complet, et une moyenne generale sur un seul semestre ne serait pas
        # une moyenne generale.
        return None

    anterieur = await bilan_semestre(
        db,
        etudiant_id=etudiant_id,
        session_id=session_id,
        semestre_id=precedent.id,
        decisions=decisions,
    )

    # Le recapitulatif annuel n'a **aucun** traitement particulier des UE
    # annuelles : c'est la moyenne ponderee des deux bulletins de semestre.
    # Elles y entrent deja, par chaque semestre ou elles sont notees, avec les
    # credits que l'institut a ports. C'est ce qui evite d'avoir a choisir a
    # leur place si ces credits se repetent ou se partagent.
    credits = anterieur.credits_prevus + courant.credits_prevus
    moyenne_annuelle = None
    couples = [
        (bilan.moyenne_exacte, float(bilan.credits_prevus))
        for bilan in (anterieur, courant)
        if bilan.moyenne_exacte is not None and bilan.credits_prevus
    ]
    if couples:
        valeur = _moyenne_ponderee(couples)
        moyenne_annuelle = _arrondi(valeur) if valeur is not None else None

    return {
        "precedent": anterieur,
        "courant": courant,
        "credits_precedent": anterieur.credits_prevus,
        "credits_courant": courant.credits_prevus,
        "credits_total": credits,
        "moyenne_precedente": anterieur.moyenne,
        "moyenne_courante": courant.moyenne,
        "moyenne_annuelle": moyenne_annuelle,
    }


__all__ = [
    "BilanSemestre",
    "MoyenneMatiere",
    "MoyenneUE",
    "TYPES_EXAMEN",
    "TYPE_CONTROLE",
    "bilan_semestre",
    "recap_annuel",
]
