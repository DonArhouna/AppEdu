"""
Suivi des relances de facturation.

La balance agee calcule les creances en retard ; ce module enregistre **ce
qu'on a fait** pour les recouvrer.

Trois partis pris, et pourquoi :

1. **La relance est un acte constate, pas un envoi.** L'application n'a
   aucune identite de messagerie, et en inventer une produirait un systeme
   qui Pretend contacter l'etudiant sans le faire. On enregistre donc que le
   secretariat a relance, par quel moyen, pour quel montant. Le contact, lui,
   se fait hors de l'application — ce qui rend le journal exact.

2. **Le montant et les factures sont figes au moment de la relance.** Une
   facture soldee depuis ne doit pas reecrire le passe : « 150 000 reclames
   le 3 mars » reste vrai meme apres encaissement.

3. **Aucune regle de relance automatique.** Le moment d'une relance releve de
   la politique de l'etablissement. Seuls le niveau (1re, 2e, 3e) et
   l'anciennete sont calcules, a partir des faits enregistres.

La detection des creances s'appuie sur la meme source que la balance agee —
``Facture.reste_a_payer`` et ``date_echeance`` — et non sur une copie :
une creance comptee de deux facons finit par diverger.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.etudiant import Etudiant
from app.models.finance import Facture
from app.models.session_academique import SessionAcademique

#: Moyens constates. Liste fermee : une saisie libre diverge des le premier
#: synonymes, et rend l'historique illisible (« appel », « Appel telephonique »).
MOYENS: Tuple[str, ...] = ("Courrier", "Email", "Appel telephonique", "Guichet", "SMS")

#: Statuts de facture qui representent une creance encore ouverte. Une facture
#: ``payee`` n'a rien a relancer.
STATUTS_CREANCE = ("emise", "partielle", "echue")


class RelanceInvalide(Exception):
    """La demande ne peut pas aboutir : la cause est expliquee."""


# ---------------------------------------------------------------------------
# Detection des creances
# ---------------------------------------------------------------------------
async def creances_etudiant(
    db: AsyncSession, etudiant_id: str, session_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Factures echues non soldees d'un etudiant, de la plus ancienne a la plus recente.

    Une facture non echue n'est pas une creance : elle apparait dans le total
    du mais pas dans les relances. Confondre les deux ferait relancer un
    etudiant pour une facture qui n'est pas encore due.
    """

    today = date.today()
    stmt = (
        select(Facture)
        .where(
            Facture.etudiant_id == etudiant_id,
            Facture.statut.in_(STATUTS_CREANCE),
            Facture.date_echeance < today,
        )
        .order_by(Facture.date_echeance)
    )
    if session_id:
        stmt = stmt.where(Facture.session_id == session_id)

    creances: List[Dict[str, Any]] = []
    for facture in (await db.execute(stmt)).scalars().all():
        reste = facture.reste_a_payer
        if reste <= 0:
            # Facture sollee mais statut non mis a jour : la creance est
            # eteinte. Ne pas la relancer serait une erreur d'encaissement.
            continue
        retard = (today - facture.date_echeance).days
        centime = Decimal("0.01")
        creances.append(
            {
                "facture_id": facture.id,
                "numero": facture.numero_facture,
                "session_id": facture.session_id,
                # Serialisee : ces dictes sont stockes tels quels dans la
                # colonne JSON ``relances.factures_concernees``, ou ``date``
                # et ``Decimal`` ne sont pas representables.  Le flottant
                # d'affichage a deux decimales suffit : l'exactitude vitre
                # dans les colonnes de la facture, l'instantane ne fait que
                # la montrer.
                "date_echeance": facture.date_echeance.isoformat(),
                "description": facture.description,
                "montant_total": float(facture.montant_total.quantize(centime)),
                "montant_regle": float(facture.montant_paye.quantize(centime)),
                "reste": float(reste.quantize(centime)),
                "retard_jours": retard,
            }
        )
    return creances


async def a_relancer(
    db: AsyncSession,
    session_id: Optional[str] = None,
    retard_minimum: int = 1,
) -> List[Dict[str, Any]]:
    """Etudiants dont les creances meritent un suivi, le plus ancien retard d'abord.

    ``retard_minimum`` vaut 1 : une facture echue **aujourd'hui** n'a pas de
    retard. Agresser l'etudiant le jour meme de l'echeance serait
    injustifiable — le versement peut encore arriver le jour meme.
    """

    from app.models.academic import Inscription

    stmt = (
        select(Etudiant)
        .options(selectinload(Etudiant.inscriptions))
        .order_by(Etudiant.nom, Etudiant.matricule)
    )
    resultats: List[Dict[str, Any]] = []
    for etudiant in (await db.execute(stmt)).scalars().all():
        if session_id and not any(
            i.session_id == session_id and i.statut == "active"
            for i in (etudiant.inscriptions or [])
        ):
            continue

        creances = await creances_etudiant(db, etudiant.id, session_id)
        echues = [c for c in creances if c["retard_jours"] >= retard_minimum]
        if not echues:
            continue

        total = sum((Decimal(c["reste"]) for c in echues), Decimal("0.00")).quantize(Decimal("0.01"))
        plus_ancienne = min(c["retard_jours"] for c in echues)
        niveau = await _niveau_relance(db, etudiant.id, session_id)

        dernier = await _derniere_relance(db, etudiant.id, session_id)
        resultats.append(
            {
                "etudiant": etudiant,
                "creances": echues,
                "nb_creances": len(echues),
                "total_du": total,
                "retard_jours": plus_ancienne,
                "anciennete_jours": plus_ancienne,
                "niveau_suivant": niveau,
                "nb_relances": niveau - 1,
                "derniere_relance": dernier,
                # Une relance faite la veille n'a pas besoin d'etre refaite
                # aujourd'hui : l'ecran doit pouvoir le dire.
                "jours_depuis_derniere": (
                    (date.today() - dernier.date_relance).days
                    if dernier
                    else None
                ),
            }
        )

    resultats.sort(key=lambda item: (-item["retard_jours"], str(item["etudiant"].matricule or "")))
    return resultats


async def _niveau_relance(
    db: AsyncSession, etudiant_id: str, session_id: Optional[str]
) -> int:
    """Prochain numero de relance sur la dette de cet etudiant.

    Compte les relances enregistrees — un fait, pas une convention. Un
    etudiant relance trois fois est a sa 4e relance, meme si les relances ont
    ete faites sur des factures differentes.
    """

    from app.models.relance import Relance

    stmt = select(func.count(Relance.id)).where(Relance.etudiant_id == etudiant_id)
    if session_id:
        stmt = stmt.where(Relance.session_id == session_id)
    return int((await db.execute(stmt)).scalar() or 0) + 1


async def _derniere_relance(
    db: AsyncSession, etudiant_id: str, session_id: Optional[str]
):
    from app.models.relance import Relance

    stmt = (
        select(Relance)
        .where(Relance.etudiant_id == etudiant_id)
        .order_by(Relance.date_relance.desc(), Relance.created_at.desc())
        .limit(1)
    )
    if session_id:
        stmt = stmt.where(Relance.session_id == session_id)
    return (await db.execute(stmt)).scalars().first()


async def historique(
    db: AsyncSession,
    etudiant_id: Optional[str] = None,
    limite: int = 100,
) -> List[Any]:
    """Relances enregistrees, de la plus recente a la plus ancienne."""

    from app.models.relance import Relance

    stmt = (
        select(Relance)
        .options(selectinload(Relance.etudiant))
        .order_by(Relance.date_relance.desc(), Relance.created_at.desc())
        .limit(limite)
    )
    if etudiant_id:
        stmt = stmt.where(Relance.etudiant_id == etudiant_id)
    return list((await db.execute(stmt)).scalars().all())


# ---------------------------------------------------------------------------
# Ecriture
# ---------------------------------------------------------------------------
async def enregistrer_relance(
    db: AsyncSession,
    *,
    etudiant_id: str,
    moyen: str,
    date_relance: date,
    session_id: Optional[str] = None,
    message: Optional[str] = None,
    auteur_id: Optional[int] = None,
) -> Tuple[Any, Dict[str, Any]]:
    """Consigne une relance et retourne ``(relance, resume)``.

    Le resume reprend les creances **telle qu'elles sont au moment de la
    relance** : c'est ce qui a ete reclame, meme si la facture est sollee
    depuis. Refuser une relance sans creance evite d'enregistrer un acte
    dans le vide.
    """

    from app.models.relance import Relance

    if moyen not in MOYENS:
        raise RelanceInvalide(
            f"Moyen de relance inconnu : « {moyen} ». "
            f"Valeurs acceptees : {', '.join(MOYENS)}."
        )
    if date_relance > date.today():
        raise RelanceInvalide(
            f"Une relance ne peut pas être datée du "
            f"{date_relance.strftime('%d/%m/%Y')} : elle est postérieure à "
            "aujourd'hui."
        )

    etudiant = await db.get(Etudiant, etudiant_id)
    if etudiant is None:
        raise RelanceInvalide("Étudiant introuvable.")

    creances = [
        c
        for c in await creances_etudiant(db, etudiant_id, session_id)
        if c["retard_jours"] >= 1
    ]
    if not creances:
        raise RelanceInvalide(
            f"Cet étudiant n'a aucune facture échue non soldée : "
            "il n'y a rien à relancer. Vérifiez les encaissements avant de "
            "relancer — relancer à tort décrédibilise l'établissement."
        )

    niveau = await _niveau_relance(db, etudiant_id, session_id)
    total = sum((Decimal(c["reste"]) for c in creances), Decimal("0.00")).quantize(Decimal("0.01"))
    plus_ancienne = min(c["retard_jours"] for c in creances)

    relance = Relance(
        id=str(uuid.uuid4()),
        etudiant_id=etudiant_id,
        session_id=creances[0]["session_id"] if not session_id else session_id,
        niveau=niveau,
        date_relance=date_relance,
        moyen=moyen,
        montant_reclame=total,
        factures_concernees=creances,
        retard_jours=plus_ancienne,
        message=(message or "").strip() or None,
        solde_apres=None,
        relance_par_id=auteur_id,
    )
    db.add(relance)
    await db.flush()

    resume = {
        "niveau": niveau,
        # Dict brut serialise par pydantic en JSON : un Decimal y partirait
        # en chaine.  Le flottant d'affichage a deux decimales suffit.
        "montant_reclame": float(total),
        "retard_jours": plus_ancienne,
        "nb_creances": len(creances),
    }
    return relance, resume


async def solder_suivi(
    db: AsyncSession,
    *,
    etudiant_id: str,
    niveau: int,
    auteur_id: Optional[int] = None,
) -> List[Any]:
    """Constate qu'un encaissement a suivi une relance.

    ``solde_apres`` est renseigne **a la volee**, jamais calcule a la volee
    lors d'une lecture : un paiement de mars ne doit pas retroagir sur une
    relance de janvier, et l'historique doit dire ce que la situation
    valait apres la relance.
    """

    from app.models.relance import Relance

    creances = await creances_etudiant(db, etudiant_id, None)
    solde = sum((Decimal(c["reste"]) for c in creances), Decimal("0.00")).quantize(Decimal("0.01"))

    stmt = select(Relance).where(
        Relance.etudiant_id == etudiant_id, Relance.niveau == niveau
    )
    relances = list((await db.execute(stmt)).scalars().all())
    for relance in relances:
        relance.solde_apres = solde
    await db.flush()
    return relances


__all__ = [
    "MOYENS",
    "STATUTS_CREANCE",
    "RelanceInvalide",
    "a_relancer",
    "creances_etudiant",
    "enregistrer_relance",
    "historique",
    "solder_suivi",
]
