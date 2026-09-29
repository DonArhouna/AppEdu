"""
Paiements en ligne (lot 4b) : intention de paiement et confirmation.

Le processus est un guichet différé, en deux temps :

1. **L'intention.** Le secrétariat (``finance.write``) crée un lien de
   paiement pour une facture, pour un montant figé. Le lien contient un
   jeton aléatoire ; la base n'en conserve que l'empreinte SHA-256. Le lien
   complet ne vit que dans la réponse de création : c'est à cet instant que
   le secrétariat le transmet à la famille.
2. **La confirmation.** La famille ouvre le lien : elle lit le résumé —
   établissement, élève, facture, reste à payer — et paie. La confirmation
   transforme l'intention en ``Paiement`` + ``Recu``, par les **mêmes règles
   que le guichet** : solde vérifié, facture mise à jour, reçu numéroté.
   Aucun montant n'est inventé ici : la passerelle confirmera un jour le
   montant qu'elle a encaissé ; en simulation, c'est le montant de
   l'intention.

Le **mode simulation** (provider ``simulation``) est assumé : tant qu'aucun
compte marchand n'est branché, la confirmation se comporte comme le retour
d'une passerelle — c'est elle qui permet de tester tout le parcours sans
rien inventer du vrai monde. Brancher Wave ou Orange Money reviendra à
remplacer la fonction de confirmation, pas à reconstruire le module.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.etablissement import Etablissement
from app.models.finance import Facture, Paiement, Recu
from app.models.paiement_intent import (
    INTENT_ANNULEE,
    INTENT_CONFIRMEE,
    INTENT_EN_ATTENTE,
    INTENT_EXPIREE,
    PaiementIntent,
)


class IntentInvalide(Exception):
    """L'intention demandée ne peut pas exister : le message dit pourquoi."""


class IntentMorte(Exception):
    """L'intention existe mais n'accepte plus de paiement (annulée, expirée,
    déjà payée). Le message est sûr à afficher à la famille."""


def empreinte(jeton: str) -> str:
    """L'empreinte SHA-256 d'un jeton de lien — ce que la base conserve."""
    return hashlib.sha256(jeton.encode("utf-8")).hexdigest()


def _maintenant() -> datetime:
    return datetime.now(timezone.utc)


def _vers_utc(valeur: datetime) -> datetime:
    """Compare des horodatages heterogenes (SQLite rend du naive)."""
    if valeur.tzinfo is None:
        return valeur.replace(tzinfo=timezone.utc)
    return valeur.astimezone(timezone.utc)


def jours_validite() -> int:
    """La durée de vie d'un lien de paiement, en jours (réglage)."""
    return max(1, getattr(settings, "PAYMENT_LINK_VALIDITY_DAYS", 7))


async def creer_intention(
    db: AsyncSession,
    *,
    facture_id: str,
    montant: Optional[Decimal],
    auteur_id: int,
    provider: str = "simulation",
    validite_jours: Optional[int] = None,
) -> Tuple[PaiementIntent, str]:
    """Crée une intention de paiement et rend (intention, jeton_en_clair).

    Le montant est celui du **reste à payer** par défaut — jamais un montant
    saisi à la main sans borne : un lien de paiement n'ouvre pas un crédit.
    Le jeton est rendu une fois, en clair, à l'appelant ; la base ne garde
    que son empreinte.
    """
    facture = await db.get(Facture, facture_id)
    if facture is None:
        raise IntentInvalide("Facture introuvable.")
    if facture.statut == "payee":
        raise IntentInvalide("Cette facture est déjà entièrement payée.")
    reste = facture.reste_a_payer
    if reste <= 0:
        raise IntentInvalide("Cette facture n'a plus de solde à régler.")

    if montant is None:
        montant = reste
    montant = Decimal(montant).quantize(Decimal("0.01"))
    if montant <= 0:
        raise IntentInvalide("Le montant du lien doit être positif.")
    if montant > reste:
        raise IntentInvalide(
            f"Le montant demandé ({montant}) dépasse le reste à payer de la "
            f"facture ({reste})."
        )

    jeton = secrets.token_urlsafe(32)
    intention = PaiementIntent(
        id=str(uuid.uuid4()),
        facture_id=facture.id,
        etudiant_id=facture.etudiant_id,
        session_id=facture.session_id,
        montant=montant,
        token_hash=empreinte(jeton),
        statut=INTENT_EN_ATTENTE,
        provider=provider or "simulation",
        expires_le=_maintenant() + timedelta(days=validite_jours or jours_validite()),
        creee_par_id=auteur_id,
    )
    db.add(intention)
    await db.flush()
    return intention, jeton


async def intention_par_jeton(db: AsyncSession, jeton: str) -> PaiementIntent:
    """L'intention vivante que ce jeton désigne, ou l'exception qui dit pourquoi non.

    Trois issues, deux messages : inconnue (« lien inconnu »), morte
    (annulée, déjà payée ou expirée — même raison affichée, la famille n'a
    pas à démêler laquelle).
    """
    if not jeton or not jeton.strip():
        raise IntentMorte("Lien inconnu.")
    ligne = (
        await db.execute(
            select(PaiementIntent).where(PaiementIntent.token_hash == empreinte(jeton.strip()))
        )
    ).scalars().first()
    if ligne is None:
        raise IntentMorte("Lien inconnu.")
    if ligne.statut == INTENT_CONFIRMEE:
        raise IntentMorte("Ce lien a déjà été payé.")
    if ligne.statut == INTENT_ANNULEE:
        raise IntentMorte("Ce lien a été annulé par l'établissement.")
    if ligne.statut == INTENT_EXPIREE or _vers_utc(ligne.expires_le) <= _maintenant():
        # Expirée par le temps mais pas encore marquée : le statut suit.
        if ligne.statut == INTENT_EN_ATTENTE:
            ligne.statut = INTENT_EXPIREE
            await db.flush()
        raise IntentMorte("Ce lien a expiré. Demandez un nouveau lien à l'établissement.")
    return ligne


async def resumer_pour_famille(db: AsyncSession, intention: PaiementIntent) -> dict:
    """Ce que le lien montre à la famille : l'essentiel, rien de plus.

    Aucune donnée qu'un lien intercepté transformerait en fuite : nom de
    l'établissement, prénom/nom de l'élève, numéro de facture, reste à
    payer **après** l'intention, échéance du lien.
    """
    etablissement = (await db.execute(select(Etablissement).limit(1))).scalars().first()
    etudiant = intention.etudiant
    facture = intention.facture
    return {
        "etablissement": etablissement.nom if etablissement else None,
        "devise": etablissement.devise if etablissement else "",
        "etudiant": f"{etudiant.prenom or ''} {etudiant.nom or ''}".strip() if etudiant else None,
        "matricule": etudiant.matricule if etudiant else None,
        "facture": {
            "numero": facture.numero_facture if facture else None,
            "montant_total": float(facture.montant_total) if facture else None,
            "montant_paye": float(facture.montant_paye) if facture else None,
            "reste_a_payer": float(facture.reste_a_payer) if facture else None,
        } if facture else None,
        "montant_demande": float(intention.montant),
        "provider": intention.provider,
        "expire_le": intention.expires_le.isoformat(),
    }


async def confirmer(
    db: AsyncSession,
    *,
    jeton: str,
    reference: Optional[str] = None,
) -> Paiement:
    """Transforme une intention vivante en Paiement + Recu, et la marque confirmée.

    Les règles du guichet sont les mêmes : solde de facture vérifié (le
    montant ne dépasse jamais le reste à payer **du moment de la
    confirmation**), facture mise à jour, reçu numéroté ``REC-AAAA-NNNN``.
    La confirmation est idempotente côté statut : une intention déjà
    confirmée lève, elle ne paie pas deux fois.

    Le montant encaissé est celui de l'intention : en simulation, c'est le
    retour de la passerelle ; le jour où une vraie passerelle confirmera un
    montant, c'est elle qui le dit ici.
    """
    intention = await intention_par_jeton(db, jeton)

    facture = await db.get(Facture, intention.facture_id) if intention.facture_id else None
    montant = Decimal(intention.montant).quantize(Decimal("0.01"))
    if facture is not None:
        if montant > facture.reste_a_payer:
            raise IntentMorte(
                "Le solde de cette facture a changé depuis l'émission du lien. "
                "Demandez un nouveau lien à l'établissement."
            )

    date_paiement = _maintenant().date()
    reference_finale = reference or f"PAY-{intention.provider.upper()}-{intention.id[:8]}"

    # Le reçu suit la numérotation du guichet : une seule séquence, un
    # encaissement en ligne ne doit pas créer de trou ni de doublon.
    annee = date_paiement.year
    count_r = (
        await db.execute(
            select(Recu.id).where(Recu.numero_recu.like(f"REC-{annee}-%"))
        )
    ).scalars().all()
    numero_recu = f"REC-{annee}-{(len(count_r) + 1):04d}"

    etablissement = (await db.execute(select(Etablissement).limit(1))).scalars().first()
    if etablissement is None:
        raise IntentInvalide("L'établissement doit être configuré avant un paiement en ligne.")

    etudiant = intention.etudiant
    session = intention.session
    donnees_recu = {
        "numero_recu": numero_recu,
        "date_emission": date_paiement.isoformat(),
        "etablissement": {
            "nom": etablissement.nom,
            "code": etablissement.code,
            "telephone": etablissement.telephone,
            "devise": etablissement.devise,
        },
        "etudiant": {
            "id": etudiant.id if etudiant else intention.etudiant_id,
            "matricule": etudiant.matricule if etudiant else None,
            "nom": etudiant.nom if etudiant else None,
            "prenom": etudiant.prenom if etudiant else None,
            "filiere": etudiant.filiere if etudiant else None,
            "niveau": etudiant.niveau if etudiant else None,
        },
        "session": {
            "id": intention.session_id,
            "nom": session.nom if session else None,
            "code": session.code if session else None,
        },
        "details_paiement": {
            "periode": "Paiement en ligne",
            # Colonne JSON : flottant d'affichage a deux decimales.
            "montant": float(montant),
            "mode_paiement": f"En ligne ({intention.provider})",
            "reference": reference_finale,
            "encaisse_par": "Paiement en ligne (auto)",
        },
        "facture": {
            "id": facture.id if facture else None,
            "numero_facture": facture.numero_facture if facture else None,
            "solde_restant": float(facture.reste_a_payer - montant) if facture else 0.0,
        } if facture else None,
    }

    paiement = Paiement(
        id=str(uuid.uuid4()),
        facture_id=intention.facture_id,
        etudiant_id=intention.etudiant_id,
        session_id=intention.session_id,
        periode_id=intention.periode_id,
        montant=montant,
        date_paiement=date_paiement,
        mode_paiement=f"En ligne ({intention.provider})",
        reference=reference_finale,
        statut="valide",
        encaisse_par_id=intention.creee_par_id,
    )
    db.add(paiement)
    await db.flush()

    recu = Recu(
        id=str(uuid.uuid4()),
        numero_recu=numero_recu,
        paiement_id=paiement.id,
        date_emission=date_paiement,
        donnees_json=donnees_recu,
    )
    db.add(recu)

    if facture is not None:
        facture.montant_paye = (facture.montant_paye + montant).quantize(Decimal("0.01"))
        facture.statut = "payee" if facture.montant_paye >= facture.montant_total else "partielle"

    intention.statut = INTENT_CONFIRMEE
    intention.confirmee_le = _maintenant()
    intention.paiement_id = paiement.id
    await db.flush()
    return paiement


async def annuler(db: AsyncSession, intention: PaiementIntent) -> None:
    """Retire un lien encore en attente. Une intention confirmée ne s'annule pas :
    elle est un paiement, qui se rembourse — pas un lien, qui se ferme."""
    if intention.statut == INTENT_CONFIRMEE:
        raise IntentInvalide("Cette intention est déjà payée : elle ne s'annule pas.")
    intention.statut = INTENT_ANNULEE
    await db.flush()
