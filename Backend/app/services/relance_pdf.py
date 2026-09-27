"""Rendu de la lettre de relance.

Une lettre de relance n'est **pas** une attestation : elle ne certifie aucun
fait, elle réclame un paiement. La rattacher au catalogue des documents
officiels l'y ferait figurer au registre d'émission, avec une empreinte et un
instantané — c'est-à-dire comme une pièce justificative. Ce serait un
contre-sens : la lettre est un acte de recouvrement, pas une preuve.

Elle n'est donc pas dans ``document_types.py``, mais elle emprunte le même
gabarit d'en-tête, de pied de page et de signature que les documents officiels,
parce que c'est la même main qui l'imprime.

Deux partis pris, tenus par le module entier :

1. **La lettre dit ce qui a été réclamé ce jour-là.** Elle rend
   ``relance.factures_concernees`` et ``relance.montant_reclame``, l'instantané
   figé à la relance — jamais les factures du jour. Un encaissement postérieur
   ne réécrit pas une lettre déjà remise.

2. **Les relances antérieures sont celles d'avant, pas celles d'aujourd'hui.**
   Le décompte s'arrête aux relances de niveau inférieur. Re-générer la
   deuxième lettre après une troisième relance doit continuer à dire
   « deuxième », sinon l'historique ment sur ce qui a été remis.

La construction est scindée en deux : :func:`composer` décide **ce que la
lettre dit**, :func:`rendre_lettre` ne fait que la mettre en page. Extraire le
texte d'un PDF en fouillant ses flux compressés serait fragile — la police de
production est un sous-ensemble dont le texte sort re-codé — et ne prouverait
rien sur la décision. Le test lit donc le contenu composé.
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
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from app.models.relance import Relance
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
    montant,
    texte_ou_valeur,
)

TITRE = "Lettre de relance"

MENTION = (
    "La présente lettre est une demande de règlement. Elle ne constitue pas "
    "une attestation d'inscription, de scolarité ou de réussite, et ne tient "
    "lieu d'aucun document officiel de cet établissement."
)

#: Le catalogue des moyens du service fait foi ; la lettre n'invente pas une
#: facon de contact que le serveur ne connait pas.
INTITULES_MOYEN = {
    "Courrier": "par courrier",
    "Email": "par courriel",
    "Appel telephonique": "par appel téléphonique",
    "Guichet": "au guichet",
    "SMS": "par SMS",
}


def reference_relance(relance: Relance, matricule: Optional[str]) -> str:
    """Référence stable, entièrement dérivée de données réelles.

    Un compteur séquentiel serait une donnée inventée : il n'existe nulle part
    dans la base. La référence est donc composée de ce qui existe — la date de
    la relance, le matricule, et le niveau.
    """

    return (
        f"REL-{relance.date_relance:%Y%m%d}-{matricule or 'SANS-MATRICULE'}"
        f"-N{relance.niveau}"
    )


async def relances_precedentes(db, relance: Relance) -> List[Relance]:
    """Les seules relances antérieures : ce que l'agent savait ce jour-là.

    Le filtre porte sur le **niveau**, pas sur la date de création. Une relance
    enregistrée plus tard mais de niveau inférieur ne réécrit pas non plus ce
    que la lettre présentait.
    """

    from sqlalchemy import select

    stmt = (
        select(Relance)
        .where(
            Relance.etudiant_id == relance.etudiant_id,
            Relance.niveau < relance.niveau,
        )
        .order_by(Relance.niveau)
    )
    return list((await db.execute(stmt)).scalars().all())


# ---------------------------------------------------------------------------
# Tableaux
# ---------------------------------------------------------------------------
def _style_tableau(entetes: bool) -> TableStyle:
    commandes = [
        ("GRID", (0, 0), (-1, -1), 0.4, GRIS_BORD),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if entetes:
        commandes.insert(0, ("BACKGROUND", (0, 0), (-1, 0), ACCENT))
        commandes.append(("ALIGN", (2, 1), (-1, -1), "RIGHT"))
    else:
        commandes.append(("VALIGN", (0, 0), (-1, -1), "TOP"))
    commandes.append(("ROWBACKGROUNDS", (0, 1 if entetes else 0), (-1, -1), [colors.white, GRIS_CLAIR]))
    return TableStyle(commandes)


def _tableau_factures(styles, factures: List[Dict[str, Any]], devise: str) -> Table:
    """Les factures de l'instantané, telles qu'elles ont été réclamées."""

    entetes = ["Facture", "Échéance", "Montant", "Réglé", "Reste"]
    lignes: List[List[Any]] = [
        [Paragraph(entete, styles["cellule_entete"]) for entete in entetes]
    ]
    for facture in factures:
        lignes.append([
            Paragraph(texte_ou_valeur(facture.get("numero")), styles["cellule"]),
            Paragraph(texte_ou_valeur(facture.get("date_echeance")), styles["cellule"]),
            Paragraph(montant(facture.get("montant_total"), devise), styles["cellule_droite"]),
            Paragraph(montant(facture.get("montant_regle"), devise), styles["cellule_droite"]),
            Paragraph(montant(facture.get("reste"), devise), styles["cellule_droite"]),
        ])

    tableau = Table(
        lignes,
        colWidths=[36 * mm, 26 * mm, 34 * mm, 30 * mm, 34 * mm],
        repeatRows=1,
    )
    tableau.setStyle(_style_tableau(entetes=True))
    return tableau


def _tableau_paires(styles, lignes: List[Tuple[str, Any]]) -> Table:
    donnees = [
        [
            Paragraph(libelle, styles["cellule"]),
            Paragraph(texte_ou_valeur(valeur), styles["cellule"]),
        ]
        for libelle, valeur in lignes
    ]
    tableau = Table(donnees, colWidths=[58 * mm, 102 * mm])
    tableau.setStyle(_style_tableau(entetes=False))
    return tableau


# ---------------------------------------------------------------------------
# Composition : ce que la lettre dit
# ---------------------------------------------------------------------------
def composer(
    relance: Relance,
    infos: Dict[str, Any],
    anterieures: Optional[List[Relance]] = None,
) -> List[Any]:
    """Construit le contenu de la lettre.

    Fonction **pure** : elle ne lit ni la base, ni la dette du jour. Elle rend ce
    que la relance a figé. C'est ici que se prend la décision, et c'est ce que
    les tests vérifient ; la mise en page, plus bas, ne décide de rien.
    """

    styles = _styles(_police_disponible())
    anterieures = list(anterieures or [])

    etudiant = relance.etudiant
    devise = str(infos.get("devise") or "")
    matricule = etudiant.matricule if etudiant else None
    reference = reference_relance(relance, matricule)
    nom_complet = " ".join(
        partie
        for partie in (
            (etudiant.nom if etudiant else None),
            (etudiant.prenom if etudiant else None),
        )
        if partie
    ) or VALEUR_ABSENTE

    # L'instantane, pas la creance du jour.
    factures = [f for f in (relance.factures_concernees or []) if isinstance(f, dict)]
    plus_ancienne = factures[0].get("date_echeance") if factures else VALEUR_ABSENTE

    corps: List[Any] = [
        Paragraph(f"Référence {reference} — {nom_complet}", styles["sous_titre"]),
    ]

    # -- Destinataire ----------------------------------------------------
    corps.append(Paragraph("Destinataire", styles["section"]))
    corps.append(_tableau_paires(styles, [
        ("Nom et prénom", nom_complet),
        ("Matricule", matricule),
        ("Filière", getattr(etudiant, "filiere", None)),
        ("Adresse", getattr(etudiant, "adresse", None)),
        ("Téléphone", getattr(etudiant, "telephone", None)),
        ("Courriel", getattr(etudiant, "email", None)),
    ]))

    # -- Objet et montant reclamé ----------------------------------------
    corps.append(Paragraph("Objet : règlement de facture échue", styles["section"]))
    corps.append(Paragraph(
        f"Nous avons enregistré à votre compte une somme de "
        f"<b>{montant(relance.montant_reclame, devise)}</b> restant due. "
        f"La plus ancienne échéance impayée date du {plus_ancienne}, "
        f"soit {relance.retard_jours} jour(s) de retard.",
        styles["corps"],
    ))
    corps.append(Paragraph(
        "Nous vous invitons à régulariser cette situation auprès du service de "
        "scolarité. Un règlement partiel reste recevable : il nous permet de "
        "constater un solde et d'interrompre le suivi.",
        styles["corps"],
    ))

    # -- Detail des factures ---------------------------------------------
    if factures:
        corps.append(Paragraph("Factures concernées", styles["section"]))
        corps.append(Paragraph(
            "Montants repris tels qu'ils étaient au jour de la présente relance.",
            styles["mention"],
        ))
        corps.append(_tableau_factures(styles, factures, devise))

    # -- Relances anterieures --------------------------------------------
    if anterieures:
        corps.append(Paragraph("Relances précédentes", styles["section"]))
        corps.append(Paragraph(
            f"Ce rappel est votre {relance.niveau}e relance. Les précédentes ont "
            "été adressées aux dates et par les moyens suivants :",
            styles["corps"],
        ))
        corps.append(_tableau_paires(styles, [
            (
                f"{anterieure.niveau}e relance",
                f"{anterieure.date_relance.strftime('%d/%m/%Y')} — "
                f"{INTITULES_MOYEN.get(anterieure.moyen, anterieure.moyen)}",
            )
            for anterieure in anterieures
        ]))

    # -- La presente relance ----------------------------------------------
    corps.append(Paragraph("La présente relance", styles["section"]))
    corps.append(_tableau_paires(styles, [
        ("Référence", reference),
        ("Date", relance.date_relance.strftime("%d/%m/%Y")),
        ("Niveau", f"{relance.niveau}e relance"),
        ("Moyen retenu", INTITULES_MOYEN.get(relance.moyen, relance.moyen)),
        ("Montant réclamé", montant(relance.montant_reclame, devise)),
    ]))
    if relance.message:
        corps.append(Spacer(1, 2 * mm))
        corps.append(Paragraph(relance.message, styles["corps"]))

    # La mention n'est pas une question de mise en page : c'est une
    # declaration de ce que la lettre est. Elle fait donc partie du contenu
    # compose, et non du gabarit — sinon un rendu alternatif pourrait l'omettre
    # sans qu'on s'en apercoive.
    corps.append(Spacer(1, 3 * mm))
    corps.append(Paragraph(MENTION, styles["mention"]))

    return corps


def signataire_de(relance: Relance) -> str:
    """Qui a constate la relance.

    Jamais deviné : le nom vient de l'auteur enregistré, et à défaut on nomme
    le service — ce qui est alors la réalité de l'acte. Un nom inventé ferait porter
    à quelqu'un une relance qu'il n'a pas faite.
    """

    auteur = relance.auteur
    if auteur is not None:
        nom = getattr(auteur, "full_name", None)
        if nom:
            return str(nom)
    return "Le service de scolarité"


# ---------------------------------------------------------------------------
# Rendu : la mise en page
# ---------------------------------------------------------------------------
async def rendre_lettre(
    db,
    *,
    relance: Relance,
    etablissement,
) -> Tuple[bytes, str]:
    """Rend la lettre et retourne ``(octets, nom_fichier)``.

    Le nom de fichier reprend la référence : une lettre rangée sous
    ``lettre.pdf`` serait introuvable au moment d'en avoir besoin.
    """

    infos = infos_etablissement(etablissement) if etablissement is not None else {}
    anterieures = await relances_precedentes(db, relance)
    police = _police_disponible()
    styles = _styles(police)

    matricule = relance.etudiant.matricule if relance.etudiant else None
    reference = reference_relance(relance, matricule)

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
        subject=f"Relance {reference}",
    )
    doc.addPageTemplates([
        PageTemplate(
            id="relance",
            frames=[Frame(
                doc.leftMargin, doc.bottomMargin,
                width=doc.width, height=doc.height, id="corps",
            )],
            onPage=lambda canvas, document: _pied(canvas, reference, infos, police),
        )
    ])

    histoire: List[Any] = [
        *_entete_etablissement(styles, infos),
        Paragraph(TITRE, styles["titre"]),
        *composer(relance, infos, anterieures),
        Spacer(1, 8 * mm),
        Paragraph("Le service de scolarité", styles["signature"]),
        Paragraph(signataire_de(relance), styles["signature"]),
    ]
    doc.build(histoire)
    return tampon.getvalue(), f"relance_{reference.replace('/', '-')}.pdf"


__all__ = [
    "INTITULES_MOYEN",
    "MENTION",
    "TITRE",
    "composer",
    "reference_relance",
    "relances_precedentes",
    "rendre_lettre",
    "signataire_de",
]
