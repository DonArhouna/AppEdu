"""
Service metier des documents officiels.

Principe directeur : **on n'atteste que ce qui est prouve par la base.**

Chaque type declare ses conditions dans ``app.core.document_types``.  Si une
condition n'est pas satisfaite, la generation est refusee avec un message qui
indique quoi corriger.  Un document « presque vrai » n'est jamais produit :
pour un acte administratif, un trou declare vaut mieux qu'une valeur inventee.

La mise en page vit dans ``pdf_service`` ; ce module collecte les donnees,
verifie les conditions, reserve le numero et ecrit le fichier.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.document_types import (
    CODE_CERTIFICAT,
    CODE_QUITUS,
    CODE_RELEVE,
    get_document_type,
)
from app.models.academic import Classe, Inscription
from app.models.document_officiel import DocumentOfficiel
from app.models.etablissement import Etablissement
from app.models.etudiant import Etudiant
from app.models.finance import Facture
from app.models.pedagogie import Note
from app.models.session_academique import SessionAcademique
from app.models.structure import Matiere, UniteEnseignement
from app.services.pdf_service import render_document


class DocumentInvalide(ValueError):
    """Le document ne peut pas etre emis : donnees manquantes ou incoherentes.

    Le message est destine a l'administrateur : il doit indiquer l'action a
    mener, pas seulement la cause technique.
    """


# ---------------------------------------------------------------------------
# Stockage
# ---------------------------------------------------------------------------
def racine_documents() -> Path:
    """Racine de stockage des PDF, creee a la demande."""

    configure = Path(settings.DOCUMENTS_STORAGE_DIR)
    racine = (
        configure
        if configure.is_absolute()
        else Path(__file__).resolve().parents[2] / configure
    )
    racine.mkdir(parents=True, exist_ok=True)
    return racine.resolve()


def _ecrire_pdf(etudiant: Etudiant, type_document: str, numero: str, contenu: bytes) -> str:
    """Ecrit le PDF et retourne son chemin relatif a la racine de stockage."""

    segment = (
        re.sub(r"[^A-Za-z0-9._-]+", "_", etudiant.matricule).strip("._") or "sans-matricule"
    )
    nom = f"{segment}_{type_document}_{numero}.pdf"
    chemin = racine_documents() / segment / nom
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_bytes(contenu)
    return f"{segment}/{nom}"


def lire_pdf(chemin_relatif: str) -> Optional[bytes]:
    """Relit un PDF emis. Retourne ``None`` si le fichier a disparu."""

    racine = racine_documents()
    cible = (racine / chemin_relatif).resolve()
    # Protection contre la traversee de repertoire.
    if not str(cible).startswith(str(racine)):
        return None
    if not cible.is_file():
        return None
    return cible.read_bytes()


# ---------------------------------------------------------------------------
# Numerotation
# ---------------------------------------------------------------------------
async def prochain_numero(db: AsyncSession, prefixe: str, annee: int) -> str:
    """Reserve le prochain numero libre d'un type pour une annee.

    L'unicite est garantie en base par un index sur (type, numero).  En cas de
    collision — deux emissions simultanees — l'appelant reessaie avec le numero
    suivant plutot que d'echouer silencieusement.
    """

    motif = f"{prefixe}-{annee}-%"
    stmt = select(DocumentOfficiel.numero).where(DocumentOfficiel.numero.like(motif))
    existants = {str(valeur) for valeur in (await db.execute(stmt)).scalars().all()}

    sequence = 1
    while f"{prefixe}-{annee}-{sequence:04d}" in existants:
        sequence += 1
    return f"{prefixe}-{annee}-{sequence:04d}"


# ---------------------------------------------------------------------------
# Collecte des donnees reelles
# ---------------------------------------------------------------------------
async def _etablissement(db: AsyncSession) -> Etablissement:
    resultat = await db.execute(select(Etablissement).limit(1))
    etablissement = resultat.scalars().first()
    if etablissement is None:
        raise DocumentInvalide(
            "Aucun établissement configuré. Terminez l'installation avant "
            "d'émettre un document officiel."
        )
    return etablissement


def infos_etablissement(etablissement: Etablissement) -> Dict[str, Any]:
    """Donnees d'impression de l'etablissement, issues de la configuration."""

    return {
        "nom": etablissement.nom,
        "sigle": etablissement.sigle,
        "adresse": etablissement.adresse,
        "telephone": etablissement.telephone,
        "email": etablissement.email,
        "devise": etablissement.devise,
        # Chemin relatif du logo ; le rendu PDF resout le fichier lui-meme.
        # ``None`` si l'etablissement n'a pas de branding : l'en-tete reste
        # alors centre, comme avant.
        "logo_url": etablissement.logo_url,
    }


async def _inscription_active(
    db: AsyncSession, etudiant_id: str, session_id: Optional[str]
) -> Optional[Inscription]:
    """Inscription active de l'etudiant, filtree sur la session si fournie."""

    stmt = (
        select(Inscription)
        .options(
            selectinload(Inscription.session),
            selectinload(Inscription.classe).selectinload(Classe.filiere),
            selectinload(Inscription.classe).selectinload(Classe.niveau),
        )
        .where(Inscription.etudiant_id == etudiant_id, Inscription.statut == "active")
    )
    if session_id:
        stmt = stmt.where(Inscription.session_id == session_id)
    inscriptions = list((await db.execute(stmt)).scalars().all())
    if not inscriptions:
        return None
    inscriptions.sort(key=lambda item: item.date_inscription, reverse=True)
    return inscriptions[0]


async def notes_et_moyennes(
    db: AsyncSession, etudiant_id: str, session_id: Optional[str]
) -> Tuple[List[Dict[str, Any]], Optional[float]]:
    """Notes par matiere et moyenne generale ponderee.

    La moyenne n'est calculee que si des notes existent.  Une matiere non notee
    n'apparait pas et n'est jamais comptee comme un zero : le document porte
    la moyenne de ce qui est reellement saisi.
    """

    stmt = (
        select(Note, Matiere, UniteEnseignement)
        .join(Matiere, Note.matiere_id == Matiere.id)
        .outerjoin(UniteEnseignement, Matiere.ue_id == UniteEnseignement.id)
        .where(Note.etudiant_id == etudiant_id)
        .order_by(Matiere.nom)
    )
    if session_id:
        stmt = stmt.where(Note.session_id == session_id)

    accumul: Dict[str, Dict[str, Any]] = {}
    for note, matiere, ue in (await db.execute(stmt)).all():
        entree = accumul.setdefault(
            str(matiere.id),
            {
                "matiere": matiere.nom,
                "code": matiere.code,
                "ue": ue.nom if ue else None,
                "notes": [],
                "somme_ponderee": 0.0,
                "somme_coefficients": 0.0,
            },
        )
        coefficient = float(note.coefficient or 1.0)
        entree["notes"].append(float(note.valeur))
        entree["somme_ponderee"] += float(note.valeur) * coefficient
        entree["somme_coefficients"] += coefficient

    resultat: List[Dict[str, Any]] = []
    total_pondere = 0.0
    total_coefficients = 0.0

    for entree in accumul.values():
        moyenne = (
            round(entree["somme_ponderee"] / entree["somme_coefficients"], 2)
            if entree["somme_coefficients"]
            else None
        )
        resultat.append(
            {
                "matiere": entree["matiere"],
                "code": entree["code"],
                "ue": entree["ue"],
                "detail": ", ".join(f"{valeur:g}" for valeur in entree["notes"]),
                "coefficient": round(entree["somme_coefficients"], 2),
                "moyenne": moyenne,
            }
        )
        if moyenne is not None:
            total_pondere += moyenne * entree["somme_coefficients"]
            total_coefficients += entree["somme_coefficients"]

    moyenne_generale = round(total_pondere / total_coefficients, 2) if total_coefficients else None
    resultat.sort(key=lambda item: (item["ue"] or "", item["matiere"]))
    return resultat, moyenne_generale


def _reste_a_payer(facture) -> float:
    """Solde restant d'une facture.

    On recalcule depuis les colonnes plutot que d'appeler la methode du
    modele : une affectation d'attribut sur l'instance masquerait la methode
    et le calcul resterait correct dans tous les cas.
    """

    return max(0.0, round(float(facture.montant_total) - float(facture.montant_paye), 2))


async def situation_financiere(
    db: AsyncSession, etudiant_id: str, session_id: Optional[str]
) -> Dict[str, Any]:
    """Factures et solde de l'etudiant pour la session demandee."""

    stmt = (
        select(Facture)
        .where(Facture.etudiant_id == etudiant_id)
        .order_by(Facture.date_emission)
    )
    if session_id:
        stmt = stmt.where(Facture.session_id == session_id)
    factures = list((await db.execute(stmt)).scalars().all())

    return {
        "factures": [
            {
                "numero": facture.numero_facture,
                "emission": facture.date_emission,
                "echeance": facture.date_echeance,
                "total": round(float(facture.montant_total), 2),
                "regle": round(float(facture.montant_paye), 2),
                "reste": _reste_a_payer(facture),
                "statut": facture.statut,
            }
            for facture in factures
        ],
        "total_facture": round(sum(float(f.montant_total) for f in factures), 2),
        "total_regle": round(sum(float(f.montant_paye) for f in factures), 2),
        "solde": round(sum(_reste_a_payer(f) for f in factures), 2),
    }


# ---------------------------------------------------------------------------
# Verification des conditions par type
# ---------------------------------------------------------------------------
def _verifier_conditions(
    type_code: str,
    etudiant: Etudiant,
    inscription: Optional[Inscription],
    notes: Sequence[Dict[str, Any]],
    finances: Dict[str, Any],
) -> None:
    """Applique les conditions declarees par le type de document.

    Leve ``DocumentInvalide`` avec le nom de la donnee a corriger.
    """

    manque: List[str] = []
    if not (etudiant.matricule or "").strip():
        manque.append("le matricule de l'étudiant")
    if not (etudiant.nom or "").strip():
        manque.append("le nom de l'étudiant")
    if not (etudiant.prenom or "").strip():
        manque.append("le prénom de l'étudiant")

    if type_code == CODE_CERTIFICAT and inscription is None:
        manque.append(
            "une inscription active (le certificat atteste une scolarité : "
            "l'étudiant doit avoir une inscription active)"
        )
    if type_code == CODE_QUITUS and not finances["factures"]:
        manque.append(
            "au moins une facture sur la session (un quitus sans facture "
            "n'attesterait rien)"
        )
    if type_code == CODE_RELEVE and not notes:
        manque.append(
            "au moins une note saisie sur la session (un relevé vide "
            "n'attesterait aucun résultat)"
        )

    if manque:
        raise DocumentInvalide(
            "Document non émissible : il manque "
            + ", ".join(manque)
            + ". Corrigez la fiche dans le registre des étudiants avant de réémettre."
        )


# ---------------------------------------------------------------------------
# Emission
# ---------------------------------------------------------------------------
async def emettre_document(
    db: AsyncSession,
    *,
    etudiant_id: str,
    type_code: str,
    emis_par_id: Optional[int] = None,
    session_id: Optional[str] = None,
    remplace_document_id: Optional[str] = None,
    motif_duplicata: Optional[str] = None,
    reservation: bool = False,
) -> DocumentOfficiel:
    """Emet un document officiel et enregistre sa tracabilite.

    ``reservation=True`` reserve un numero sans produire le PDF : c'est le
    mode « apercu » de l'ecran, qui permet d'afficher le numero avant que
    l'administration ne decide de delivrer.
    """

    definition = get_document_type(type_code)
    if definition is None:
        raise DocumentInvalide(f"Type de document inconnu : {type_code!r}.")

    etudiant = await db.get(Etudiant, etudiant_id)
    if etudiant is None:
        raise DocumentInvalide("Étudiant introuvable.")

    etablissement = await _etablissement(db)
    session_obj = await db.get(SessionAcademique, session_id) if session_id else None
    if session_id and session_obj is None:
        raise DocumentInvalide("Session introuvable.")

    inscription = await _inscription_active(db, etudiant_id, session_id)
    notes, moyenne = await notes_et_moyennes(db, etudiant_id, session_id)
    finances = await situation_financiere(db, etudiant_id, session_id)

    _verifier_conditions(definition.code, etudiant, inscription, notes, finances)

    annee = date.today().year
    numero = await prochain_numero(db, definition.prefixe, annee)

    if reservation:
        return DocumentOfficiel(
            id=str(uuid.uuid4()),
            type_document=definition.code,
            numero=numero,
            etudiant_id=etudiant_id,
            session_id=session_id,
            annee=annee,
            fichier="",
            sha256="",
            taille_octets=0,
            donnees={},
            reserves=[],
            emis_par_id=emis_par_id,
            emis_le=datetime.now(),
        )

    contexte = {
        "etablissement": infos_etablissement(etablissement),
        "etudiant": etudiant,
        "inscription": inscription,
        "session": session_obj,
        "notes": notes,
        "moyenne": moyenne,
        "finances": finances,
        "numero": numero,
    }
    contenu = render_document(definition.code, contexte)
    chemin = _ecrire_pdf(etudiant, definition.code, numero, contenu)

    document = DocumentOfficiel(
        id=str(uuid.uuid4()),
        type_document=definition.code,
        numero=numero,
        etudiant_id=etudiant_id,
        session_id=session_id,
        annee=annee,
        fichier=chemin,
        sha256=hashlib.sha256(contenu).hexdigest(),
        taille_octets=len(contenu),
        donnees={
            # Identite de l'etablissement au moment de l'emission. Sans elle,
            # un certificat delivre devient inexplicable des que
            # l'etablissement change d'adresse ou retire son logo : on ne
            # saurait plus sous quel nom il a ete signe.
            "etablissement": infos_etablissement(etablissement),
            "etudiant": {
                "matricule": etudiant.matricule,
                "nom": etudiant.nom,
                "prenom": etudiant.prenom,
                "filiere": etudiant.filiere,
                "niveau": etudiant.niveau,
            },
            "session": session_obj.nom if session_obj else None,
            "moyenne_generale": moyenne,
            "solde": finances["solde"],
            "nb_notes": len(notes),
            "nb_factures": len(finances["factures"]),
        },
        reserves=[],
        remplace_document_id=remplace_document_id,
        motif_duplicata=motif_duplicata,
        emis_par_id=emis_par_id,
        emis_le=datetime.now(),
    )
    db.add(document)
    await db.flush()
    return document


__all__ = [
    "DocumentInvalide",
    "emettre_document",
    "infos_etablissement",
    "lire_pdf",
    "notes_et_moyennes",
    "prochain_numero",
    "racine_documents",
    "situation_financiere",
]
