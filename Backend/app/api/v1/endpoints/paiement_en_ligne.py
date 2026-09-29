"""
Paiements en ligne (lot 4b) : liens de paiement et confirmation.

Deux portes, deux publics :

- **Le personnel** (``finance.read`` / ``finance.write``) : créer un lien
  pour une facture, voir les intentions, annuler un lien encore en
  attente. La réponse de création contient le jeton **en clair, une seule
  fois** : c'est à cet instant que le lien part vers la famille.
- **La famille**, sans compte : ouvrir le lien (résumé de ce qui est dû) et
  confirmer le paiement. La seule clé est le jeton du lien ; la base n'en
  garde que l'empreinte, et le résumé ne révèle rien de plus que ce qu'une
  lettre de relance imprimerait.

En mode ``simulation``, la confirmation produit un ``Paiement`` + ``Recu``
normaux — le guichet suit, sans guichet.
"""

import uuid
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_finance_read, require_finance_write
from app.models.paiement_intent import PaiementIntent
from app.models.utilisateur import Utilisateur
from app.services import paiement_en_ligne_service as service
from app.services.paiement_en_ligne_service import IntentInvalide, IntentMorte

router = APIRouter()


# ---------------------------------------------------------------------------
# Schémas
# ---------------------------------------------------------------------------
class IntentionCreation(BaseModel):
    facture_id: str
    #: Par défaut, le reste à payer de la facture. Un montant saisi ne
    #: dépasse jamais ce reste : un lien n'ouvre pas un crédit.
    montant: Optional[Decimal] = None
    provider: str = "simulation"
    validite_jours: Optional[int] = Field(None, ge=1, le=90)


class IntentionCreee(BaseModel):
    """Le lien, tel que le personnel le reçoit — jeton en clair, une seule fois."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    facture_id: Optional[str]
    etudiant_id: str
    session_id: str
    montant: Decimal
    provider: str
    statut: str
    expires_le: str
    #: L'URL complète à transmettre : le frontend la copie vers la famille.
    lien: str
    token: str


class IntentionListe(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    facture_id: Optional[str]
    etudiant_id: str
    etudiant_nom: Optional[str] = None
    montant: Decimal
    provider: str
    statut: str
    expires_le: str
    paiement_id: Optional[str] = None
    created_at: str


class ResumeFamille(BaseModel):
    etablissement: Optional[str]
    devise: str
    etudiant: Optional[str]
    matricule: Optional[str]
    facture: Optional[dict]
    montant_demande: float
    provider: str
    expire_le: str


class ConfirmationRequete(BaseModel):
    #: La référence que la passerelle (ou la simulation) rapporte. Libre.
    reference: Optional[str] = None


class ConfirmationReponse(BaseModel):
    paiement_id: str
    numero_recu: str
    montant: Decimal
    mode_paiement: str


def _erreur_intention(exc: Exception, *, famille: bool = False) -> HTTPException:
    """Traduit les exceptions du service, sans dire plus qu'il faut.

    Côté famille, « lien inconnu » et « lien expiré » sont le même 410 :
    un attaquant n'a rien à apprendre de la différence. Côté personnel, le
    422 nomme la cause pour corriger la saisie.
    """
    if isinstance(exc, IntentMorte):
        if famille:
            return HTTPException(status_code=410, detail=str(exc))
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=422, detail=str(exc))


def _lien_pour(jeton: str) -> str:
    """L'URL publique du lien de paiement, relative au frontend."""
    return f"/paiement-en-ligne/{jeton}"


# ---------------------------------------------------------------------------
# Porte du personnel
# ---------------------------------------------------------------------------
@router.post(
    "/paiements-en-ligne",
    response_model=IntentionCreee,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un lien de paiement pour une facture",
)
async def creer_lien(
    payload: IntentionCreation,
    db: AsyncSession = Depends(get_db),
    auteur: Utilisateur = Depends(require_finance_write),
):
    """Émet un lien de paiement. Le jeton ne repassera jamais : la base ne
    conserve que son empreinte — transmettez le lien à la famille dès réception."""
    try:
        intention, jeton = await service.creer_intention(
            db,
            facture_id=payload.facture_id,
            montant=payload.montant,
            auteur_id=auteur.id,
            provider=payload.provider,
            validite_jours=payload.validite_jours,
        )
    except IntentInvalide as exc:
        raise _erreur_intention(exc) from exc
    await db.commit()
    await db.refresh(intention)
    return IntentionCreee(
        id=intention.id,
        facture_id=intention.facture_id,
        etudiant_id=intention.etudiant_id,
        session_id=intention.session_id,
        montant=intention.montant,
        provider=intention.provider,
        statut=intention.statut,
        expires_le=intention.expires_le.isoformat(),
        lien=_lien_pour(jeton),
        token=jeton,
    )


@router.get(
    "/paiements-en-ligne",
    response_model=List[IntentionListe],
    summary="Lister les intentions de paiement",
)
async def lister_intentions(
    statut: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_finance_read),
):
    stmt = select(PaiementIntent).order_by(PaiementIntent.created_at.desc()).limit(200)
    if statut:
        stmt = stmt.where(PaiementIntent.statut == statut)
    intentions = (await db.execute(stmt)).scalars().all()
    resultat = []
    for intention in intentions:
        etudiant = intention.etudiant
        resultat.append(
            IntentionListe(
                id=intention.id,
                facture_id=intention.facture_id,
                etudiant_id=intention.etudiant_id,
                etudiant_nom=(
                    f"{etudiant.prenom or ''} {etudiant.nom or ''}".strip() if etudiant else None
                ),
                montant=intention.montant,
                provider=intention.provider,
                statut=intention.statut,
                expires_le=intention.expires_le.isoformat(),
                paiement_id=intention.paiement_id,
                created_at=intention.created_at.isoformat(),
            )
        )
    return resultat


@router.post(
    "/paiements-en-ligne/{intention_id}/annuler",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Annuler un lien de paiement en attente",
)
async def annuler_intention(
    intention_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_finance_write),
):
    intention = await db.get(PaiementIntent, intention_id)
    if intention is None:
        raise HTTPException(status_code=404, detail="Intention introuvable.")
    try:
        await service.annuler(db, intention)
    except IntentInvalide as exc:
        raise _erreur_intention(exc) from exc
    await db.commit()
    return None


# ---------------------------------------------------------------------------
# Porte de la famille : sans compte, gardée par le jeton du lien
# ---------------------------------------------------------------------------
@router.get(
    "/public/paiement/{jeton}",
    response_model=ResumeFamille,
    summary="Résumé d'un lien de paiement (famille)",
)
async def resume_lien(jeton: str, db: AsyncSession = Depends(get_db)):
    """Ce que la famille lit en ouvrant le lien : l'essentiel, rien de plus."""
    try:
        intention = await service.intention_par_jeton(db, jeton)
        resume = await service.resumer_pour_famille(db, intention)
    except IntentMorte as exc:
        raise _erreur_intention(exc, famille=True) from exc
    return ResumeFamille(**resume)


@router.post(
    "/public/paiement/{jeton}/confirmer",
    response_model=ConfirmationReponse,
    summary="Confirmer le paiement (famille)",
)
async def confirmer_paiement(
    jeton: str,
    payload: ConfirmationRequete,
    db: AsyncSession = Depends(get_db),
):
    """Confirme le paiement : Paiement + Recu créés, facture mise à jour.

    Mêmes règles que le guichet — solde vérifié au moment de la
    confirmation, reçu numéroté dans la même séquence. Un lien mort est un
    410, sans détail superflu.
    """
    try:
        paiement = await service.confirmer(db, jeton=jeton, reference=payload.reference)
    except IntentMorte as exc:
        raise _erreur_intention(exc, famille=True) from exc
    except IntentInvalide as exc:
        raise _erreur_intention(exc, famille=True) from exc
    await db.commit()
    await db.refresh(paiement)

    recu = (
        await db.execute(
            select(Recu).where(Recu.paiement_id == paiement.id)
        )
    ).scalars().first()
    return ConfirmationReponse(
        paiement_id=paiement.id,
        numero_recu=recu.numero_recu if recu else "",
        montant=paiement.montant,
        mode_paiement=paiement.mode_paiement,
    )


# Import tardif pour éviter un cycle d'import au chargement du module.
from app.models.finance import Recu  # noqa: E402
