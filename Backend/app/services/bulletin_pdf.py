"""Mise en page du bulletin de notes d'un semestre.

Ce module ne decide **rien**. Il ne calcule aucune moyenne, n'invente aucune
mention, ne complete aucune case : il recoit un :class:`~app.services.bulletin_service.Bulletin`
et l'imprime. C'est ce qui permet de tester le contenu sans passer par le PDF,
et ce qui garantit que deux documents differences ne peuvent pas diverger sur
leur contenu.

La structure suit les releves de l'institut :

- une ligne d'en-tete **fusionnee** par unite d'enseignement, portant son code,
  son intitule et son CUE ;
- une ligne par matiere, avec MCC, EXAM, CEC et MEC ;
- une ligne de sous-total portant le CUE et la MUE ;
- le total du semestre, puis le recapitulatif annuel sur les semestres pairs ;
- enfin la signature.

**Ni cachet ni signature ne sont imprimes.** L'institut signe et tamponne a la
main : le PDF sort de l'imprimante et se complete au stylo. Pre-remplir une
signature — meme par une image, meme par un nom — fabriquerait un document
semblant signe, ce qui n'est pas la meme chose qu'un document signe. La zone
laissee est donc **vide**, et elle est assez grande pour etre signee.
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.bulletin_service import (
    NON_RENSEIGNE,
    BlocUE,
    Bulletin,
    LigneRecapitulatif,
    _nombre,
)
from app.services.pdf_service import (
    ACCENT,
    GRIS_BORD,
    GRIS_CLAIR,
    GRIS_TEXTE,
    VALEUR_ABSENTE,
    _police_disponible,
    _styles,
)

#: Marges du document. Fixees ici parce que **toutes** les largeurs de colonnes
#: en dependent : un tableau plus large que la page deborde dans la marge
#: droite.
MARGE = 18 * mm
LARGEUR_UTILE = A4[0] - 2 * MARGE


def _largeurs(*proportions: float) -> List[float]:
    """Repartit la largeur utile selon des proportions.

    Les largeurs ne s'ecrivent plus en millimetres. C'etait la source du
    defaut : cinq tableaux independants donnaient chacun 180 mm pour une
    largeur utile de 174, et aucun ne pouvait le signaler tout seul. Ici, la
    somme est la largeur utile **par construction** — impossible de deborder,
    et impossible qu'un tableau etire les colonnes d'un autre.
    """

    total = sum(proportions)
    return [LARGEUR_UTILE * part / total for part in proportions]


#: Colonnes du tableau principal. Les proportions suivent les releves : on lit
#: les controles, puis le coefficient, puis la moyenne qui en decoule. Six
#: colonnes, pas sept : on n'invente pas de colonne pour y loger la validation
#: du jury — elle est ecrite dans l'intitule du sous-total, ou elle tient.
COLONNES = [
    ("Code", 20),
    ("Intitulé", 74),
    ("Moy. contrôle", 22),
    ("Moy. examen", 22),
    ("CEC", 14),
    ("Moy. matière", 22),
]

#: Hauteur de la zone reservee au cachet. Assez grande pour un tampon, vide.
HAUTEUR_CACHET = 28 * mm


def _cellule(styles, texte: str, cle: str = "cellule") -> Paragraph:
    return Paragraph(texte, styles[cle])


def _ligne_entete_ue(styles, bloc: BlocUE) -> List[Any]:
    """L'en-tele d'une UE : une seule ligne, fusionnee sur toute la largeur.

    Le CUE figure dans cette ligne, pas dans le sous-total : c'est lui qui dit
    de combien l'UE pese dans la moyenne du semestre, et le lecteur doit le
    voir entilesant l'intitule.
    """

    intitule = bloc.nom
    if bloc.annuelle:
        # Un enseignement annuel figure sur chaque semestre. Le dire ici evite
        # que deux UE identiques sur deux bulletins paraissent une erreur.
        intitule = f"{intitule} <i>(enseignement annuel)</i>"

    # Les quatre cellules de droite sont vides et fusionnees a elles aussi :
    # une ligne d'en-tete qui laisse voir des colonnes vides ressemblerait a
    # une matiere sans note.
    contenu: List[Any] = [
        _cellule(styles, f"<b>{bloc.code}</b>"),
        _cellule(styles, intitule),
        _cellule(styles, ""),
        _cellule(styles, ""),
        _cellule(styles, ""),
        _cellule(styles, f"<b>CUE {bloc.cue}</b>", "cellule_droite"),
    ]
    return contenu


def _ligne_matiere(styles, matiere) -> List[Any]:
    return [
        _cellule(styles, matiere.code),
        _cellule(styles, matiere.nom),
        _cellule(styles, _nombre(matiere.mcc), "cellule_droite"),
        _cellule(styles, _nombre(matiere.exam), "cellule_droite"),
        _cellule(styles, matiere.cec_texte(), "cellule_droite"),
        _cellule(styles, _nombre(matiere.mec), "cellule_droite"),
    ]


def _ligne_sous_total(styles, bloc: BlocUE) -> List[Any]:
    """Le sous-total d'une UE : sa MUE, sa mention, et la decision du jury.

    Le tout tient dans l'intitule, pas dans une colonne supplementaire : le
    releve de reference en a six, et la mise en page n'a pas a en inventer une
    septieme. La decision du jury — valide, valide en rattrapage, a reprendre —
    n'est de toute facon pas une donnee de calcul ; elle est **imprimee**, la
    mise en page ne la produit pas.
    """

    morceaux = [f"Total UE ({bloc.cue} crédit(s)"]
    if bloc.mention:
        morceaux.append(f"— {bloc.mention}")
    morceaux.append(")")
    intitule = "".join(morceaux)

    if bloc.decidee:
        # Le jury a tranche. On imprime sa decision, et elle seule.
        detail = bloc.validation or ""
        if bloc.credits_obtenus is not None:
            detail = f"{detail} — {bloc.credits_obtenus} crédit(s) obtenu(s)"
        intitule = f"{intitule} — <b>{detail}</b>"
    elif bloc.proposition_validation:
        # Le jury n'a pas tranche. Ce qui suit est une **proposition** du
        # moteur, et le dit sur la ligne. Imprimer « Validee » sans cette
        # precision attribuerait au jury une decision qu'il n'a pas prise.
        intitule = (
            f"{intitule} — <i>proposition du moteur : "
            f"{bloc.proposition_validation} — non tranche par le jury</i>"
        )

    return [
        _cellule(styles, ""),
        _cellule(styles, f"<b>{intitule}</b>"),
        _cellule(styles, ""),
        _cellule(styles, ""),
        _cellule(styles, f"<b>{bloc.cue}</b>", "cellule_droite"),
        _cellule(styles, f"<b>{_nombre(bloc.mue)}</b>", "cellule_droite"),
    ]


def _tableau_notes(styles, bulletin: Bulletin) -> Table:
    """Le tableau principal : une en-tete de colonnes, puis un bloc par UE."""

    donnees: List[List[Any]] = [
        [
            _cellule(styles, titre, "cellule_entete")
            for titre, _largeur in COLONNES
        ]
    ]
    commandes: List[Tuple[Any, ...]] = [
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("GRID", (0, 0), (-1, 0), 0.5, GRIS_BORD),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        # La colonne code ne se comprime pas : elle identifie la ligne.
        ("LEFTPADDING", (0, 0), (0, -1), 4),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 4),
    ]

    for bloc in bulletin.blocs:
        premiere = len(donnees)
        donnees.append(_ligne_entete_ue(styles, bloc))
        # Fusion complete : l'en-tete est une seule cellule sur toute la
        # largeur. C'est ce qui fait qu'on sait a quoi se rapporte chaque
        # moyenne qui suit.
        commandes.append(("SPAN", (0, premiere), (-1, premiere)))
        commandes.append(("BACKGROUND", (0, premiere), (-1, premiere), GRIS_CLAIR))
        commandes.append(("LINEABOVE", (0, premiere), (-1, premiere), 0.7, GRIS_BORD))
        commandes.append(("TOPPADDING", (0, premiere), (-1, premiere), 3))
        commandes.append(("BOTTOMPADDING", (0, premiere), (-1, premiere), 3))

        for matiere in bloc.matieres:
            donnees.append(_ligne_matiere(styles, matiere))

        derniere = len(donnees)
        donnees.append(_ligne_sous_total(styles, bloc))
        commandes.append(("BACKGROUND", (0, derniere), (-1, derniere), GRIS_CLAIR))
        commandes.append(("LINEBELOW", (0, derniere), (-1, derniere), 0.7, GRIS_BORD))
        commandes.append(("BOTTOMPADDING", (0, derniere), (-1, derniere), 4))

    largeur = sum(largeur for _titre, largeur in COLONNES)
    return Table(donnees, colWidths=_largeurs(*[proportion for _t, proportion in COLONNES]),
                 style=TableStyle(commandes), repeatRows=1)


def _tableau_totaux(styles, bulletin: Bulletin) -> Table:
    """Le total du semestre : credits prevus, obtenus, moyenne et mention."""

    ligne = [
        _cellule(styles, "Total du semestre"),
        _cellule(styles, f"{bulletin.credits_prevus} crédit(s)"),
        _cellule(styles, f"{bulletin.credits_obtenus} obtenu(s)"),
        _cellule(styles, f"<b>{_nombre(bulletin.moyenne_semestre)}</b>"),
        _cellule(styles, bulletin.mention_semestre or VALEUR_ABSENTE),
    ]
    return Table(
        [ligne],
        colWidths=_largeurs(58, 32, 30, 30, 30),
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), GRIS_CLAIR),
                ("GRID", (0, 0), (-1, -1), 0.7, GRIS_BORD),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        ),
    )


def _tableau_recapitulatif(
    styles, bulletin: Bulletin
) -> Optional[Table]:
    """Le recapitulatif annuel — sur un semestre pair seulement.

    Sur un semestre impair, la fonction rend ``None`` : pas de bloc vide, pas
    de ligne a zero. L'absence se lirait sinon comme un historique manquant,
    alors que le document n'en prevoyait pas.
    """

    if not bulletin.recapitulatif:
        return None

    lignes: List[List[Any]] = [
        [
            _cellule(styles, titre, "cellule_entete")
            for titre in ("Période", "Crédits", "Moyenne")
        ]
    ]
    for entree in bulletin.recapitulatif:
        lignes.append([
            _cellule(styles, entree.libelle),
            _cellule(styles, _nombre_credits(entree.credits), "cellule_droite"),
            _cellule(styles, _nombre(entree.moyenne), "cellule_droite"),
        ])

    lignes.append([
        _cellule(styles, "<b>Moyenne générale</b>"),
        _cellule(styles, f"<b>{bulletin.credits_prevus + _credits_recapitulatif(bulletin)}</b>", "cellule_droite"),
        _cellule(
            styles,
            f"<b>{_nombre(bulletin.moyenne_annuelle)}</b> — "
            f"{bulletin.mention_annuelle or VALEUR_ABSENTE}",
            "cellule_droite",
        ),
    ])

    return Table(
        lignes,
        colWidths=_largeurs(80, 35, 65),
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
                ("GRID", (0, 0), (-1, -1), 0.5, GRIS_BORD),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, -1), (-1, -1), GRIS_CLAIR),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        ),
    )


def _credits_recapitulatif(bulletin: Bulletin) -> int:
    return sum(entree.credits or 0 for entree in bulletin.recapitulatif)


def _nombre_credits(valeur: Optional[int]) -> str:
    if valeur is None:
        return NON_RENSEIGNE
    return str(int(valeur))


def _encadre_reserves(styles, lignes: List[str], titre: str) -> List[Any]:
    """Les mentions que le bulletin doit porter malgre tout.

    Une UE hors programme, un enseignement annuel note ailleurs, une colonne
    contradictoire : ces trois choses ne se voient pas dans le tableau, et leur
    absence se lirait comme « tout va bien ». Elles sont donc ecrites, et
    nomment ce qui manque.

    L'encadre est colore, pas rouge : il constate un fait, il ne constate pas
    une faute. Le document doit pouvoir etre lu et signe tel quel.
    """

    if not lignes:
        return []

    donnees: List[List[Any]] = [
        [
            Paragraph(f"<b>{titre}</b>", styles["cellule"]),
            Paragraph("", styles["cellule"]),
        ]
    ]
    for ligne in lignes:
        donnees.append([
            Paragraph("•", styles["cellule"]),
            Paragraph(ligne, styles["cellule"]),
        ])

    return [
        Spacer(1, 4 * mm),
        Table(
            donnees,
            colWidths=_largeurs(5, 175),
            style=TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.5, GRIS_BORD),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.Color(1, 0.97, 0.9)),
                    # Le titre occupe les deux colonnes : il surmonte la liste.
                    ("SPAN", (0, 0), (1, 0)),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("LEFTPADDING", (0, 0), (0, -1), 2),
                ]
            ),
        ),
    ]


def _bloc_reserves(bulletin: Bulletin) -> List[str]:
    """Les phrases a ecrire sous le tableau, ou la liste vide."""

    lignes: List[str] = []

    if bulletin.unites_non_decidees:
        # Le moteur a propose, le jury n'a pas tranche. Sans cette ligne, les
        # UE porteraient « proposition : Validee » et le document se lirait
        # comme une seance de jury tenue.
        lignes.append(
            "Le jury n'a pas encore tranché pour "
            f"{len(bulletin.unites_non_decidees)} unité(s) d'enseignement "
            f"({', '.join(bulletin.unites_non_decidees[:8])}"
            + ("…" if len(bulletin.unites_non_decidees) > 8 else "")
            + "). Les mentions « proposition du moteur » qui figurent au "
            "tableau ne sont pas des décisions du jury."
        )

    if bulletin.deliberation_absente:
        # Distinguer « pas delibere » de « delibere sans decision » : le
        # bulletin ne doit pas laisser croire que le jury s'est prononce.
        lignes.append(
            "Aucune délibération n'est enregistrée pour cet étudiant sur cette "
            "session. Les décisions du jury (admission, rattrapage, crédits "
            "obtenus) ne figurent donc pas sur ce bulletin ; seules les moyennes "
            "y figurent."
        )

    for entree in bulletin.incompletudes:
        lignes.append(
            f"{entree['matiere']} ({entree['code']}) : un {entree['manque']} "
            "est noted sans l'autre. La colonne « n. c. » signale une valeur "
            "non communiquee, pas une absence d'epreuve."
        )
    for entree in bulletin.annuelles_absentes:
        lignes.append(
            f"{entree['code']} — {entree['unite']} : enseignement annuel "
            "sans note sur ce semestre. Il figure sur le bulletin du semestre "
            "ou il a ete note."
        )
    for entree in bulletin.hors_bulletin:
        lignes.append(
            f"{entree.get('code') or ''} — {entree.get('matiere') or ''} : "
            f"{entree.get('raison') or 'hors bulletin.'}"
        )

    return lignes


def _bloc_signature(styles, bulletin: Bulletin) -> List[Any]:
    """La signature et le cachet : deux zones **vides**.

    L'institut signe a la main. Pre-remplir — meme par un nom, meme par une
    image — fabriquerait un document qui *parait* signe sans l'etre. Les deux
    zones sont donc laissees vides, avec le nom du signataire et sa fonction
    imprimes au-dessus : le nom dit qui doit signer, pas qu'il a signe.
    """

    return [
        Spacer(1, 10 * mm),
        Table(
            [
                [Paragraph("Visa du jury", styles["signature"]),
                 Paragraph("Cachet de l'établissement", styles["signature"])],
            ],
            colWidths=_largeurs(90, 90),
            style=TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEABOVE", (0, 0), (0, 0), 0.5, GRIS_BORD),
                    ("LINEABOVE", (1, 0), (1, 0), 0.5, GRIS_BORD),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                ]
            ),
        ),
        Spacer(1, HAUTEUR_CACHET),
    ]


def _pied_de_page(canvas, doc) -> None:
    """Le pied : la mention « projete a signer », page sur nombre.

    Le bulletin sort de l'imprimante pour etre signe. Le dire en bas de chaque
    page evite qu'une page detachee soit prise pour un extrait officiel — et
    rappelle que le document n'est pas encore signe quand il sort.
    """

    canvas.saveState()
    canvas.setFont(_police_disponible(), 7)
    canvas.setFillColor(GRIS_TEXTE)
    canvas.drawString(
        MARGE, 10 * mm,
        "Bulletin provisoire — à signer et à cacheter par l'établissement.",
    )
    canvas.drawRightString(A4[0] - MARGE, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def composer_bulletin_pdf(bulletin: Bulletin) -> List[Any]:
    """Construit les flowables du bulletin. Aucune donnee n'y est decidee."""

    styles = _styles(_police_disponible())
    largeur_utile = A4[0] - 36 * mm

    corps: List[Any] = []

    # -- L'etablissement -------------------------------------------------
    corps.append(Paragraph(bulletin.etablissement_nom, styles["etablissement"]))
    if bulletin.etablissement_sigle:
        corps.append(Paragraph(bulletin.etablissement_sigle, styles["etablissement_meta"]))
    contact = ", ".join(
        partie for partie in (
            bulletin.etablissement_adresse,
            bulletin.etablissement_telephone,
            bulletin.etablissement_email,
            bulletin.etablissement_pays,
        ) if partie
    )
    if contact:
        corps.append(Paragraph(contact, styles["etablissement_meta"]))

    # -- Le titre et la periode -----------------------------------------
    corps.append(Paragraph("BULLETIN DE NOTES", styles["titre"]))
    periode = " · ".join(
        partie for partie in (
            bulletin.semestre_libelle,
            f"Année {bulletin.session_annee}" if bulletin.session_annee else None,
            bulletin.session_nom,
        ) if partie
    )
    corps.append(Paragraph(periode, styles["sous_titre"]))

    # -- L'etudiant ------------------------------------------------------
    # Le bloc tient sur deux colonnes de paires. Un nombre impair de champs
    # laisse une case vide : elle est **remplie explicitement**, pas supprimee.
    # Tronquer en silence ferait disparaitre une donnee du document officiel,
    # et personne ne verrait qu'elle y etait.
    identite = [
        ("Nom et prénom", " ".join(
            p for p in (bulletin.etudiant_nom, bulletin.etudiant_prenom) if p
        ) or VALEUR_ABSENTE),
        ("Matricule", bulletin.matricule or VALEUR_ABSENTE),
        ("Filière", bulletin.filiere or VALEUR_ABSENTE),
        ("Niveau", bulletin.niveau or VALEUR_ABSENTE),
        ("Classe", bulletin.classe or VALEUR_ABSENTE),
    ]
    if len(identite) % 2:
        identite.append(("", ""))

    corps.append(
        Table(
            [
                [
                    Paragraph(f"<b>{gauche[0]}</b>" if gauche[0] else "", styles["cellule"]),
                    Paragraph(gauche[1], styles["cellule"]),
                    Paragraph(f"<b>{droite[0]}</b>" if droite[0] else "", styles["cellule"]),
                    Paragraph(droite[1], styles["cellule"]),
                ]
                for gauche, droite in zip(identite[::2], identite[1::2])
            ],
            colWidths=_largeurs(28, 62, 28, 62),
            style=TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.4, GRIS_BORD),
                    ("BACKGROUND", (0, 0), (0, -1), GRIS_CLAIR),
                    ("BACKGROUND", (2, 0), (2, -1), GRIS_CLAIR),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            ),
        )
    )

    corps.append(Spacer(1, 4 * mm))

    # -- Le tableau des notes -------------------------------------------
    if bulletin.blocs:
        corps.append(_tableau_notes(styles, bulletin))
        corps.append(Spacer(1, 3 * mm))
        corps.append(_tableau_totaux(styles, bulletin))
    else:
        # Aucune UE notee : le bulletin le dit plutot que d'imprimer un
        # tableau vide, qui se lirait comme un semestre sans matieres.
        corps.append(
            Paragraph(
                "Aucune unité d'enseignement notée sur ce semestre.",
                styles["mention"],
            )
        )

    # -- Le recapitulatif annuel ---------------------------------------
    recapitulatif = _tableau_recapitulatif(styles, bulletin)
    if recapitulatif is not None:
        corps.append(Paragraph("Récapitulatif de l'année", styles["section"]))
        corps.append(recapitulatif)

    # -- Ce que le tableau ne montre pas --------------------------------
    reserves = _bloc_reserves(bulletin)
    if reserves:
        corps.extend(_encadre_reserves(styles, reserves, "Observations"))

    corps.extend(_bloc_signature(styles, bulletin))

    return corps


def rendre_bulletin(bulletin: Bulletin) -> Tuple[bytes, str]:
    """Rend le bulletin et retourne ``(octets, nom_fichier)``."""

    tampon = io.BytesIO()
    document = SimpleDocTemplate(
        tampon,
        pagesize=A4,
        leftMargin=MARGE,
        rightMargin=MARGE,
        topMargin=14 * mm,
        bottomMargin=18 * mm,
        title=f"Bulletin {bulletin.semestre_libelle} — "
              f"{bulletin.etudiant_nom} {bulletin.etudiant_prenom}".strip(),
        author=bulletin.etablissement_nom,
    )
    document.build(composer_bulletin_pdf(bulletin), onFirstPage=_pied_de_page,
                   onLaterPages=_pied_de_page)

    nom = "_".join(
        partie for partie in (
            "bulletin",
            bulletin.semestre_libelle or f"s{bulletin.semestre_numero}",
            bulletin.matricule,
            bulletin.etudiant_nom,
            bulletin.etudiant_prenom,
        ) if partie
    ).replace(" ", "-").lower() + ".pdf"

    return tampon.getvalue(), nom


# ---------------------------------------------------------------------------
# Assemblage : ce que l'appelant doit fournir
# ---------------------------------------------------------------------------
async def rendre_bulletin_pour(
    db,
    *,
    etudiant,
    semestre,
    etablissement,
    session,
    decision=None,
) -> Tuple[bytes, str]:
    """Rend le bulletin d'un etudiant pour un semestre.

    Cette fonction fait l'assemblage — elle lit la base, appelle le service de
    moyennes, puis la mise en page. Elle ne **calcule** rien : les moyennes
    viennent de ``semestre_service``, les mentions de la deliberation ou du
    bareme confirme, et le contenu de ``bulletin_service``.

    Un point a savoir, et qui n'est pas un oubli : **la decision du jury
    n'existe pas encore par UE.** La deliberation persiste un statut, une
    mention et des ECTS acquis **par etudiant**, pas par unite
    d'enseignement. Le bulletin imprime donc ce qui existe — la decision
    globale, dans le bloc des totaux — et ne sort pas de « validee en
    rattrapage » pour une UE, parce que personne ne l'a enregistree. Les trois
    etats par UE (validee, validee en rattrapage, a reprendre) sont la piece
    suivante : c'est ce qui manquera au flux de rattrapage, et ce qui doit
    etre persiste avant d'etre imprime.
    """

    from app.services.bulletin_service import composer_bulletin
    from app.services.deliberation_service import BAREME_REPLI
    from app.services.semestre_service import bilan_semestre, recap_annuel

    # Un etat vide de deliberation n'est pas « pas de decision » : c'est
    # « aucune deliberation enregistree », et le bulletin le dit.
    if decision is not None:
        decisions = {
            identifiant: {
                "validation": entree.get("validation"),
                "credits_obtenus": entree.get("credits_obtenus"),
                "mention": entree.get("mention"),
            }
            for identifiant, entree in (getattr(decision, "moyennes_ue", None) or {}).items()
            if isinstance(entree, dict) and entree.get("validation")
        }
    else:
        decisions = {}

    bilan = await bilan_semestre(
        db,
        etudiant_id=etudiant.id,
        session_id=semestre.session_id,
        semestre_id=semestre.id,
        decisions=decisions,
    )
    recap = await recap_annuel(
        db,
        etudiant_id=etudiant.id,
        session_id=semestre.session_id,
        semestre_id=semestre.id,
        decisions=decisions,
    )

    # Le bareme vient de la deliberation confirmee quand elle existe, sinon du
    # repli — jamais d'une liste ecrite ici.
    bareme: List[Dict[str, Any]] = list(BAREME_REPLI["bareme_mentions"])
    if decision is not None:
        regles = getattr(decision, "regles", None) or {}
        if regles.get("bareme_mentions"):
            bareme = list(regles["bareme_mentions"])

    bulletin = composer_bulletin(
        bilan,
        infos={
            "etablissement": {
                "nom": getattr(etablissement, "nom", None),
                "sigle": getattr(etablissement, "sigle", None),
                "adresse": getattr(etablissement, "adresse", None),
                "telephone": getattr(etablissement, "telephone", None),
                "email": getattr(etablissement, "email", None),
                "pays": getattr(etablissement, "pays", None),
                "logo_url": getattr(etablissement, "logo_url", None),
            },
            "etudiant": {
                "nom": getattr(etudiant, "nom", None),
                "prenom": getattr(etudiant, "prenom", None),
                "matricule": getattr(etudiant, "matricule", None),
                "filiere": getattr(etudiant, "filiere", None),
                "niveau": getattr(etudiant, "niveau", None),
                "classe": getattr(getattr(etudiant, "classe", None), "nom", None),
                "date_naissance": getattr(etudiant, "date_naissance", None),
            },
            "session": {
                "nom": getattr(session, "nom", None),
                "annee_academique": getattr(session, "annee_academique", None),
            },
            "bareme_mentions": bareme,
        },
        recap=recap,
    )

    if decision is None:
        bulletin.deliberation_absente = True

    return rendre_bulletin(bulletin)


__all__ = ["composer_bulletin_pdf", "rendre_bulletin", "rendre_bulletin_pour"]
