"""
Import massif d'etudiants : analyse, validation, suivi des lots.

Toutes les routes exigent ``students.write`` (guard dynamique, cf.
``_GUARD_SPECS``) ou ``students.read`` pour la consultation de l'historique.

Le parcours est volontairement en deux temps : l'admin depose un fichier, lit
un rapport ligne a ligne, puis valide.  Rien n'est ecrit dans ``etudiants``
avant cette validation explicite.
"""

import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_students_read, require_students_write
from app.models.etudiant_import import (
    STATUT_ANALYSE,
    STATUT_ANNULE,
    STATUT_ERREUR,
    STATUT_TERMINE,
    EtudiantImportBatch,
    EtudiantImportRow,
)
from app.models.utilisateur import Utilisateur
from app.schemas.etudiant_import import (
    AnalyseEtudiantsResponse,
    AnalyseLigne,
    ColonneImport,
    EtudiantImportBatchDetail,
    EtudiantImportBatchOut,
    EtudiantImportRowOut,
    ModeleImportResponse,
    ValidationImportResponse,
)
from app.services.etudiant_import_service import (
    COLONNES_MODELE,
    ImportFormatInvalide,
    analyse,
    modele_colonnes,
    valider,
)

logger = logging.getLogger(__name__)

router = APIRouter()

#: En-tetes du fichier, dans l'ordre du modele.
_ENTETES_MODELE = ",".join(colonne for colonne, *_ in COLONNES_MODELE)


@router.get(
    "/modele",
    response_model=ModeleImportResponse,
    summary="Contrat du fichier d'import attendu",
)
async def get_modele(
    _auth=Depends(require_students_read),
):
    """Décrit les colonnes attendues. Aucune donnée d'étudiant n'est fournie."""

    return ModeleImportResponse(
        nom_fichier_suggere="import-etudiants.csv",
        formats_acceptes=["csv", "xlsx"],
        encodage="UTF-8 (avec ou sans BOM). CSV séparé par « ; » ou « , ».",
        separateurs_csv=[";", ",", "tabulation"],
        colonnes=modele_colonnes(),
        notes=[
            "Seules les colonnes « nom » et « prénom » sont obligatoires.",
            "Une filière, une session ou une classe inconnue produit une erreur "
            "de ligne : l'import ne crée jamais de référentiel.",
            "Une classe exige une session sur la même ligne.",
            "« matricule » vide : le matricule est généré automatiquement au "
            "moment de la validation.",
            "En mode « mise à jour », une ligne dont le matricule ou l'email "
            "existe déjà modifie le dossier au lieu d'en créer un nouveau.",
        ],
    )


@router.get(
    "/modele.csv",
    response_class=PlainTextResponse,
    summary="Fichier CSV modèle (en-têtes uniquement)",
)
async def get_modele_csv(
    _auth=Depends(require_students_read),
):
    """En-têtes du modèle. Aucune ligne d'exemple : le fichier reste vide de
    toute donnée métier, conformément à la règle « aucun exemple fictif »."""

    return PlainTextResponse(
        content=_ENTETES_MODELE + "\n",
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="import-etudiants.csv"'},
    )


@router.post(
    "/analyse",
    response_model=AnalyseEtudiantsResponse,
    summary="Analyser un fichier d'étudiants (dry-run)",
)
async def analyser_fichier(
    fichier: UploadFile = File(..., description="Fichier .csv ou .xlsx"),
    mode: str = Form("creation", description="creation ou mise_a_jour"),
    db: AsyncSession = Depends(get_db),
    _auth: Utilisateur = Depends(require_students_write),
):
    """Lit et valide le fichier, et enregistre son rapport.

    **Aucune écriture métier.** L'import n'est déclenché que par
    ``POST /etudiants/import/{batch_id}/valider``.
    """

    if mode not in ("creation", "mise_a_jour"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Mode invalide : utilisez « creation » ou « mise_a_jour ».",
        )
    raw = await fichier.read()
    try:
        batch, rows = await analyse(
            db,
            filename=fichier.filename or "import.csv",
            raw=raw,
            mode=mode,
            created_by_id=_auth.id,
        )
    except ImportFormatInvalide as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    colonnes = batch.colonnes or {}
    return AnalyseEtudiantsResponse(
        batch_id=batch.id,
        nom_fichier=batch.nom_fichier,
        format_source=batch.format_source,
        statut=batch.statut,
        mode=mode,
        nb_lignes=batch.nb_lignes,
        nb_creer=batch.nb_creer,
        nb_mettre_a_jour=batch.nb_mettre_a_jour,
        nb_erreurs=batch.nb_erreurs,
        nb_avertissements=batch.nb_avertissements,
        nb_ignorees=batch.nb_ignorees,
        colonnes_reconnues=[
            ColonneImport(source=item.split(" → ")[0], cible=item.split(" → ")[-1])
            for item in colonnes.get("reconnues", [])
        ],
        colonnes_ignorees=list(colonnes.get("ignorees", [])),
        champs_obligatoires_manquants=[],
        lignes=[
            AnalyseLigne(
                ligne=row.ligne,
                statut=row.statut,
                action=row.action,
                matricule=row.donnees.get("matricule") or row.matricule,
                nom=row.donnees.get("nom"),
                prenom=row.donnees.get("prenom"),
                filiere=row.donnees.get("filiere"),
                niveau=row.donnees.get("niveau"),
                email=row.donnees.get("email"),
                erreurs=list(row.erreurs or []),
                avertissements=list(row.avertissements or []),
            )
            for row in rows
        ],
    )


@router.get(
    "/",
    response_model=List[EtudiantImportBatchOut],
    summary="Historique des imports",
)
async def lister_lots(
    limite: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_students_read),
):
    result = await db.execute(
        select(EtudiantImportBatch)
        .order_by(EtudiantImportBatch.created_at.desc())
        .limit(limite)
    )
    return list(result.scalars().all())


@router.get(
    "/{batch_id}",
    response_model=EtudiantImportBatchDetail,
    summary="Détail d'un lot et de ses lignes",
)
async def get_lot(
    batch_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_students_read),
):
    batch = await db.get(EtudiantImportBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Lot d'import introuvable.")
    return batch


@router.post(
    "/{batch_id}/valider",
    response_model=ValidationImportResponse,
    summary="Valider l'import (écrit les lignes valides)",
)
async def valider_lot(
    batch_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: Utilisateur = Depends(require_students_write),
):
    """Écrit les lignes valides du lot. Idempotent : rejouer ne duplique rien."""

    batch = await db.get(EtudiantImportBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Lot d'import introuvable.")
    if batch.statut == STATUT_ANNULE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce lot a été annulé : il ne peut plus être validé.",
        )
    if batch.statut == STATUT_TERMINE:
        return ValidationImportResponse(
            batch_id=batch.id,
            statut=batch.statut,
            nb_importes=batch.nb_importes,
            nb_mises_a_jour=0,
            nb_erreurs=batch.nb_erreurs,
            nb_ignorees=batch.nb_ignorees,
            lignes=[],
            message="Lot déjà validé : aucun nouvel import n'a été effectué.",
        )

    result = await db.execute(
        select(EtudiantImportRow).where(EtudiantImportRow.batch_id == batch_id)
    )
    rows = list(result.scalars().all())
    try:
        bilan = await valider(db, batch, rows)
    except Exception:
        # La transaction est annulee par ``get_db`` : on journalise le detail
        # technique cote serveur et on renvoie un message generique, sans fuite.
        logger.exception("Echec de la validation du lot d'import %s", batch_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "L'import a échoué et a été annulé : aucune donnée n'a été "
                "écrite. Consultez les journaux du serveur."
            ),
        )

    return ValidationImportResponse(
        batch_id=batch.id,
        statut=batch.statut,
        nb_importes=bilan["importes"],
        nb_mises_a_jour=bilan["mises_a_jour"],
        nb_erreurs=sum(1 for row in rows if row.statut == "erreur"),
        nb_ignorees=sum(1 for row in rows if row.statut == "ignore"),
        lignes=bilan["resultats"],
        message=(
            "Import terminé. Les lignes en erreur n'ont pas été enregistrées : "
            "corrigez le fichier et relancez une analyse."
            if bilan["importes"] == 0 and bilan["mises_a_jour"] == 0
            else None
        ),
    )


@router.post(
    "/{batch_id}/annuler",
    response_model=EtudiantImportBatchOut,
    summary="Annuler un lot analysé",
)
async def annuler_lot(
    batch_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: Utilisateur = Depends(require_students_write),
):
    """Annule un lot non validé. Un lot déjà validé reste consultable."""

    batch = await db.get(EtudiantImportBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Lot d'import introuvable.")
    if batch.statut == STATUT_TERMINE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un lot déjà validé ne peut pas être annulé.",
        )
    batch.statut = STATUT_ANNULE
    batch.message = "Annulé avant validation."
    return batch
