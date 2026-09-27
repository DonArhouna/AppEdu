"""Endpoint d'export de la liste des etudiants.

Le filtre de classe est **optionnel** : l'export de tous les etudiants est un
usage legitime, et le restreindre a une classe serait une perte de fonction.

L'export est une lecture : il exige ``academic.read``, pas un droit d'ecriture.
Aucun etat n'est modifie, donc exiger davantage serait une entrave sans motif.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, require_academic_read
from app.models.academic import Classe
from app.models.etudiant import Etudiant
from app.services import export_service

logger = logging.getLogger(__name__)
router = APIRouter()

FORMATS = {"xlsx", "csv"}


async def _etudiants(
    db: AsyncSession,
    *,
    classe_id: Optional[str],
    filiere: Optional[str],
    session_id: Optional[str],
) -> List[Etudiant]:
    stmt = (
        select(Etudiant)
        .options(
            selectinload(Etudiant.classe),
            selectinload(Etudiant.session),
        )
        .order_by(Etudiant.nom, Etudiant.prenom, Etudiant.matricule)
    )
    if classe_id:
        stmt = stmt.where(Etudiant.classe_id == classe_id)
    if filiere:
        stmt = stmt.where(Etudiant.filiere == filiere)
    if session_id:
        stmt = stmt.where(Etudiant.session_id == session_id)
    return list((await db.execute(stmt)).scalars().all())


@router.get(
    "/export",
    summary="Exporter la liste des etudiants",
    responses={
        200: {
            "content": {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {},
                "text/csv": {},
            }
        }
    },
)
async def exporter_etudiants(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_read),
    classe_id: Optional[str] = Query(None, description="Restreindre a une classe."),
    filiere: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
    format: str = Query("xlsx", description="xlsx ou csv"),
):
    """Genere le fichier d'export.

    Le contenu vient de la base, avec les memes filtres que l'ecran, mais
    **sans pagination** : un institut qui exporte sa promotion veut tous ses
    eleves, pas la page qu'il était en train de regarder.
    """

    if format not in FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Format inconnu : {format!r}. Formats acceptés : "
            f"{', '.join(sorted(FORMATS))}.",
        )

    classe = None
    if classe_id:
        classe = await db.get(Classe, classe_id)
        if classe is None:
            # Un 404 plutot qu'un fichier vide : un classeur sans ligne pour
            # une classe inexistante se lirait « cette classe est vide ».
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cette classe n'existe pas. Vérifiez qu'elle n'a pas été "
                "supprimée depuis l'ouverture de la liste.",
            )

    etudiants = await _etudiants(
        db, classe_id=classe_id, filiere=filiere, session_id=session_id
    )

    nom = export_service.nom_fichier(
        classe=classe.nom if classe is not None else None, format_=format
    )

    if format == "csv":
        contenu = export_service.vers_csv(etudiants)
        media = "text/csv; charset=utf-8"
    else:
        contenu = export_service.vers_xlsx(
            etudiants,
            titre=classe.nom if classe is not None else "Tous les étudiants",
        )
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    # Le nombre d'etudiants est expose : l'institut peut verifier d'un coup
    # d'oeil qu'il a bien exporte toute la promotion.
    return Response(
        content=contenu,
        media_type=media,
        headers={
            "Content-Disposition": f'attachment; filename="{nom}"',
            "X-Export-Etudiants": str(len(etudiants)),
        },
    )


__all__ = ["router"]
