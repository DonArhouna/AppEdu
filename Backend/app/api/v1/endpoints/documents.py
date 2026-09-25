"""
Endpoints des documents officiels.

Trois usages distincts :

- **Consulter** l'historique et les types disponibles (``students.read``) ;
- **Emettre** un document pour un etudiant, en lot, ou en duplicata
  (``documents.issue``) ;
- **Telecharger** le PDF emis (``students.read``) : un secretaire doit
  pouvoir reimprimer un document deja delivre.

La separation des permissions est volontaire : consulter l'historique n'exige
pas le droit d'emettre.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, require_permission, require_students_read
from app.core.document_types import DOCUMENT_TYPES, get_document_type
from app.models.academic import Classe, Inscription
from app.models.document_officiel import DocumentOfficiel
from app.models.etudiant import Etudiant
from app.models.session_academique import SessionAcademique
from app.models.utilisateur import Utilisateur
from app.schemas.document_officiel import (
    DocumentOfficielListe,
    DuplicataRequest,
    EmissionDocumentRequest,
    LotDocumentRequest,
    LotDocumentResponse,
    ResultatLigne,
    TypeDocumentOut,
)
from app.services.document_service import (
    DocumentInvalide,
    emettre_document,
    infos_etablissement,
    lire_pdf,
)
from app.services.document_service import _etablissement  # noqa: F401  (validation)

logger = logging.getLogger(__name__)
router = APIRouter()

#: Emission : permission dediee, distincte de l'ecriture sur les dossiers.
require_documents_issue = require_permission("documents.issue")

#: Motifs acceptes pour un duplicata.
MOTIFS_DUPLICATA = {
    "perte": "Perte",
    "vol": "Vol",
    "detruction": "Destruction",
    "erreur": "Erreur de saisie sur l'original",
}


def _libelle(type_code: str) -> str:
    definition = get_document_type(type_code)
    return definition.libelle if definition else type_code


@router.get(
    "/types",
    response_model=List[TypeDocumentOut],
    summary="Types de documents officiels disponibles",
)
async def lister_types(
    _auth=Depends(require_students_read),
):
    """Catalogue des types emissibles et conditions a satisfaire.

    Les types dont les donnees ne sont pas persistees (deliberation, diplome)
    ne figurent pas ici : on ne peut pas attester ce qui n'est pas enregistre.
    """

    return [
        TypeDocumentOut(
            code=definition.code,
            prefixe=definition.prefixe,
            libelle=definition.libelle,
            description=definition.description,
            permission=definition.permission,
            avec_tableau=definition.avec_tableau,
            conditions=list(definition.champs_obligatoires),
        )
        for definition in DOCUMENT_TYPES
    ]


@router.post(
    "/etudiants/{etudiant_id}",
    response_model=DocumentOfficielListe,
    status_code=status.HTTP_201_CREATED,
    summary="Émettre un document officiel pour un étudiant",
)
async def emettre(
    etudiant_id: str,
    payload: EmissionDocumentRequest,
    db: AsyncSession = Depends(get_db),
    acteur: Utilisateur = Depends(require_documents_issue),
):
    """Émet un document et enregistre sa traçabilité.

    En mode ``apercu``, un numéro est réservé sans produire de PDF : l'agent
    voit la référence avant de|delivrer.
    """

    try:
        document = await emettre_document(
            db,
            etudiant_id=etudiant_id,
            type_code=payload.type_document,
            emis_par_id=acteur.id,
            session_id=payload.session_id,
            reservation=payload.apercu,
        )
    except DocumentInvalide as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    etudiant = await db.get(Etudiant, etudiant_id)
    return _enrichir(document, etudiant)


@router.post(
    "/etudiants/{etudiant_id}/apercu",
    response_model=DocumentOfficielListe,
    summary="Réserver un numéro sans générer le document",
)
async def apercu(
    etudiant_id: str,
    payload: EmissionDocumentRequest,
    db: AsyncSession = Depends(get_db),
    acteur: Utilisateur = Depends(require_documents_issue),
):
    """Vérifie l'éligibilité et affiche la future référence, sans rien écrire
    sur le disque. L'administrateur décide ensuite s'il délivre."""

    try:
        document = await emettre_document(
            db,
            etudiant_id=etudiant_id,
            type_code=payload.type_document,
            emis_par_id=acteur.id,
            session_id=payload.session_id,
            reservation=True,
        )
    except DocumentInvalide as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    etudiant = await db.get(Etudiant, etudiant_id)
    return _enrichir(document, etudiant)


@router.post(
    "/lot",
    response_model=LotDocumentResponse,
    summary="Émettre les documents d'une classe ou d'une promotion",
)
async def emettre_lot(
    payload: LotDocumentRequest,
    db: AsyncSession = Depends(get_db),
    acteur: Utilisateur = Depends(require_documents_issue),
):
    """Émet en série. Par défaut, les dossiers non éligibles sont listés sans
    interrompre le lot : une école doit pouvoir sortir 300 certificats même si
    deux étudiants ont un dossier incomplet."""

    if payload.classe_id:
        classe = await db.get(Classe, payload.classe_id)
        if classe is None:
            raise HTTPException(status_code=404, detail="Classe introuvable.")
        stmt = (
            select(Etudiant)
            .join(Inscription, Inscription.etudiant_id == Etudiant.id)
            .where(Inscription.classe_id == classe.id, Inscription.statut == "active")
            .distinct()
        )
    elif payload.session_id:
        stmt = (
            select(Etudiant)
            .join(Inscription, Inscription.etudiant_id == Etudiant.id)
            .where(Inscription.session_id == payload.session_id, Inscription.statut == "active")
            .distinct()
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Indiquez une classe ou une session pour délimiter le lot.",
        )

    etudiants = list((await db.execute(stmt)).scalars().all())
    if not etudiants:
        raise HTTPException(
            status_code=status.HTTP_404,
            detail="Aucun étudiant inscrit dans le périmètre demandé.",
        )

    lignes: List[ResultatLigne] = []
    emis = 0
    echoues = 0
    for etudiant in etudiants:
        try:
            document = await emettre_document(
                db,
                etudiant_id=etudiant.id,
                type_code=payload.type_document,
                emis_par_id=acteur.id,
                session_id=payload.session_id,
            )
            emis += 1
            lignes.append(
                ResultatLigne(
                    etudiant_id=etudiant.id,
                    matricule=etudiant.matricule,
                    nom=f"{etudiant.nom} {etudiant.prenom}".strip(),
                    emis=True,
                    numero=document.numero,
                    document_id=document.id,
                )
            )
        except DocumentInvalide as exc:
            echoues += 1
            lignes.append(
                ResultatLigne(
                    etudiant_id=etudiant.id,
                    matricule=etudiant.matricule,
                    nom=f"{etudiant.nom} {etudiant.prenom}".strip(),
                    emis=False,
                    motif=str(exc),
                )
            )
            if not payload.ignorer_les_non_eligibles:
                break

    return LotDocumentResponse(
        type_document=payload.type_document, emis=emis, echoues=echoues, lignes=lignes
    )


@router.get(
    "/",
    response_model=List[DocumentOfficielListe],
    summary="Historique des documents émis",
)
async def lister_documents(
    etudiant_id: Optional[str] = Query(None),
    type_document: Optional[str] = Query(None),
    limite: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_students_read),
):
    stmt = (
        select(DocumentOfficiel, Etudiant)
        .join(Etudiant, DocumentOfficiel.etudiant_id == Etudiant.id)
        .order_by(DocumentOfficiel.emis_le.desc())
        .limit(limite)
    )
    if etudiant_id:
        stmt = stmt.where(DocumentOfficiel.etudiant_id == etudiant_id)
    if type_document:
        stmt = stmt.where(DocumentOfficiel.type_document == type_document)

    return [_enrichir(document, etudiant) for document, etudiant in (await db.execute(stmt)).all()]


@router.get(
    "/{document_id}/telecharger",
    summary="Télécharger le PDF d'un document",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}, "description": "PDF du document officiel"}},
)
async def telecharger(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_students_read),
):
    """Retourne le PDF émis. Un secretariat doit pouvoir reimprimer."""

    document = await db.get(DocumentOfficiel, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document introuvable.")
    contenu = lire_pdf(document.fichier)
    if contenu is None:
        # La ligne existe mais le fichier a disparu du disque : information
        # exploitable, distinction entre erreur de donnee et absence de fichier.
        logger.error("Fichier manquant pour le document %s (%s)", document.numero, document.fichier)
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=(
                f"Le fichier du document {document.numero} est introuvable sur le "
                "serveur. Réémettez-le en duplicata."
            ),
        )

    etudiant = await db.get(Etudiant, document.etudiant_id)
    nom = (
        f"{document.numero}_{etudiant.matricule if etudiant else 'document'}.pdf"
    )
    return Response(
        content=contenu,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nom}"'},
    )


@router.post(
    "/{document_id}/duplicata",
    response_model=DocumentOfficielListe,
    status_code=status.HTTP_201_CREATED,
    summary="Réémettre un duplicata",
)
async def duplicata(
    document_id: str,
    payload: DuplicataRequest,
    db: AsyncSession = Depends(get_db),
    acteur: Utilisateur = Depends(require_documents_issue),
):
    """Réédite un document détruit ou perdu.

    Le duplicata porte un **nouveau numéro** et l'instantané des données
    actuelles. Le document d'origine reste consultable : c'est ce qui permet
    d'établir ce qui avait été délivré la première fois.
    """

    origine = await db.get(DocumentOfficiel, document_id)
    if origine is None:
        raise HTTPException(status_code=404, detail="Document introuvable.")
    if origine.remplace_document_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce document est déjà un duplicata : émettez-le depuis l'original.",
        )

    motif = payload.motif.strip()
    if not motif:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Le motif est obligatoire."
        )

    try:
        document = await emettre_document(
            db,
            etudiant_id=origine.etudiant_id,
            type_code=origine.type_document,
            emis_par_id=acteur.id,
            session_id=origine.session_id,
            remplace_document_id=origine.id,
            motif_duplicata=motif,
        )
    except DocumentInvalide as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    etudiant = await db.get(Etudiant, origine.etudiant_id)
    return _enrichir(document, etudiant)


@router.post(
    "/{document_id}/delivrance",
    response_model=DocumentOfficielListe,
    summary="Marquer un document comme délivré",
)
async def marquer_delivrance(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_documents_issue),
):
    """Enregistre la remise physique du document. Hors ligne, le document
    reste consultable et réimprimable."""

    document = await db.get(DocumentOfficiel, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document introuvable.")
    if document.delivre_le is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document déjà délivré le {document.delivre_le:%d/%m/%Y}.",
        )
    from datetime import date as _date

    document.delivre_le = _date.today()
    etudiant = await db.get(Etudiant, document.etudiant_id)
    return _enrichir(document, etudiant)


def _enrichir(document: DocumentOfficiel, etudiant: Optional[Etudiant]) -> DocumentOfficielListe:
    """Ajoute l'identite de l'etudiant a la reponse."""

    return DocumentOfficielListe(
        id=document.id,
        type_document=document.type_document,
        numero=document.numero,
        etudiant_id=document.etudiant_id,
        session_id=document.session_id,
        annee=document.annee,
        fichier=document.fichier,
        sha256=document.sha256,
        taille_octets=document.taille_octets,
        donnees=document.donnees or {},
        reserves=document.reserves or [],
        remplace_document_id=document.remplace_document_id,
        motif_duplicata=document.motif_duplicata,
        emis_par_id=document.emis_par_id,
        emis_le=document.emis_le,
        delivre_le=document.delivre_le,
        created_at=document.created_at,
        etudiant_nom=etudiant.nom if etudiant else None,
        etudiant_prenom=etudiant.prenom if etudiant else None,
        etudiant_matricule=etudiant.matricule if etudiant else None,
        libelle=_libelle(document.type_document),
    )
