"""Catalogue des types de documents officiels.

Source de verite unique, importable par Alembic sans charger l'application.

Regle absolue : **un document officiel n'est delivrable que si les donnees
qu'il atteste sont reellement persistes.**  Aucun type n'est propose si son
contenu ne peut pas etre prouve par la base.

C'est pourquoi ``attestation_reussite`` et ``attestation_diplome`` sont
absents : les decisions de deliberation sont calculees a la volee et ne sont
jamais enregistrees.  Les emettre reviendrait a inventer un droit academique.
Ils deviendront disponibles le jour ou la deliberation sera **persistee** (decision,
date, jury, mention), pas avant.

Chaque type declare ses conditions de validite.  Une condition non satisfaite
bloque la generation avec un message explicite : l'appelant ne peut pas
produire un document faux.
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping, Tuple


#: Prefixe de numerotation par type : ``CERT-2026-0001``.
CODE_CERTIFICAT = "certificat_scolarite"
CODE_RELEVE = "releve_notes"
CODE_QUITUS = "quitus_financier"

PERMISSION_DOCUMENTS = "documents.issue"


@dataclass(frozen=True)
class DocumentTypeDefinition:
    """Definition immuable d'un type de document officiel."""

    code: str
    #: Prefixe de numerotation, affiche sur le document.
    prefixe: str
    libelle: str
    description: str
    #: Permission dynamique requise pour emettre ce document.
    permission: str = PERMISSION_DOCUMENTS
    #: Elements de donnee indispensables. Une donnee manquante (hors null
    #: tolerated) bloque la generation plutot que d'etre masquee.
    champs_obligatoires: Tuple[str, ...] = field(default_factory=tuple)
    #: Champs dont l'absence est signalee dans le document sans le bloquer.
    champs_requis_non_bloquants: Tuple[str, ...] = field(default_factory=tuple)
    #: Le document porte-t-il une liste d'elements (tableau) ?
    avec_tableau: bool = False


DOCUMENT_TYPES: Tuple[DocumentTypeDefinition, ...] = (
    DocumentTypeDefinition(
        code=CODE_CERTIFICAT,
        prefixe="CERT",
        libelle="Certificat de scolarite",
        description=(
            "Atteste que l'etudiant est regulierement inscrit dans l'etablissement "
            "pour l'annee academique indiquee."
        ),
        champs_obligatoires=("etudiant.matricule", "etudiant.nom", "etudiant.prenom", "inscription"),
    ),
    DocumentTypeDefinition(
        code=CODE_RELEVE,
        prefixe="REL",
        libelle="Releve de notes",
        description=(
            "Recapitulatif des notes de l'etudiant, avec moyenne par matiere "
            "et moyenne generale ponderee par les coefficients."
        ),
        champs_obligatoires=("etudiant.matricule", "etudiant.nom", "etudiant.prenom"),
        avec_tableau=True,
    ),
    DocumentTypeDefinition(
        code=CODE_QUITUS,
        prefixe="QUIT",
        libelle="Quitus financier",
        description=(
            "Atteste la situation financière de l'etudiant pour la session : "
            "montant facture, montant regle et solde."
        ),
        champs_obligatoires=("etudiant.matricule", "etudiant.nom", "etudiant.prenom", "factures"),
    ),
)

DOCUMENT_TYPES_BY_CODE: Mapping[str, DocumentTypeDefinition] = MappingProxyType(
    {item.code: item for item in DOCUMENT_TYPES}
)

DOCUMENT_CODES: frozenset = frozenset(item.code for item in DOCUMENT_TYPES)


def get_document_type(code: str) -> DocumentTypeDefinition | None:
    """Retourne la definition d'un type de document, ou ``None``."""

    return DOCUMENT_TYPES_BY_CODE.get((code or "").strip().lower())


__all__ = [
    "CODE_CERTIFICAT",
    "CODE_QUITUS",
    "CODE_RELEVE",
    "DOCUMENT_CODES",
    "DOCUMENT_TYPES",
    "DOCUMENT_TYPES_BY_CODE",
    "DocumentTypeDefinition",
    "PERMISSION_DOCUMENTS",
    "get_document_type",
]
