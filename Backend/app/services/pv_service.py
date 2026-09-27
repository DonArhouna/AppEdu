"""
Proces-verbal de jury.

Le PV est le document qui **prouve** qu'un jury s'est tenu. Deux exigences
non negociables :

1. Il ne porte que des **decisions consignees**. Les propositions du moteur
   n'y apparaissent que comme comparaison, dans une colonne separee, et
   seulement lorsqu'elles divergent. Un PV qui presenterait une proposition
   comme un verdict attesterait d'une decision que le jury n'a pas prise.

2. Il porte les **regles appliquees**, figees dans la seance. Un PV qui ne
   dirait pas sur quelle base le jury a statue ne prouverait rien : dix ans
   plus tard, on ne saurait pas si l'admission a 10/20 etait la regle du jour
   ou une coincidence.

Rendu : ReportLab, comme les autres documents officiels, avec l'en-tete
d'etablissement et donc le logo.
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
        TableStyle,
)

from app.models.deliberation import Deliberation, DeliberationDecision
from app.models.etablissement import Etablissement
from app.services.document_service import infos_etablissement
from app.services.pdf_service import (
    ACCENT,
    GRIS_BORD,
    GRIS_CLAIR,
    VALEUR_ABSENTE,
    _entete_etablissement,
    _pied,
    _police_disponible,
    _styles,
    texte_ou_valeur,
)

TITRE = "Procès-verbal de jury"


async def rendre_proces_verbal(
    db,
    *,
    seance: Deliberation,
    etablissement: Optional[Etablissement],
    decisions: List[DeliberationDecision],
) -> Tuple[bytes, str]:
    """Rend le PV et retourne ``(octets, nom_fichier)``."""

    infos = infos_etablissement(etablissement) if etablissement is not None else {}
    police = _police_disponible()
    styles = _styles(police)

    corps: List[Any] = []

    # ------------------------------------------------------------------
    # 1. Promotion et seance
    # ------------------------------------------------------------------
    corps.append(Paragraph("Promotion et séance", styles["section"]))
    details = [
        ("Promotion", seance.classe.nom if seance.classe else None),
        ("Filière", seance.classe.filiere.nom if seance.classe and seance.classe.filiere else None),
        ("Niveau", seance.classe.niveau.nom if seance.classe and seance.classe.niveau else None),
        ("Session", seance.session.nom if seance.session else None),
        ("Année académique", seance.session.annee_academique if seance.session else None),
        ("Date de la séance", seance.date_deliberation.strftime("%d/%m/%Y")),
        ("Lieu", seance.lieu),
    ]
    corps.append(
        _tableau_paires(
            styles,
            [(libelle, valeur) for libelle, valeur in details if valeur],
        )
    )

    # ------------------------------------------------------------------
    # 2. Composition du jury — saisie, jamais devinee
    # ------------------------------------------------------------------
    corps.append(Paragraph("Composition du jury", styles["section"]))
    jury = [("Président", seance.president)]
    for membre in seance.membres or []:
        nom = str(membre.get("nom") or "").strip()
        qualite = str(membre.get("qualite") or "").strip()
        jury.append(("Membre", f"{nom} — {qualite}" if qualite else nom))
    corps.append(_tableau_paires(styles, jury))

    # ------------------------------------------------------------------
    # 3. Regles appliquees
    # ------------------------------------------------------------------
    regles = dict(seance.regles or {})
    corps.append(Paragraph("Règles appliquées", styles["section"]))
    bareme = regles.get("bareme_mentions") or []
    bareme_texte = ", ".join(
        f"{entree.get('libelle')} à partir de {entree.get('seuil_min')}/20"
        for entree in sorted(
            bareme, key=lambda e: float(e.get("seuil_min", 0)), reverse=True
        )
    )
    mention_regles = (
        "Règlement confirmé par l'établissement."
        if regles.get("confirmee")
        else "Règlement issu des valeurs par défaut, non confirmé par l'établissement."
    )
    corps.append(
        _tableau_paires(
            styles,
            [
                ("Moyenne de validation", f"{regles.get('seuil_validation_moyenne')}/20"),
                ("Moyenne minimale de rattrapage", f"{regles.get('seuil_rattrapage_minimale')}/20"),
                ("Note éliminatoire", f"en dessous de {regles.get('seuil_eliminatoire')}/20"),
                (
                    "Passage conditionnel",
                    f"{regles.get('seuil_passage_conditionnel_ects')} ECTS acquis",
                ),
                (
                    "Compensation entre UE",
                    "autorisée" if regles.get("compensation_autorisee") else "non autorisée",
                ),
                ("Mentions", bareme_texte or VALEUR_ABSENTE),
                ("Statut du règlement", mention_regles),
            ],
        )
    )
    if not regles.get("confirmee"):
        corps.append(
            Paragraph(
                "Attention : ce procès-verbal a été produit avec un règlement "
                "non validé par l'établissement. Les seuils appliqués doivent "
                "être confirmés.",
                styles["mention"],
            )
        )

    # ------------------------------------------------------------------
    # 4. Decisions du jury
    # ------------------------------------------------------------------
    corps.append(Paragraph("Décisions du jury", styles["section"]))
    corps.append(
        Paragraph(
            "Les décisions ci-dessous sont celles consignées en séance. La "
            "colonne « écart » signale les cas où le jury s'est écarté de la "
            "proposition du moteur, avec le motif de cet écart.",
            styles["mention"],
        )
    )
    # Le tableau s'ajoute tel quel : un ``Paragraph`` attend du texte, et
    # lui passer un tableau echoue au moment du rendu.
    corps.append(_tableau_decisions(styles, decisions))

    # ------------------------------------------------------------------
    # 5. Ecarts motives
    # ------------------------------------------------------------------
    ecarts = [d for d in decisions if d.ecart_proposition]
    if ecarts:
        corps.append(Paragraph("Écarts et motifs", styles["section"]))
        corps.append(
            Paragraph(
                "Le jury s'est écarté de la proposition du moteur pour les "
                "étudiants suivants. Ces écarts sont motivés : une décision "
                "non motivée ne serait pas justifiable.",
                styles["mention"],
            )
        )
        lignes = []
        for decision in ecarts:
            identite = _identite(decision)
            lignes.append(
                [
                    Paragraph(identite, styles["cellule"]),
                    Paragraph(
                        f"Proposition : {decision.proposition_statut}"
                        + (
                            f" / {decision.proposition_mention}"
                            if decision.proposition_mention
                            else ""
                        ),
                        styles["cellule"],
                    ),
                    Paragraph(
                        f"Décision : {decision.statut}"
                        + (f" / {decision.mention}" if decision.mention else ""),
                        styles["cellule"],
                    ),
                    Paragraph(
                        texte_ou_valeur(decision.motif_ecart), styles["cellule"]
                    ),
                ]
            )
        corps.append(Table(lignes, colWidths=[38 * mm, 32 * mm, 32 * mm, 72 * mm], repeatRows=1))
        corps.append(
            Table(
                [[Paragraph("", styles["cellule"])]],
                colWidths=[38 * mm, 32 * mm, 32 * mm, 72 * mm],
                style=TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, GRIS_BORD)]),
            )
        )

    # ------------------------------------------------------------------
    # 6. Statistiques de la seance
    # ------------------------------------------------------------------
    corps.append(Paragraph("Bilan de la séance", styles["section"]))
    corps.append(
        _tableau_paires(
            styles,
            [
                ("Effectif délibéré", f"{len(decisions)} étudiant(s)"),
                ("Admis", f"{_compter(decisions, 'Admis')}"),
                ("Rattrapage", f"{_compter(decisions, 'Rattrapage')}"),
                ("Ajourné", f"{_compter(decisions, 'Ajourné')}"),
                ("Écarts par rapport à la proposition", f"{len(ecarts)}"),
            ],
        )
    )

    # ------------------------------------------------------------------
    # 7. Mentions finales
    # ------------------------------------------------------------------
    corps.append(Spacer(1, 4 * mm))
    corps.append(
        Paragraph(
            "Le présent procès-verbal arrête les décisions du jury. Il ne peut "
            "plus être modifié. Toute décision d'attestation de réussite s'y "
            "appuie exclusivement.",
            styles["mention"],
        )
    )
    corps.append(_bloc_signatures(styles, seance))

    # ------------------------------------------------------------------
    # Assemblage
    # ------------------------------------------------------------------
    sous_titre = "Décisions arrêtées par le jury"
    if seance.close:
        sous_titre += f" — séance close le {seance.close_le.strftime('%d/%m/%Y') if seance.close_le else '—'}"
    corps.insert(0, Paragraph(sous_titre, styles["sous_titre"]))

    tampon = io.BytesIO()
    doc = BaseDocTemplate(
        tampon,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=13 * mm,
        bottomMargin=22 * mm,
        title=f"{TITRE} — {infos.get('nom') or 'EduManagePro'}",
        author=str(infos.get("nom") or "EduManagePro"),
        subject="Procès-verbal de délibération",
    )
    reference = f"PV-{seance.date_deliberation.strftime('%Y%m%d')}-{seance.id[:8]}"
    doc.addPageTemplates(
        [
            PageTemplate(
                id="pv",
                frames=[
                    Frame(
                        doc.leftMargin,
                        doc.bottomMargin,
                        width=doc.width,
                        height=doc.height,
                        id="corps",
                    )
                ],
                onPage=lambda canvas, document: _pied(canvas, reference, infos, police),
            )
        ]
    )
    doc.build(
        [
            *_entete_etablissement(styles, infos),
            Paragraph(TITRE, styles["titre"]),
            corps[0],
            *corps[1:],
        ]
    )

    nom = f"PV_{seance.date_deliberation.isoformat()}_{seance.id[:8]}.pdf"
    return tampon.getvalue(), nom


# ---------------------------------------------------------------------------
# Blocs de mise en page
# ---------------------------------------------------------------------------
def _identite(decision: DeliberationDecision) -> str:
    etudiant = decision.etudiant
    if etudiant is None:
        return VALEUR_ABSENTE
    nom = f"{etudiant.nom} {etudiant.prenom}".strip()
    return f"{etudiant.matricule} — {nom}" if nom else str(etudiant.matricule)


def _compter(decisions: List[DeliberationDecision], statut: str) -> int:
    return sum(1 for decision in decisions if decision.statut == statut)


def _tableau_paires(styles, lignes: List[Tuple[str, Any]]) -> Table:
    donnees = [
        [Paragraph(str(libelle), styles["cellule"]), Paragraph(texte_ou_valeur(valeur), styles["cellule"])]
        for libelle, valeur in lignes
    ]
    tableau = Table(donnees, colWidths=[55 * mm, 119 * mm], hAlign="LEFT")
    tableau.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("BACKGROUND", (0, 0), (0, -1), GRIS_CLAIR),
                ("LINEBELOW", (0, 0), (-1, -2), 0.25, GRIS_BORD),
            ]
        )
    )
    return tableau


def _tableau_decisions(styles, decisions: List[DeliberationDecision]) -> Table:
    entetes = [
        Paragraph("Matricule", styles["cellule_entete"]),
        Paragraph("Nom et prénom", styles["cellule_entete"]),
        Paragraph("Moyenne", styles["cellule_entete"]),
        Paragraph("ECTS", styles["cellule_entete"]),
        Paragraph("Décision du jury", styles["cellule_entete"]),
        Paragraph("Écart", styles["cellule_entete"]),
    ]
    donnees: List[List[Any]] = [entetes]
    for decision in sorted(
        decisions, key=lambda d: str(d.etudiant.matricule if d.etudiant else "")
    ):
        etudiant = decision.etudiant
        nom = f"{etudiant.nom} {etudiant.prenom}".strip() if etudiant else VALEUR_ABSENTE
        matricule = etudiant.matricule if etudiant else VALEUR_ABSENTE
        mention = f" / {decision.mention}" if decision.mention else ""
        donnees.append(
            [
                Paragraph(str(matricule), styles["cellule"]),
                Paragraph(nom, styles["cellule"]),
                Paragraph(f"{decision.moyenne_generale:g}/20", styles["cellule"]),
                Paragraph(
                    f"{decision.ects_acquis}/{decision.ects_total}", styles["cellule"]
                ),
                Paragraph(f"{decision.statut}{mention}", styles["cellule"]),
                Paragraph("oui" if decision.ecart_proposition else "—", styles["cellule"]),
            ]
        )

    tableau = Table(
        donnees,
        colWidths=[22 * mm, 46 * mm, 18 * mm, 18 * mm, 40 * mm, 14 * mm],
        repeatRows=1,
    )
    tableau.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.25, GRIS_BORD),
                # Les lignes en ecart ressortent : elles demandent une
                # explication, et le lecteur doit la voir immediatement.
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFBFC")]),
            ]
        )
    )
    return tableau


def _bloc_signatures(styles, seance: Deliberation) -> KeepTogether:
    return KeepTogether(
        [
            Spacer(1, 6 * mm),
            Table(
                [
                    [
                        Paragraph("Le président de jury", styles["cellule"]),
                        Paragraph("Le doyen / secrétaire", styles["cellule"]),
                    ],
                    [
                        Paragraph(str(seance.president), styles["cellule"]),
                        Paragraph("", styles["cellule"]),
                    ],
                    [Paragraph("", styles["cellule"]), Paragraph("", styles["cellule"])],
                    [
                        Paragraph("Signature et date", styles["mention"]),
                        Paragraph("Signature et date", styles["mention"]),
                    ],
                ],
                colWidths=[87 * mm, 87 * mm],
                style=TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                ),
            ),
        ]
    )


__all__ = ["TITRE", "rendre_proces_verbal"]
