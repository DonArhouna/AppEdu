"""Relances de facturation : suivi des creances et journal des relances.

Ce module complete la balance agee, qui **calcule** les creances en retard,
par ce qui permet de **agir** et de **se souvenir** :

- ``GET /finances/relances`` : qui relancer, et de combien ;
- ``POST /finances/relances`` : constater une relance faite ;
- ``GET /finances/relances/historique`` : ce qui a deja ete fait ;
- ``POST /finances/relances/{niveau}/solde`` : constater qu'un encaissement a
  suivi.

La lecture exige ``finance.read``, l'ecriture ``finance.write`` : relancer
un etudiant est un acte de recouvrement, pas une consultation. La separation
est celle du reste du module finances.

Aucun envoi automatique. L'application n'a aucune identite de messagerie, et
pretendre contacter l'etudiant serait faux : la relance est un acte du
secretariat, constate ici.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_finance_read, require_finance_write
from app.models.etablissement import Etablissement
from app.models.relance import Relance
from app.models.utilisateur import Utilisateur
from app.schemas.relance import (
    ARelancer,
    CreanceEtudiant,
    RelanceAnterieure,
    RelanceCreation,
    RelanceEnregistree,
    RelanceOut,
    SoldeSuivi,
    SyntheseRelances,
)
from app.services import relance_service as service
from app.services.relance_pdf import rendre_lettre
from app.services.audit_service import record_audit_event
from app.services.relance_service import RelanceInvalide

logger = logging.getLogger(__name__)
router = APIRouter()


def _erreur(cause: RelanceInvalide) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(cause)
    )


def _relance_out(relance: Relance) -> RelanceOut:
    factures = list(relance.factures_concernees or [])
    return RelanceOut(
        id=relance.id,
        etudiant_id=relance.etudiant_id,
        matricule=relance.etudiant.matricule if relance.etudiant else None,
        nom=relance.etudiant.nom if relance.etudiant else None,
        prenom=relance.etudiant.prenom if relance.etudiant else None,
        session_id=relance.session_id,
        niveau=relance.niveau,
        date_relance=relance.date_relance,
        moyen=relance.moyen,
        montant_reclame=relance.montant_reclame,
        retard_jours=relance.retard_jours,
        message=relance.message,
        solde_apres=relance.solde_apres,
        relance_par_email=relance.auteur.email if relance.auteur else None,
        created_at=relance.created_at,
        nb_factures=len(factures),
        factures_concernees=factures,
        email_statut=relance.email_statut,
        email_envoye_le=relance.email_envoye_le,
        resolue=relance.resolue,
    )


@router.get(
    "/relances",
    response_model=SyntheseRelances,
    summary="Creances en retard a suivre, et leur anciennete",
)
async def lister_a_relancer(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_finance_read),
    session_id: Optional[str] = Query(None, description="Restreindre a une session."),
    retard_minimum: int = Query(
        1, ge=0, le=3650, description="Jours de retard minimaux (1 = facture echue)."
    ),
):
    """Detruit les creances en retard, du plus ancien retard au plus recent.

    ``retard_minimum`` vaut 1 par defaut : une facture echue **aujourd'hui**
    n'a pas de retard, et relancer le jour de l'echeance serait
    injustifiable — le versement peut encore arriver le jour meme.
    """

    elements = await service.a_relancer(
        db, session_id=session_id, retard_minimum=retard_minimum
    )

    items: List[ARelancer] = []
    for element in elements:
        etudiant = element["etudiant"]
        items.append(
            ARelancer(
                etudiant_id=etudiant.id,
                matricule=etudiant.matricule,
                nom=etudiant.nom,
                prenom=etudiant.prenom,
                filiere=etudiant.filiere,
                telephone=etudiant.telephone,
                email=etudiant.email,
                creances=[CreanceEtudiant(**creance) for creance in element["creances"]],
                nb_creances=element["nb_creances"],
                total_du=element["total_du"],
                retard_jours=element["retard_jours"],
                anciennete_jours=element["anciennete_jours"],
                niveau_suivant=element["niveau_suivant"],
                nb_relances=element["nb_relances"],
                derniere_relance=(
                    RelanceAnterieure.model_validate(element["derniere_relance"])
                    if element["derniere_relance"]
                    else None
                ),
                jours_depuis_derniere=element["jours_depuis_derniere"],
            )
        )

    # Paliers alignes sur la balance agee : les deux vues doivent concorder.
    retard_1_30 = round(
        sum(e["total_du"] for e in elements if 1 <= e["retard_jours"] <= 30), 2
    )
    retard_31_60 = round(
        sum(e["total_du"] for e in elements if 31 <= e["retard_jours"] <= 60), 2
    )
    retard_plus_60 = round(
        sum(e["total_du"] for e in elements if e["retard_jours"] > 60), 2
    )
    etablissement = (await db.execute(select(Etablissement).limit(1))).scalars().first()

    return SyntheseRelances(
        date_calcul=date.today(),
        devise=etablissement.devise if etablissement else "",
        nb_etudiants=len(items),
        nb_creances=sum(item.nb_creances for item in items),
        total_du=round(sum(item.total_du for item in items), 2),
        retard_1_30=retard_1_30,
        retard_31_60=retard_31_60,
        retard_plus_60=retard_plus_60,
        items=items,
    )


@router.get(
    "/relances/historique",
    response_model=List[RelanceOut],
    summary="Historique des relances effectuees",
)
async def lister_historique(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_finance_read),
    etudiant_id: Optional[str] = Query(None),
    limite: int = Query(100, ge=1, le=1000),
):
    relances = await service.historique(db, etudiant_id=etudiant_id, limite=limite)
    return [_relance_out(relance) for relance in relances]


@router.post(
    "/relances",
    response_model=RelanceEnregistree,
    status_code=status.HTTP_201_CREATED,
    summary="Constater une relance effectuee",
)
async def constater_relance(
    payload: RelanceCreation,
    db: AsyncSession = Depends(get_db),
    auteur: Utilisateur = Depends(require_finance_write),
):
    """Consigne une relance et fige ce qui etait reclame ce jour-la.

    Le montant et le detail des factures sont **copies**, pas references : une
    facture soldee depuis ne doit pas reecrire ce que le secretariat a
    reclame. Refuser une relance sans creance evite d'enregistrer un acte
    dans le vide.
    """

    try:
        relance, resume = await service.enregistrer_relance(
            db,
            etudiant_id=payload.etudiant_id,
            moyen=payload.moyen,
            date_relance=payload.date_relance or date.today(),
            session_id=payload.session_id,
            message=payload.message,
            auteur_id=auteur.id,
        )
    except RelanceInvalide as exc:
        await db.rollback()
        raise _erreur(exc) from exc

    await record_audit_event(
        db,
        actor_id=auteur.id,
        actor_email=auteur.email,
        action="finance.relance.recorded",
        resource_type="relance",
        resource_id=relance.id,
        details={
            "etudiant_id": payload.etudiant_id,
            "niveau": relance.niveau,
            # Le journal d'audit est une colonne JSON : un Decimal n'y est pas
            # representable, le montant part en flottant d'affichage.
            "montant": float(relance.montant_reclame),
            "moyen": relance.moyen,
            "retard_jours": relance.retard_jours,
        },
    )
    await db.commit()
    await db.refresh(relance)

    return RelanceEnregistree(relance=_relance_out(relance), resume=resume)


@router.post(
    "/relances/solde",
    response_model=SoldeSuivi,
    summary="Constater le solde apres une relance",
)
async def constater_solde(
    db: AsyncSession = Depends(get_db),
    auteur: Utilisateur = Depends(require_finance_write),
    etudiant_id: str = Query(..., min_length=1),
    niveau: int = Query(..., ge=1),
):
    """Renseigne le solde constate apres une relance.

    Appele apres un encaissement : c'est ce qui distingue une relance
    efficace d'une relance restee sans effet. Le solde est **fige** a ce
    moment-la — un paiement ulterieur ne doit pas retroagir sur le passe.
    """

    relances = await service.solder_suivi(
        db, etudiant_id=etudiant_id, niveau=niveau, auteur_id=auteur.id
    )
    if not relances:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Aucune relance de niveau {niveau} n'est enregistree pour cet "
                "étudiant."
            ),
        )
    solde = relances[0].solde_apres if relances[0].solde_apres is not None else Decimal("0.00")

    await record_audit_event(
        db,
        actor_id=auteur.id,
        actor_email=auteur.email,
        action="finance.relance.settled",
        resource_type="relance",
        resource_id=relances[0].id,
        # JSON n'a pas de decimal : l'audit flotte, la relance ne flotte pas.
        details={"etudiant_id": etudiant_id, "niveau": niveau, "solde_apres": float(solde)},
    )
    await db.commit()

    return SoldeSuivi(
        etudiant_id=etudiant_id,
        niveau=niveau,
        solde_apres=solde,
        nb_relances_concernees=len(relances),
    )


@router.get(
    "/relances/moyens",
    response_model=List[str],
    summary="Moyens de relance disponibles",
)
async def lister_moyens(_auth=Depends(require_finance_read)):
    """Liste fermee des moyens constates.

    Une saisie libre diverge des le premier synonymes et rend l'historique
    illisible. Le libelle vient du serveur, l'ecran n'en invente pas.
    """

    return list(service.MOYENS)


@router.get(
    "/relances/{relance_id}/lettre",
    summary="Lettre de relance imprimable",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def lettre_de_relance(
    relance_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_finance_read),
):
    """Genere la lettre a remettre ou a envoyer a l'etudiant.

    La lettre rend l'**instantane** fige a la relance : elle dit ce qui a ete
    reclame ce jour-la, pas le solde du moment ou l'on imprime. Un encaissement
    survenu entre-temps ne doit pas faire dire a la lettre autre chose que ce
    qui a ete remis.

    Elle n'est pas un document officiel et ne figure donc pas au registre
    d'emission : c'est une demande de reglement, pas une attestation.
    """

    relance = await db.get(Relance, relance_id)
    if relance is None:
        raise HTTPException(
            status_code=404,
            detail="Aucune relance à cet identifiant. Générez-la depuis l'écran "
                   "avant de chercher sa lettre.",
        )

    etablissement = (await db.execute(select(Etablissement).limit(1))).scalars().first()
    contenu, nom_fichier = await rendre_lettre(
        db, relance=relance, etablissement=etablissement
    )

    return Response(
        content=contenu,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nom_fichier}"'},
    )


@router.post(
    "/relances/{relance_id}/envoyer-email",
    response_model=RelanceOut,
    summary="Envoyer la lettre de relance par email",
)
async def envoyer_lettre_email(
    relance_id: str,
    db: AsyncSession = Depends(get_db),
    auteur: Utilisateur = Depends(require_finance_write),
):
    """Envoie la lettre de relance (PDF) à l'étudiant, par email.

    Un acte **explicite** du secrétariat, jamais automatique : rien ne part
    sans qu'on ait cliqué. Le résultat est consigné **sur la relance** :
    ``envoye`` (parti), ``simule`` (SMTP non configuré — l'application le
    dit, elle ne prétend pas avoir contacté l'étudiant) ou ``echec``
    (serveur de courrier injoignable, à retenter).

    Un étudiant sans adresse email est un refus nommé (422) : la relance a
    un autre moyen, la lettre imprimable reste disponible.
    """

    relance = await db.get(Relance, relance_id)
    if relance is None:
        raise HTTPException(status_code=404, detail="Aucune relance à cet identifiant.")
    etudiant = relance.etudiant
    if etudiant is None or not (etudiant.email or "").strip():
        raise HTTPException(
            status_code=422,
            detail=(
                "Cet étudiant n'a pas d'adresse email enregistrée. Complétez sa "
                "fiche, ou remettez la lettre imprimable par un autre moyen."
            ),
        )

    etablissement = (await db.execute(select(Etablissement).limit(1))).scalars().first()
    contenu, nom_fichier = await rendre_lettre(
        db, relance=relance, etablissement=etablissement
    )

    from app.services import email_service

    devise = etablissement.devise if etablissement else ""
    texte = (
        f"Bonjour {etudiant.prenom or ''} {etudiant.nom or ''},\n\n"
        "Veuillez trouver en pièce jointe la lettre de relance concernant "
        "vos frais de scolarité.\n\n"
        f"Montant réclamé : {relance.montant_reclame} {devise}.\n\n"
        "Le service comptabilité."
    )
    resultat = await email_service.envoyer_email(
        destinataire=etudiant.email.strip(),
        sujet=f"Lettre de relance niveau {relance.niveau} — frais de scolarité",
        corps_texte=texte,
        pieces_jointes=[(nom_fichier, contenu, "application/pdf")],
    )

    from datetime import datetime, timezone

    relance.email_envoye_le = datetime.now(timezone.utc)
    relance.email_statut = resultat.statut
    await record_audit_event(
        db,
        actor_id=auteur.id,
        actor_email=auteur.email,
        action="finance.relance.email",
        resource_type="relance",
        resource_id=relance.id,
        outcome=resultat.statut if resultat.statut != "simule" else "success",
        reason=resultat.detail,
        details={
            "destinataire": etudiant.email.strip(),
            "statut": resultat.statut,
            "pieces_jointes": resultat.pieces_jointes,
        },
    )
    await db.commit()
    await db.refresh(relance)

    if not resultat.parti:
        raise HTTPException(
            status_code=502,
            detail=(
                f"L'envoi a échoué ({resultat.detail}). La relance est enregistrée, "
                "la lettre reste imprimable : réessayez plus tard."
            ),
        )

    return _relance_out(relance)


__all__ = ["router"]
