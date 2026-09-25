"""Configuration institutionnelle : identite, logo et historique des versions.

Le menu « Parametrage General » promettait une configuration d'etablissement ;
elle n'existait pas. Ces endpoints la rendent reelle, et versionnee.

Deux droits distincts :

- **consulter** la configuration et le logo (``academic.read``) : un secretaire
  doit voir l'identite quifigurera les documents qu'il emet ;
- **modifier** l'identite et le logo (``institution.settings``) : deliberement
  separe de ``users.manage`` et ``roles.manage``, pour qu'une direction
  preparer le branding sans gerer les comptes.

Une lecture est sans effet de bord : consulter la configuration ne cree pas de
version, sinon l'historique se remplirait de faux changements.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_academic_read, require_permission
from app.core.config import settings
from app.models.utilisateur import Utilisateur
from app.schemas.institution import (
    ConfigurationMajout,
    ConfigurationModifiee,
    ConfigurationOut,
    VersionConfigurationOut,
)
from app.services import branding_service, configuration_service
from app.services.audit_service import record_audit_event
from app.services.configuration_service import (
    charger_etablissement,
    comparer,
    enregistrer_version,
)

logger = logging.getLogger(__name__)
router = APIRouter()

#: Modification de la configuration : permission dediee, sans heritage.
require_institution_settings = require_permission("institution.settings")

#: Lecture : on **reutilise** le guard ``academic.read`` deja declare plutot
#: qu'un checker neuve. Un checker cree ici avec une fenetre legacy vide
#: interdirait aux roles historiques qui ont acces partout ailleurs, ce qui
#: serait une regression. Consulter l'identite institutionnelle est bien une
#: lecture du socle academique : le secretariat doit voir l'identite qu'il va
#: imprimer.
require_institution_read = require_academic_read


def _configuration_out(etablissement, version: int) -> ConfigurationOut:
    # ``logo_present`` separe la configuration du disque : un logo enregistre
    # dont le fichier a disparu ne doit pas laisser croire a un branding actif.
    logo_present = bool(etablissement.logo_url) and (
        branding_service.lire_logo(etablissement.logo_url) is not None
    )
    return ConfigurationOut(
        version=version,
        nom=etablissement.nom,
        sigle=etablissement.sigle,
        adresse=etablissement.adresse,
        telephone=etablissement.telephone,
        email=etablissement.email,
        pays=etablissement.pays,
        devise=etablissement.devise,
        annee_academique_active=etablissement.annee_academique_active,
        logo_present=logo_present,
    )


@router.get(
    "/configuration",
    response_model=ConfigurationOut,
    summary="Consulter la configuration institutionnelle",
)
async def lire_configuration(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_institution_read),
):
    try:
        etablissement = await charger_etablissement(db)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    version = await configuration_service.version_courante(db, etablissement.id)
    return _configuration_out(etablissement, version)


@router.put(
    "/configuration",
    response_model=ConfigurationModifiee,
    summary="Modifier l'identite institutionnelle",
)
async def modifier_configuration(
    payload: ConfigurationMajout,
    db: AsyncSession = Depends(get_db),
    auteur: Utilisateur = Depends(require_institution_settings),
):
    """Enregistre une nouvelle version si l'identite a reellement change.

    Une soumission sans changement ne cree pas de version : l'historique ne
    doit contenir que des changements reels, sans quoi il ne prouve plus rien.
    """

    try:
        etablissement = await charger_etablissement(db)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    changement = payload.model_dump(exclude_none=True)
    if not changement:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Aucun champ a modifier.",
        )

    modifications = comparer(etablissement, changement)
    if not modifications:
        version = await configuration_service.version_courante(db, etablissement.id)
        return ConfigurationModifiee(
            configuration=_configuration_out(etablissement, version),
            version=version,
            modifications={},
        )

    for champ, detail in modifications.items():
        setattr(etablissement, champ, detail["apres"])

    version = await enregistrer_version(
        db, etablissement, nature="etablissement", modifications=modifications, auteur=auteur
    )
    await record_audit_event(
        db,
        actor_id=auteur.id,
        actor_email=auteur.email,
        action="institution.configuration.updated",
        resource_type="etablissement",
        resource_id=etablissement.id,
        details={"version": version.version, "champs": list(modifications)},
    )
    await db.commit()
    await db.refresh(etablissement)

    return ConfigurationModifiee(
        configuration=_configuration_out(etablissement, version.version),
        version=version.version,
        modifications=modifications,
    )


@router.post(
    "/logo",
    response_model=ConfigurationModifiee,
    summary="Televerser le logo de l'etablissement",
)
async def televerser_logo(
    db: AsyncSession = Depends(get_db),
    auteur: Utilisateur = Depends(require_institution_settings),
    fichier: UploadFile = File(..., description="Logo PNG ou JPEG (512 Ko maximum)."),
):
    """Remplace le logo et enregistre une version.

    Le format est reconnu sur les **octets**, pas d'apres le nom ou le type
    annonce par le navigateur : un fichier qui n'est pas une image est refuse,
    et jamais ecrit sur le disque.
    """

    try:
        etablissement = await charger_etablissement(db)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    contenu = await fichier.read()
    try:
        extension, largeur, hauteur = branding_service.valider_logo(contenu)
    except branding_service.LogoInvalide as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    ancien = etablissement.logo_url
    etablissement.logo_url = branding_service.ecrire_logo(contenu, extension)

    modifications = {
        "logo": {
            "avant": "present" if ancien else "absent",
            "apres": "present",
        }
    }
    version = await enregistrer_version(
        db, etablissement, nature="branding", modifications=modifications, auteur=auteur
    )

    # Le fichier precedent n'est supprime qu'apres le commit : avant, un echec
    # d'ecriture laisserait l'etablissement sans logo alors que la base
    # indique encore l'ancien chemin.
    await record_audit_event(
        db,
        actor_id=auteur.id,
        actor_email=auteur.email,
        action="institution.logo.uploaded",
        resource_type="etablissement",
        resource_id=etablissement.id,
        details={
            "version": version.version,
            "format": extension,
            "dimensions": f"{largeur}x{hauteur}",
            "taille": len(contenu),
        },
    )
    await db.commit()
    await db.refresh(etablissement)

    if ancien and ancien != etablissement.logo_url:
        branding_service.supprimer_logo(ancien)

    return ConfigurationModifiee(
        configuration=_configuration_out(etablissement, version.version),
        version=version.version,
        modifications=modifications,
    )


@router.delete(
    "/logo",
    response_model=ConfigurationModifiee,
    summary="Retirer le logo de l'etablissement",
)
async def retirer_logo(
    db: AsyncSession = Depends(get_db),
    auteur: Utilisateur = Depends(require_institution_settings),
):
    try:
        etablissement = await charger_etablissement(db)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not etablissement.logo_url:
        version = await configuration_service.version_courante(db, etablissement.id)
        return ConfigurationModifiee(
            configuration=_configuration_out(etablissement, version),
            version=version,
            modifications={},
        )

    ancien = etablissement.logo_url
    etablissement.logo_url = None
    modifications = {"logo": {"avant": "present", "apres": "absent"}}
    version = await enregistrer_version(
        db, etablissement, nature="branding", modifications=modifications, auteur=auteur
    )
    await record_audit_event(
        db,
        actor_id=auteur.id,
        actor_email=auteur.email,
        action="institution.logo.removed",
        resource_type="etablissement",
        resource_id=etablissement.id,
        details={"version": version.version},
    )
    await db.commit()
    await db.refresh(etablissement)

    branding_service.supprimer_logo(ancien)

    return ConfigurationModifiee(
        configuration=_configuration_out(etablissement, version.version),
        version=version.version,
        modifications=modifications,
    )


@router.get(
    "/logo",
    summary="Recuperer le logo de l'etablissement",
    responses={200: {"content": {"image/png": {}}, "description": "Logo enregistre."}},
)
async def recuperer_logo(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_institution_read),
):
    """Servit le logo. 404 s'il n'y en a pas — c'est un etat normal.

    Un ``<img src>`` ne peut pas distinguer « pas de logo » d'une erreur : le
    404 est donc la reponse correcte, et l'ecran affiche son etat vide.
    """

    try:
        etablissement = await charger_etablissement(db)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not etablissement.logo_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun logo n'est enregistre pour cet etablissement.",
        )

    lu = branding_service.lire_logo(etablissement.logo_url)
    if lu is None:
        # La configuration annonce un logo mais le fichier a disparu : c'est
        # un incident de stockage, pas une absence de logo. Le dire evite de
        # laisser croire a un branding actif.
        logger.warning(
            "Logo enregistre introuvable pour l'etablissement %s : %s",
            etablissement.id,
            etablissement.logo_url,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Un logo est enregistre mais son fichier est introuvable. "
                "Renvoyez le logo depuis le parametrage."
            ),
        )

    contenu, type_mime = lu
    return Response(
        content=contenu,
        media_type=type_mime,
        headers={"Cache-Control": "private, max-age=300"},
    )


@router.get(
    "/versions",
    response_model=List[VersionConfigurationOut],
    summary="Historique des versions de la configuration",
)
async def lister_versions(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_institution_read),
    limite: int = 50,
):
    try:
        etablissement = await charger_etablissement(db)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return await configuration_service.historique(db, etablissement.id, limite=limite)
