"""
Rendu PDF des documents officiels (ReportLab).

Choix techniques :

- **Polices** : on tente d'enregistrer une TrueType du systeme (meilleure
  couverture Unicode, rendu plus proche d'un document word).  En repli, les
  polices standard ReportLab, qui couvrent le Latin-1 et donc le francais.
  Aucun document n'est refuse pour un accent.
- **Aucune invention** : une donnee absente s'affiche explicitement
  (« Non renseigne ») ou la ligne est omise et signalee en reserve.  Le
  service ne comble jamais un trou par une valeur plausible.
- **Pas de moteur de gabarit externe** : la mise en page vit ici, en Python.
  Jinja + WeasyPrint serait plus souple mais ajouterait deux dependances et
  une couche de rendu pour un gain nul a ce stade.
"""

from __future__ import annotations

import io
import logging
import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from app.core.document_types import CODE_CERTIFICAT, CODE_QUITUS, CODE_RELEVE
from app.services import branding_service

#: Garde-fous du logo. Un logo trop grand ecraserait le titre du document ;
#: un logo minuscule serait illisible a l'impression.
LOGO_HAUTEUR_MAX_MM = 24
LOGO_LARGEUR_MAX_MM = 60

logger = logging.getLogger(__name__)

#: Palette sobre, lisible a l'impression comme a l'ecran.
ENCRE = colors.HexColor("#1A1A1A")
ACCENT = colors.HexColor("#0F4C81")
GRIS_CLAIR = colors.HexColor("#F2F4F7")
GRIS_BORD = colors.HexColor("#9AA4B2")
GRIS_TEXTE = colors.HexColor("#5A6472")

VALEUR_ABSENTE = "Non renseigné"

#: Fichiers TrueType testes dans l'ordre ; le premier lisible est utilise.
_POLICES_CANDIDATES = (
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
)

_police_enregistree: Optional[str] = None


def _police_disponible() -> str:
    """Enregistre une police systeme si possible, sinon utilise Helvetica."""

    global _police_enregistree
    if _police_enregistree:
        return _police_enregistree

    for chemin in _POLICES_CANDIDATES:
        if not os.path.isfile(chemin):
            continue
        try:
            pdfmetrics.registerFont(TTFont("EmpDoc", chemin))
        except Exception:  # pragma: no cover - police illisible ou incompatible
            continue
        _police_enregistree = "EmpDoc"
        return _police_enregistree

    _police_enregistree = "Helvetica"
    return _police_enregistree


def texte_ou_valeur(valeur: Any) -> str:
    """Formate une valeur pour le PDF, sans jamais inventer de contenu."""

    if valeur is None:
        return VALEUR_ABSENTE
    if isinstance(valeur, bool):
        return "Oui" if valeur else "Non"
    if isinstance(valeur, (date, datetime)):
        return valeur.strftime("%d/%m/%Y")
    if isinstance(valeur, float):
        return f"{valeur:,.2f}".replace(",", " ").replace(".", ",")
    texte = str(valeur).strip()
    return texte or VALEUR_ABSENTE


def montant(valeur: Optional[float], devise: str = "") -> str:
    """Formate un montant avec la devise de l'etablissement."""

    if valeur is None:
        return VALEUR_ABSENTE
    formate = f"{valeur:,.2f}".replace(",", " ").replace(".", ",")
    return f"{formate} {devise}".strip()


def _styles(police: str) -> Dict[str, ParagraphStyle]:
    """Styles du document.

    Un style de base porte la police et la couleur de fond du texte.  Chaque
    style enfant surcharge uniquement ce qu'il change : pas de dictionnaire
    eclat, donc aucune possibility de collision de cle.
    """

    base = getSampleStyleSheet()["Normal"]
    base_emp = ParagraphStyle(
        "baseEmp", parent=base, fontName=police, textColor=ENCRE,
    )

    return {
        "titre": ParagraphStyle(
            "titre", parent=base_emp, fontSize=16, leading=21,
            textColor=ACCENT, alignment=TA_CENTER, spaceAfter=2,
        ),
        "sous_titre": ParagraphStyle(
            "sous_titre", parent=base_emp, fontSize=9, leading=12,
            textColor=GRIS_TEXTE, alignment=TA_CENTER, spaceAfter=9,
        ),
        "etablissement": ParagraphStyle(
            "etablissement", parent=base_emp, fontSize=13, leading=16,
            alignment=TA_CENTER, spaceAfter=1,
        ),
        "etablissement_meta": ParagraphStyle(
            "etablissement_meta", parent=base_emp, fontSize=7.5, leading=10,
            textColor=GRIS_TEXTE, alignment=TA_CENTER,
        ),
        "section": ParagraphStyle(
            "section", parent=base_emp, fontSize=10, leading=13,
            textColor=ACCENT, spaceBefore=9, spaceAfter=3,
        ),
        "corps": ParagraphStyle(
            "corps", parent=base_emp, fontSize=9.5, leading=15,
            alignment=TA_JUSTIFY, spaceAfter=5,
        ),
        "mention": ParagraphStyle(
            "mention", parent=base_emp, fontSize=8, leading=11,
            textColor=GRIS_TEXTE, spaceAfter=3,
        ),
        "puce": ParagraphStyle(
            "puce", parent=base_emp, fontSize=9, leading=13, leftIndent=6,
        ),
        "cellule": ParagraphStyle(
            "cellule", parent=base_emp, fontSize=8, leading=10.5,
        ),
        "cellule_droite": ParagraphStyle(
            "cellule_droite", parent=base_emp, fontSize=8, leading=10.5,
            alignment=TA_RIGHT,
        ),
        "cellule_entete": ParagraphStyle(
            "cellule_entete", parent=base_emp, fontSize=8, leading=10.5,
            textColor=colors.white,
        ),
        "signature": ParagraphStyle(
            "signature", parent=base_emp, fontSize=8.5, leading=11,
            alignment=TA_CENTER, textColor=GRIS_TEXTE,
        ),
    }


# ---------------------------------------------------------------------------
# Blocs reutilisables
# ---------------------------------------------------------------------------
def _logo_etablissement(chemin_relatif: Optional[str]) -> Optional[Image]:
    """Construit le flowable du logo, ou ``None`` s'il n'est pas exploitable.

    L'echec est silencieux pour l'appelant : un logo deplace ou corrompu ne
    doit pas empecher l'emission d'un certificat. Le motif est journalise pour
    que l'incident reste visible.
    """

    if not chemin_relatif:
        return None

    lu = branding_service.lire_logo(chemin_relatif)
    if lu is None:
        logger.warning("Logo introuvable pour l'en-tete : %s", chemin_relatif)
        return None

    contenu, _type_mime = lu
    try:
        lecteur = ImageReader(io.BytesIO(contenu))
        largeur_px, hauteur_px = lecteur.getSize()
    except Exception as exc:  # pragma: no cover - depend du contenu du fichier
        logger.warning("Logo illisible (%s) : %s", chemin_relatif, exc)
        return None

    if not largeur_px or not hauteur_px:
        return None

    # Facteur d'echelle borne : on preserve le rapport d'aspect du logo et on
    # interdit qu'il depasse la zone reservee en tete.
    facteur = min(
        (LOGO_LARGEUR_MAX_MM * mm) / largeur_px,
        (LOGO_HAUTEUR_MAX_MM * mm) / hauteur_px,
    )
    return Image(
        io.BytesIO(contenu),
        width=largeur_px * facteur,
        height=hauteur_px * facteur,
        hAlign="CENTER",
    )


def _entete_etablissement(styles, etablissement: Dict[str, Any]) -> List[Any]:
    elements: List[Any] = [Spacer(1, 3 * mm)]
    logo = _logo_etablissement(etablissement.get("logo_url"))
    if logo is not None:
        elements.append(logo)
        elements.append(Spacer(1, 2 * mm))
    elements.append(
        Paragraph(texte_ou_valeur(etablissement.get("nom")), styles["etablissement"])
    )
    details = [
        str(etablissement.get(cle))
        for cle in ("adresse", "telephone", "email")
        if etablissement.get(cle)
    ]
    if details:
        elements.append(Paragraph(" · ".join(details), styles["etablissement_meta"]))
    if etablissement.get("sigle"):
        elements.append(Paragraph(str(etablissement["sigle"]), styles["etablissement_meta"]))
    elements.append(Spacer(1, 3 * mm))
    return elements


def _bloc_identite(styles, etudiant, champs: Optional[Sequence[tuple]] = None) -> Table:
    """Tableau « libelle / valeur » pour l'identite de l'etudiant."""

    lignes = champs or [
        ("Matricule", etudiant.matricule),
        ("Nom et prénom", f"{etudiant.nom} {etudiant.prenom}".strip()),
        ("Date de naissance", etudiant.date_naissance),
        ("Filière", etudiant.filiere),
        ("Niveau", etudiant.niveau),
    ]
    donnees = [
        [
            Paragraph(str(libelle), styles["cellule"]),
            Paragraph(texte_ou_valeur(valeur), styles["cellule"]),
        ]
        for libelle, valeur in lignes
    ]
    tableau = Table(donnees, colWidths=[50 * mm, 110 * mm], hAlign="LEFT")
    tableau.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("BACKGROUND", (0, 0), (0, -1), GRIS_CLAIR),
            ]
        )
    )
    return tableau


def _tableau(
    styles,
    entetes: Sequence[str],
    lignes: Sequence[Sequence[Any]],
    largeurs: Optional[Sequence[float]] = None,
    alignements: Optional[Sequence[str]] = None,
    vide: str = "Aucune donnée disponible pour cette période.",
) -> Table:
    """Tableau de donnees avec en-tete colore et lignes alternees."""

    style_par_colonne = {"g": styles["cellule"], "d": styles["cellule_droite"]}
    entete = [Paragraph(texte, styles["cellule_entete"]) for texte in entetes]
    if lignes:
        corps = [
            [
                Paragraph(
                    texte_ou_valeur(valeur),
                    style_par_colonne[(alignements[index] if alignements else "g")],
                )
                for index, valeur in enumerate(ligne)
            ]
            for ligne in lignes
        ]
    else:
        corps = [[Paragraph(vide, styles["mention"])] + [Paragraph("", styles["cellule"])] * (len(entetes) - 1)]

    tableau = Table(
        [entete, *corps], colWidths=list(largeurs) if largeurs else None,
        repeatRows=1, hAlign="LEFT",
    )
    tableau.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("GRID", (0, 0), (-1, -1), 0.3, GRIS_BORD),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS_CLAIR]),
            ]
        )
    )
    return tableau


def _puces(styles, valeurs: Sequence[str]) -> Paragraph:
    return Paragraph(
        "".join(f"• {texte_ou_valeur(valeur)}<br/>" for valeur in valeurs),
        styles["puce"],
    )


def _encadre_etat(styles, texte: str, favorable: bool) -> Table:
    """Encadre la conclusion du document (quitus)."""

    couleur = colors.HexColor("#E8F3EA") if favorable else colors.HexColor("#FBECEC")
    tableau = Table([[Paragraph(texte, styles["corps"])]], colWidths=[160 * mm])
    tableau.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), couleur),
                ("BOX", (0, 0), (-1, -1), 0.6, GRIS_BORD),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return tableau


def _bloc_reserves(styles, reserves: Sequence[str]) -> List[Any]:
    elements: List[Any] = []
    liste = [str(item) for item in reserves if str(item).strip()]
    if not liste:
        return elements
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph("Réserves du document", styles["section"]))
    elements.append(
        Paragraph(
            "Les éléments suivants n'ont pas pu être documentés au moment de "
            "l'émission :<br/>" + "<br/>".join(f"• {item}" for item in liste),
            styles["mention"],
        )
    )
    return elements


def _bloc_signature(styles, fonction: str) -> List[Any]:
    """Signature : reserve a l'etablissement, jamais pre-remplie."""

    return [
        Spacer(1, 9 * mm),
        Table(
            [[Paragraph("", styles["signature"]), Paragraph(fonction, styles["signature"])]],
            colWidths=[95 * mm, 65 * mm],
            style=TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEABOVE", (1, 0), (1, 0), 0.5, GRIS_BORD),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ]
            ),
        ),
    ]


# ---------------------------------------------------------------------------
# Rendu par type
# ---------------------------------------------------------------------------
def _rendre_certificat(styles, contexte: Dict[str, Any]) -> tuple:
    etablissement = contexte["etablissement"]
    inscription = contexte["inscription"]
    session = inscription.session if inscription is not None else None

    corps: List[Any] = [
        _bloc_identite(
            styles, contexte["etudiant"],
            champs=[
                ("Matricule", contexte["etudiant"].matricule),
                ("Nom et prénom", f"{contexte['etudiant'].nom} {contexte['etudiant'].prenom}".strip()),
                ("Date de naissance", contexte["etudiant"].date_naissance),
                ("Filière", contexte["etudiant"].filiere),
                ("Niveau", contexte["etudiant"].niveau),
                # ``Classe`` n'a pas de colonne ``code`` : le code d'affichage
                # est derive de la filiere et du niveau. On affiche donc le
                # nom enregistre, avec l'identifiant en repli.
                (
                    "Classe",
                    (
                        inscription.classe.nom or inscription.classe.id
                        if inscription is not None and inscription.classe is not None
                        else None
                    ),
                ),
                ("Session", f"{session.nom} ({session.code})" if session is not None else None),
            ],
        ),
        Paragraph("Énoncé", styles["section"]),
        Paragraph(
            "Je soussigné, autorité de l'établissement "
            f"<b>{texte_ou_valeur(etablissement.get('nom'))}</b>, certifie que "
            "l'étudiant dont l'identité précède est régulièrement inscrit et "
            "fréquente les cours de cet établissement pour l'année académique "
            "indiquée ci-dessus.",
            styles["corps"],
        ),
        Spacer(1, 2 * mm),
        Paragraph(
            "Le présent certificat est délivré pour servir et valoir ce que de "
            "droit. Il ne préjuge pas des résultats académiques, qui font "
            "l'objet d'un relevé de notes distinct.",
            styles["corps"],
        ),
    ]
    mention = (
        "Document émis à partir des données d'inscription enregistrées dans le "
        "système de gestion de l'établissement. Toute altération du contenu "
        "engage la responsabilité de son détenteur."
    )
    sous_titre = (
        f"Année académique {session.annee_academique or session.nom}"
        if session is not None
        else "Année académique en cours"
    )
    return "Certificat de scolarité", sous_titre, corps, mention, "Le Directeur des études"


def _rendre_releve(styles, contexte: Dict[str, Any]) -> tuple:
    notes = contexte["notes"]
    moyenne = contexte["moyenne"]
    devise = contexte["etablissement"].get("devise") or ""
    reserves: List[str] = []
    if not notes:
        reserves.append("Aucune note enregistrée sur la session demandée.")
    elif moyenne is None:
        reserves.append("Moyenne générale non calculable : coefficients absents.")

    lignes = [
        [
            note["ue"] or "—",
            note["matiere"],
            note["detail"],
            texte_ou_valeur(note["coefficient"]),
            texte_ou_valeur(note["moyenne"]),
        ]
        for note in notes
    ]

    corps: List[Any] = [
        _bloc_identite(styles, contexte["etudiant"]),
        Paragraph("Notes par matière", styles["section"]),
        _tableau(
            styles,
            ["Unité d'enseignement", "Matière", "Notes", "Coef.", "Moyenne"],
            lignes,
            largeurs=[38 * mm, 42 * mm, 44 * mm, 14 * mm, 18 * mm],
            alignements=["g", "g", "g", "d", "d"],
            vide="Aucune note n'est enregistrée pour cette session.",
        ),
        Spacer(1, 3 * mm),
        _tableau(
            styles,
            ["Moyenne générale pondérée", "Échelle"],
            [[texte_ou_valeur(moyenne), "sur 20"]],
            largeurs=[110 * mm, 46 * mm],
            alignements=["d", "g"],
        ),
        Spacer(1, 2 * mm),
        Paragraph(
            "Les moyennes sont pondérées par le coefficient de chaque évaluation. "
            "Les matières sans note ne figurent pas dans le tableau : aucune note "
            "n'est supposée nulle. Ce relevé ne constitue pas une décision de "
            "délibération.",
            styles["mention"],
        ),
    ]
    mention = (
        "Relevé établi à partir des notes saisies et validées dans le système. "
        "Cours et devise de l'établissement : "
        f"{texte_ou_valeur(contexte['etudiant'].filiere)} / {devise}."
    )
    session = contexte.get("session")
    sous_titre = (
        f"Année {session.annee_academique}" if session is not None else "Période non précisée"
    )
    return "Relevé de notes", sous_titre, corps, mention, "Le Directeur des études"


def _rendre_quitus(styles, contexte: Dict[str, Any]) -> tuple:
    finances = contexte["finances"]
    devise = contexte["etablissement"].get("devise") or ""
    solde = finances["solde"]
    reserves: List[str] = []
    if not finances["factures"]:
        reserves.append("Aucune facture émise sur la session demandée.")

    lignes = [
        [
            facture["numero"],
            texte_ou_valeur(facture["emission"]),
            montant(facture["total"], devise),
            montant(facture["regle"], devise),
            montant(facture["reste"], devise),
        ]
        for facture in finances["factures"]
    ]

    if solde <= 0:
        conclusion = (
            "L'étudiant ne présente aucune dette au titre des frais scolaires. "
            "En conséquence, il lui est accorde quitus.")
        favorable = True
    else:
        conclusion = (
            f"L'étudiant présente un solde restant dû de {montant(solde, devise)}. "
            "Le présent document ne vaut pas quitus."
        )
        favorable = False

    corps: List[Any] = [
        _bloc_identite(styles, contexte["etudiant"]),
        Paragraph("Situation financière", styles["section"]),
        _tableau(
            styles,
            ["Facture", "Émission", "Montant", "Réglé", "Reste dû"],
            lignes,
            largeurs=[36 * mm, 24 * mm, 34 * mm, 32 * mm, 30 * mm],
            alignements=["g", "g", "d", "d", "d"],
            vide="Aucune facture n'est enregistrée pour cette session.",
        ),
        Spacer(1, 3 * mm),
        _tableau(
            styles,
            ["Total facturé", "Total réglé", "Solde"],
            [[
                montant(finances["total_facture"], devise),
                montant(finances["total_regle"], devise),
                montant(solde, devise),
            ]],
            largeurs=[53 * mm, 53 * mm, 54 * mm],
            alignements=["d", "d", "d"],
        ),
        Paragraph("Conclusion", styles["section"]),
        _encadre_etat(styles, conclusion, favorable),
    ]
    mention = (
        "Situation calculée à partir des factures et des règlements enregistrés "
        "à la date d'émission. Les règlements postérieurs ne sont pas pris en "
        "compte : le document reflète la situation au moment de son émission."
    )
    session = contexte.get("session")
    sous_titre = f"Session {session.nom}" if session is not None else "Toutes sessions"
    return "Quitus financier", sous_titre, corps, mention, "Le Service de comptabilité"


_RENDUS = {
    CODE_CERTIFICAT: _rendre_certificat,
    CODE_RELEVE: _rendre_releve,
    CODE_QUITUS: _rendre_quitus,
}


def render_document(type_code: str, contexte: Dict[str, Any]) -> bytes:
    """Rend le PDF d'un type de document et retourne ses octets."""

    rendu = _RENDUS.get(type_code)
    if rendu is None:
        raise ValueError(f"Aucun rendu pour le type de document {type_code!r}.")

    police = _police_disponible()
    styles = _styles(police)
    titre, sous_titre, corps, mention, signataire = rendu(styles, contexte)
    numero = contexte["numero"]
    etablissement = contexte["etablissement"]

    tampon = io.BytesIO()
    doc = BaseDocTemplate(
        tampon,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=13 * mm,
        bottomMargin=22 * mm,
        title=f"{titre} — {etablissement.get('nom') or 'EduManagePro'}",
        author=str(etablissement.get("nom") or "EduManagePro"),
        subject=f"Document officiel {numero}",
    )
    doc.addPageTemplates(
        [
            PageTemplate(
                id="document",
                frames=[
                    Frame(
                        doc.leftMargin, doc.bottomMargin,
                        width=doc.width, height=doc.height, id="corps",
                    )
                ],
                onPage=lambda canvas, document: _pied(canvas, numero, etablissement, police),
            )
        ]
    )

    histoire: List[Any] = [
        *_entete_etablissement(styles, etablissement),
        Paragraph(titre, styles["titre"]),
        Paragraph(sous_titre, styles["sous_titre"]),
        *corps,
        Spacer(1, 3 * mm),
        Paragraph(mention, styles["mention"]),
        *_bloc_reserves(styles, contexte.get("reserves", [])),
        *_bloc_signature(styles, signataire),
    ]
    doc.build(histoire)
    return tampon.getvalue()


def _pied(canvas, numero: str, etablissement: Dict[str, Any], police: str) -> None:
    """Pied de page : identite de l'etablissement et reference du document."""

    canvas.saveState()
    largeur, _ = A4
    canvas.setStrokeColor(GRIS_BORD)
    canvas.setLineWidth(0.4)
    canvas.line(18 * mm, 16 * mm, largeur - 18 * mm, 16 * mm)
    canvas.setFont(police, 7)
    canvas.setFillColor(GRIS_TEXTE)
    canvas.drawString(18 * mm, 11.5 * mm, str(etablissement.get("nom") or "EduManagePro"))
    canvas.drawRightString(
        largeur - 18 * mm, 11.5 * mm,
        f"Référence {numero} — page {canvas.getPageNumber()}",
    )
    canvas.restoreState()


__all__ = ["montant", "render_document", "texte_ou_valeur", "VALEUR_ABSENTE"]
