"""Contenu du bulletin de notes d'un semestre.

Ce module decide **ce que le bulletin dit** ; ``bulletin_pdf`` decide seulement
comment c'est imprime. La separation est la meme que pour la lettre de
relance, et pour la meme raison : la mise en page se teste mal, et elle ne doit
rien decider.

Trois partis pris, tous dictes par les releves de l'institut.

**Une UE = un en-tete fusionne, puis ses matieres, puis un sous-total.**
L'en-tete porte le code, l'intitule et le CUE ; chaque ligne de matiere porte
MCC, EXAM, CEC et MEC ; la derniere ligne de l'UE porte la MUE. C'est la
structure des releves, et elle dit d'un coup d'oeil a quoi se rapporte chaque
nombre.

**L'arreti se fait en fin de chaine.** Les valeurs affichees sont arrondies,
mais les moyennes parentes le sont sur les valeurs exactes — voir
``semestre_service``. Un bulletin qui afficherait 10,84 la ou l'institut imprime
10,83 ne serait pas un bulletin, ce serait un autre document portant le meme
nom.

**Une case vide ne dit pas pourquoi elle est vide.** Trois etats, trois
rendus : une valeur, un tiret quand la colonne ne s'applique pas (pas de
controle continu dans cette matiere), et une mention explicite quand la
donnee manque. Aucun blanc, jamais.

Ce que le module ne fait pas : il ne decide ni de la validation, ni des
mentions. Ces deux-là viennent du jury, par la deliberation, et le bulletin se
contente de les imprimer. Un bulletin qui recalculerait le sort de l'etudiant
serait un second jury, en papier.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from app.services.deliberation_service import mention_pour
from app.services.semestre_service import BilanSemestre, MoyenneUE

#: Rendu d'une colonne sans valeur. **Pas** un tiret, et surtout pas un zero.
#:
#: La raison est delicate. Une matiere notee par un seul devoir afficherait « — »
#: en colonne examen ; cela affirmerait qu'aucun examen n'existe, alors qu'on
#: ne peut pas distinguer « pas d'examen » de « examen non saisi ». Le tiret
#: serait une affirmation de trop.
#:
#: « n. c. » — non communique — ne pretend rien. Il dit que la valeur n'est pas
#: connue, ce qui est exactement ce que l'on sait. C'est la notation des
#: releves francais, et elle se rencontre sur ce genre de document.
NON_RENSEIGNE = "n. c."


def _nombre(valeur: Optional[float], decimales: int = 2) -> str:
    """Formate un nombre a la francaise, ou le rendu de son absence.

    Le separateur decimal suit la locale de l'institut : leurs releves ecrivent
    « 12,51 ». Un bulletin qui ecrit « 12.51 » pour les memes notes serait
    rejete par l'etudiant avant d'etre lu.
    """

    if valeur is None:
        return NON_RENSEIGNE
    texte = f"{valeur:.{decimales}f}"
    return texte.replace(".", ",")


def _entier(valeur: Optional[int]) -> str:
    if valeur is None:
        return NON_RENSEIGNE
    return str(int(valeur))


@dataclass
class LigneMatiere:
    """Une matiere dans le tableau d'une UE."""

    code: str
    nom: str
    #: Moyenne controlee, moyenne simple des evaluations de type CC.
    mcc: Optional[float] = None
    #: Moyenne d'examen, moyenne simple des evaluations d'examen.
    exam: Optional[float] = None
    #: Coefficient de l'element constitutif dans son UE — la colonne CEC.
    cec: float = 1.0
    #: Moyenne de la matiere — la colonne MEC.
    mec: Optional[float] = None

    def cec_texte(self) -> str:
        return _nombre(self.cec)


@dataclass
class BlocUE:
    """Une unite d'enseignement : son en-tete, ses matieres, son sous-total."""

    code: str
    nom: str
    #: Credit propre de l'UE — la colonne CUE. **Pas** la somme des CEC.
    cue: int
    #: L'enseignement est annuel : il figure sur chaque semestre, et le
    #: bulletin le dit, pour que deux UE identiques sur deux bulletins ne
    #: paraissent pas une erreur de saisie.
    annuelle: bool = False
    matieres: List[LigneMatiere] = field(default_factory=list)
    #: Moyenne de l'UE — la colonne MUE.
    mue: Optional[float] = None
    mention: Optional[str] = None
    #: Decision du jury pour cette UE, imprimee telle qu'elle a ete prise.
    #: Jamais recalculee, jamais devinee.
    validation: Optional[str] = None
    credits_obtenus: Optional[int] = None
    #: Ce que le moteur proposait, quand le jury n'a pas tranche. Imprime
    #: **comme une proposition**, avec la mention qui le dit. Confondre les
    #: deux afficherait un verdict que le jury n'a jamais prononce.
    proposition_validation: Optional[str] = None
    proposition_mention: Optional[str] = None

    @property
    def notee(self) -> bool:
        return self.mue is not None

    @property
    def decidee(self) -> bool:
        """Le jury a-t-il tranche pour cette UE ?"""

        return self.validation is not None


@dataclass
class LigneRecapitulatif:
    """Une ligne du recapitulatif annuel."""

    libelle: str
    credits: Optional[int] = None
    moyenne: Optional[float] = None
    #: ``None`` sur la ligne de synthese : elle n'est pas un semestre.
    mis_en_forme: bool = False


@dataclass
class Bulletin:
    """Le contenu d'un bulletin, pret a etre mis en page.

    L'ordre des champs suit la lecture du document : ce qui identifie le
    bulletin, puis son destinataire, puis la periode, puis les notes. Les deux
    noms sont les seuls obligatoires — sans eux, le document ne dit pas a qui il
    s'adresse, et il ne doit pas partir.
    """

    # -- Destinataire, les deux seules donnees obligatoires -----------
    etudiant_nom: str
    etudiant_prenom: str
    etablissement_nom: str

    # -- Identite de l'etablissement ---------------------------------
    etablissement_sigle: Optional[str] = None
    etablissement_adresse: Optional[str] = None
    etablissement_telephone: Optional[str] = None
    etablissement_email: Optional[str] = None
    etablissement_pays: Optional[str] = None
    logo_url: Optional[str] = None

    # -- Suite de l'identite de l'etudiant ---------------------------
    matricule: Optional[str] = None
    filiere: Optional[str] = None
    niveau: Optional[str] = None
    classe: Optional[str] = None
    date_naissance: Optional[str] = None

    # -- Periode ----------------------------------------------------
    session_nom: Optional[str] = None
    session_annee: Optional[str] = None
    semestre_numero: int = 1
    semestre_libelle: str = ""

    # -- Notes --------------------------------------------------------
    blocs: List[BlocUE] = field(default_factory=list)
    credits_prevus: int = 0
    credits_obtenus: int = 0
    moyenne_semestre: Optional[float] = None
    mention_semestre: Optional[str] = None

    # -- Recapitulatif annuel, sur un semestre pair seulement --------
    recapitulatif: List[LigneRecapitulatif] = field(default_factory=list)
    moyenne_annuelle: Optional[float] = None
    mention_annuelle: Optional[str] = None

    #: Enseignements annuels notes ailleurs : ils ne figurent pas ici, et le
    #: bulletin le dit plutot que de laisser croire a une UE disparue.
    annuelles_absentes: List[Dict[str, Any]] = field(default_factory=list)
    #: UE et matieres hors de tout bulletin, avec la raison. Un bulletin muet
    #: sur ce point ferait croire que tout est entre dans le calcul.
    hors_bulletin: List[Dict[str, Any]] = field(default_factory=list)
    #: Matieres dont certaines colonnes sont remplies et d'autres non. C'est la
    #: seule incoherence que les donnees revelent **sans** supposer le plan de
    #: l'institut : un devoir sans examen, ou l'inverse. Elle est signalee
    #: parce que le signe « n. c. » ne dit pas s'il manque une note ou une
    #: epreuve.
    incompletudes: List[Dict[str, Any]] = field(default_factory=list)
    #: Aucune deliberation enregistree pour cet etudiant sur cette session.
    #:
    #: Distinct de « deliberation tenue mais sans decision » : ici, le jury ne
    #: s'est pas prononce, et le bulletin ne doit pas laisser croire qu'il l'a
    #: fait. Un bulletin sans mention ni credits obtenus le dirait, mais
    #: l'absence se lirait comme un oubli de saisie plutot que comme une
    #: decision de ne pas decider.
    deliberation_absente: bool = False
    #: UE pour lesquelles le jury n'a pas tranche. Elles portent une proposition
    #: du moteur, clairement marquee comme telle, et le bulletin le dit en bas.
    #: Sans cette liste, un bulletin affichant « proposition : Validee » pour
    #: toutes les UE se lirait comme une seance de jury tenue.
    unites_non_decidees: List[str] = field(default_factory=list)

    def credits_annuels(self) -> int:
        return sum(bloc.cue for bloc in self.blocs if bloc.annuelle)

    def matieres(self) -> int:
        return sum(len(bloc.matieres) for bloc in self.blocs)


def _incompletudes(bilan: BilanSemestre) -> List[Dict[str, Any]]:
    """Les matieres dont les colonnes se contredisent.

    On ne peut pas savoir combien d'evaluations une matiere **devrait** avoir :
    cela depend du plan de l'institut, qui n'est pas une donnee. Ce qu'on peut
    voir, en revanche, c'est une matiere notee par un controle et **sans**
    examen, ou l'inverse — un des deux groupes existe, l'autre non. C'est une
    incoherence interne, independante de toute convention.

    Une matiere notee par un seul controle, sans rien d'autre, n'est **pas**
    signalee : on n'a aucune preuve qu'il manque quoi que ce soit, et signaler
    une normalite sur tous les bulletins ferait perdre leur sens aux
    signaux reels.
    """

    trouvees: List[Dict[str, Any]] = []
    for ue in bilan.unites:
        for matiere in ue.matieres:
            if (matiere.mcc is None) == (matiere.exam is None):
                # Les deux colonnes remplies, ou les deux vides : rien a dire.
                continue
            trouvees.append({
                "unite": ue.code,
                "matiere": matiere.nom,
                "code": matiere.code,
                "manque": "examen" if matiere.exam is None else "contrôle continu",
            })
    return trouvees


def _ligne_matiere(matiere) -> LigneMatiere:
    return LigneMatiere(
        code=matiere.code,
        nom=matiere.nom,
        mcc=matiere.mcc,
        exam=matiere.exam,
        cec=matiere.cec,
        mec=matiere.mec,
    )


def _bloc_ue(ue: MoyenneUE) -> BlocUE:
    return BlocUE(
        code=ue.code,
        nom=ue.nom,
        cue=ue.cue,
        annuelle=ue.annuelle,
        matieres=[_ligne_matiere(m) for m in ue.matieres],
        mue=ue.mue,
        mention=ue.mention,
        validation=ue.validation,
        credits_obtenus=ue.credits_obtenus,
        proposition_validation=ue.proposition_validation,
        proposition_mention=ue.proposition_mention,
    )


def composer_bulletin(
    bilan: BilanSemestre,
    *,
    infos: Dict[str, Any],
    recap: Optional[Dict[str, Any]] = None,
) -> Bulletin:
    """Construit le contenu du bulletin a partir d'un bilan de semestre.

    Fonction **pure** : elle ne lit ni la base, ni le jury. Elle rend ce que les
    donnees disent, y compris ce qu'elles ne disent pas — les absences sont
    reportees dans ``hors_bulletin`` et ``annuelles_absentes``, pas dissimulees
    par une cellule vide.

    ``infos`` porte l'identite de l'etablissement et de l'etudiant. Les
    valeurs manquantes y restent ``None`` et sont rendues par ``NON_RENSEIGNE``
    plutot qu'inventees.
    """

    etudiant = infos.get("etudiant") or {}
    session = infos.get("session") or {}
    etablissement = infos.get("etablissement") or {}

    bulletin = Bulletin(
        etudiant_nom=str(etudiant.get("nom") or ""),
        etudiant_prenom=str(etudiant.get("prenom") or ""),
        etablissement_nom=str(etablissement.get("nom") or ""),
        etablissement_sigle=etablissement.get("sigle"),
        etablissement_adresse=etablissement.get("adresse"),
        etablissement_telephone=etablissement.get("telephone"),
        etablissement_email=etablissement.get("email"),
        etablissement_pays=etablissement.get("pays"),
        logo_url=etablissement.get("logo_url"),
        matricule=etudiant.get("matricule"),
        filiere=etudiant.get("filiere"),
        niveau=etudiant.get("niveau"),
        classe=etudiant.get("classe"),
        date_naissance=etudiant.get("date_naissance"),
        session_nom=session.get("nom"),
        session_annee=session.get("annee_academique"),
        semestre_numero=bilan.numero,
        semestre_libelle=bilan.libelle,
        blocs=[_bloc_ue(ue) for ue in bilan.unites],
        credits_prevus=bilan.credits_prevus,
        credits_obtenus=bilan.credits_obtenus,
        moyenne_semestre=bilan.moyenne,
        annuelles_absentes=list(bilan.annuelles_sans_note),
        hors_bulletin=list(bilan.unites_exclues),
        incompletudes=_incompletudes(bilan),
    )

    # Le jury a-t-il tranche pour chaque UE ? La reponse decide de ce que le
    # bulletin affiche : une decision, ou une proposition **marquee** comme
    # telle. Le decompte se fait ici, sur les blocs, plutot que dans la mise en
    # page — le contenu d'un bulletin se decide hors du PDF.
    bulletin.unites_non_decidees = [
        bloc.code
        for bloc in bulletin.blocs
        if not bloc.decidee and bloc.proposition_validation
    ]

    # La mention du semestre se lit sur sa moyenne. Elle est **imprimee**, elle
    # ne decide de rien : le seuil d'admission reste celui du jury.
    bareme: Sequence[Dict[str, Any]] = infos.get("bareme_mentions") or []
    if bilan.moyenne is not None and bareme:
        bulletin.mention_semestre = mention_pour(bilan.moyenne, bareme)

    if recap is None:
        return bulletin

    anterieur = recap.get("precedent")
    courant = recap.get("courant")
    bulletin.recapitulatif = [
        LigneRecapitulatif(
            libelle=str(getattr(anterieur, "libelle", "") or "Semestre précédent"),
            credits=getattr(anterieur, "credits_prevus", None),
            moyenne=getattr(anterieur, "moyenne", None),
        ),
        LigneRecapitulatif(
            libelle=str(getattr(courant, "libelle", "") or "Semestre courant"),
            credits=getattr(courant, "credits_prevus", None),
            moyenne=getattr(courant, "moyenne", None),
        ),
    ]
    bulletin.moyenne_annuelle = recap.get("moyenne_annuelle")
    if bulletin.moyenne_annuelle is not None and bareme:
        bulletin.mention_annuelle = mention_pour(
            bulletin.moyenne_annuelle, bareme
        )

    return bulletin


__all__ = [
    "BlocUE",
    "Bulletin",
    "LigneMatiere",
    "LigneRecapitulatif",
    "NON_RENSEIGNE",
    "composer_bulletin",
]
