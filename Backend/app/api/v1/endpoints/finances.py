"""
Endpoints Finances & Encaissements :
- Facturation (création, consultation)
- Encaissements rattachés aux tranches de session
- Génération automatique de Reçus structurés (REC-YYYY-XXXX)
- Suivi de la Balance Âgée & Impayés
"""

from typing import List, Optional
from datetime import date, datetime
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, require_comptabilite, get_current_active_user
from app.models.finance import Facture, Paiement, Recu
from app.models.etudiant import Etudiant
from app.models.etablissement import Etablissement
from app.models.session_academique import SessionAcademique, PeriodePaiement
from app.models.utilisateur import Utilisateur
from app.schemas.finance import (
    FactureResponse, FactureCreate,
    PaiementResponse, PaiementCreate,
    RecuResponse,
    BalanceAgeeResponse, BalanceAgeeItem,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# FACTURES
# ---------------------------------------------------------------------------
@router.get("/factures", response_model=List[FactureResponse], summary="Lister les factures")
async def list_factures(
    etudiant_id: Optional[str] = None,
    session_id: Optional[str] = None,
    statut: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_comptabilite),
):
    stmt = select(Facture)
    if etudiant_id:
        stmt = stmt.where(Facture.etudiant_id == etudiant_id)
    if session_id:
        stmt = stmt.where(Facture.session_id == session_id)
    if statut:
        stmt = stmt.where(Facture.statut == statut)
    stmt = stmt.order_by(Facture.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/factures", response_model=FactureResponse, status_code=status.HTTP_201_CREATED, summary="Émettre une facture")
async def create_facture(
    payload: FactureCreate,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_comptabilite),
):
    annee = payload.date_emission.year
    numero = payload.numero_facture
    if not numero:
        stmt_c = select(func.count(Facture.id)).where(Facture.numero_facture.like(f"FAC-{annee}-%"))
        res_c = await db.execute(stmt_c)
        count = res_c.scalar() or 0
        numero = f"FAC-{annee}-{(count + 1):04d}"

    facture = Facture(
        id=payload.id or str(uuid.uuid4()),
        numero_facture=numero,
        etudiant_id=payload.etudiant_id,
        session_id=payload.session_id,
        montant_total=payload.montant_total,
        montant_paye=0.0,
        date_emission=payload.date_emission,
        date_echeance=payload.date_echeance,
        statut="emise",
        description=payload.description,
    )
    db.add(facture)
    await db.commit()
    await db.refresh(facture)
    return facture


@router.get("/factures/{facture_id}", response_model=FactureResponse, summary="Détail d'une facture")
async def get_facture(facture_id: str, db: AsyncSession = Depends(get_db), _auth=Depends(require_comptabilite)):
    stmt = select(Facture).where(Facture.id == facture_id)
    res = await db.execute(stmt)
    facture = res.scalar_one_or_none()
    if not facture:
        raise HTTPException(status_code=404, detail="Facture introuvable.")
    return facture


# ---------------------------------------------------------------------------
# PAIEMENTS & ENCAISSEMENTS
# ---------------------------------------------------------------------------
@router.get("/paiements", response_model=List[PaiementResponse], summary="Lister les paiements")
async def list_paiements(
    etudiant_id: Optional[str] = None,
    session_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_comptabilite),
):
    stmt = select(Paiement)
    if etudiant_id:
        stmt = stmt.where(Paiement.etudiant_id == etudiant_id)
    if session_id:
        stmt = stmt.where(Paiement.session_id == session_id)
    stmt = stmt.order_by(Paiement.date_paiement.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/paiements/{paiement_id}", response_model=PaiementResponse, summary="Détail d'un paiement")
async def get_paiement(paiement_id: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Paiement)
        .options(
            selectinload(Paiement.etudiant),
            selectinload(Paiement.facture),
            selectinload(Paiement.session),
            selectinload(Paiement.periode),
        )
        .where(Paiement.id == paiement_id)
    )
    res = await db.execute(stmt)
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Paiement introuvable.")
    return p


@router.post("/paiements", response_model=PaiementResponse, status_code=status.HTTP_201_CREATED, summary="Encaisser un paiement")
async def create_paiement(
    payload: PaiementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateur = Depends(require_comptabilite),
):
    """
    Enregistre un paiement étudiant :
    1. Si lié à une facture, déduit le montant et ajuste le statut (partielle, payee).
    2. Enregistre le paiement avec sa référence ou génère une référence automatique.
    3. Génère immédiatement le reçu fiscal/scolaire structuré (REC-YYYY-XXXX).
    """
    dt_paiement = payload.date_paiement or date.today()
    annee = dt_paiement.year

    # Référence paiement
    reference = payload.reference
    if not reference:
        reference = f"ENC-{int(datetime.now().timestamp())}"

    # Vérification étudiant
    stmt_etu = select(Etudiant).where(Etudiant.id == payload.etudiant_id)
    res_etu = await db.execute(stmt_etu)
    etudiant = res_etu.scalar_one_or_none()
    if not etudiant:
        raise HTTPException(status_code=404, detail="Étudiant introuvable.")

    # Vérification session
    stmt_ses = select(SessionAcademique).where(SessionAcademique.id == payload.session_id)
    res_ses = await db.execute(stmt_ses)
    session = res_ses.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session académique introuvable.")

    # Période optionnelle
    nom_periode = "Droits / Scolarité Générale"
    if payload.periode_id:
        stmt_per = select(PeriodePaiement).where(PeriodePaiement.id == payload.periode_id)
        res_per = await db.execute(stmt_per)
        periode = res_per.scalar_one_or_none()
        if periode:
            nom_periode = periode.nom

    # Mise à jour de la facture si spécifiée
    facture = None
    if payload.facture_id:
        stmt_fac = select(Facture).where(Facture.id == payload.facture_id)
        res_fac = await db.execute(stmt_fac)
        facture = res_fac.scalar_one_or_none()
        if facture:
            facture.montant_paye = round(facture.montant_paye + payload.montant, 2)
            if facture.montant_paye >= facture.montant_total:
                facture.statut = "payee"
            else:
                facture.statut = "partielle"

    paiement_id = str(uuid.uuid4())
    paiement = Paiement(
        id=paiement_id,
        facture_id=payload.facture_id,
        etudiant_id=payload.etudiant_id,
        session_id=payload.session_id,
        periode_id=payload.periode_id,
        montant=payload.montant,
        date_paiement=dt_paiement,
        mode_paiement=payload.mode_paiement,
        reference=reference,
        statut="valide",
        encaisse_par_id=current_user.id,
    )
    db.add(paiement)

    # Récupération établissement pour l'en-tête du reçu
    stmt_etab = select(Etablissement).limit(1)
    res_etab = await db.execute(stmt_etab)
    etablissement = res_etab.scalar_one_or_none()

    # Numérotation du reçu
    stmt_cr = select(func.count(Recu.id)).where(Recu.numero_recu.like(f"REC-{annee}-%"))
    res_cr = await db.execute(stmt_cr)
    count_r = res_cr.scalar() or 0
    numero_recu = f"REC-{annee}-{(count_r + 1):04d}"

    # Données structurées pour impression
    donnees_recu = {
        "numero_recu": numero_recu,
        "date_emission": dt_paiement.isoformat(),
        "etablissement": {
            "nom": etablissement.nom if etablissement else "EduManagePro",
            "code": etablissement.code if etablissement else "EMP",
            "telephone": etablissement.telephone if etablissement else "",
            "devise": etablissement.devise if etablissement else "FCFA",
        },
        "etudiant": {
            "id": etudiant.id,
            "matricule": etudiant.matricule,
            "nom": etudiant.nom,
            "prenom": etudiant.prenom,
            "filiere": etudiant.filiere,
            "niveau": etudiant.niveau,
        },
        "session": {
            "id": session.id,
            "nom": session.nom,
            "code": session.code,
        },
        "details_paiement": {
            "periode": nom_periode,
            "montant": payload.montant,
            "mode_paiement": payload.mode_paiement,
            "reference": reference,
            "encaisse_par": current_user.full_name,
        },
        "facture": {
            "id": facture.id if facture else None,
            "numero_facture": facture.numero_facture if facture else None,
            "solde_restant": facture.reste_a_payer if facture else 0.0,
        } if facture else None,
    }

    recu = Recu(
        id=str(uuid.uuid4()),
        numero_recu=numero_recu,
        paiement_id=paiement_id,
        date_emission=dt_paiement,
        donnees_json=donnees_recu,
    )
    db.add(recu)

    await db.commit()
    await db.refresh(paiement)
    return paiement


# ---------------------------------------------------------------------------
# REÇUS
# ---------------------------------------------------------------------------
@router.get("/recus/{recu_id}", response_model=RecuResponse, summary="Consulter un reçu")
async def get_recu(recu_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Recu).where(Recu.id == recu_id)
    res = await db.execute(stmt)
    recu = res.scalar_one_or_none()
    if not recu:
        raise HTTPException(status_code=404, detail="Reçu introuvable.")
    return recu


@router.get("/paiements/{paiement_id}/recu", response_model=RecuResponse, summary="Reçu d'un paiement")
async def get_recu_by_paiement(paiement_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Recu).where(Recu.paiement_id == paiement_id)
    res = await db.execute(stmt)
    recu = res.scalar_one_or_none()
    if not recu:
        raise HTTPException(status_code=404, detail="Aucun reçu associé à ce paiement.")
    return recu


# ---------------------------------------------------------------------------
# BALANCE ÂGÉE & REPORTING
# ---------------------------------------------------------------------------
@router.get("/balance-agee", response_model=BalanceAgeeResponse, summary="Calculer la balance âgée des créances")
async def get_balance_agee(db: AsyncSession = Depends(get_db), _auth=Depends(require_comptabilite)):
    """Génère la balance âgée des créances scolaires par palier de retard (0-30, 31-60, >60 jours)."""
    today = date.today()
    stmt = (
        select(Facture)
        .options(selectinload(Facture.etudiant))
        .where(Facture.statut.in_(["emise", "partielle", "echue"]))
    )
    res = await db.execute(stmt)
    factures = res.scalars().all()

    items: List[BalanceAgeeItem] = []
    total_creances = 0.0

    for f in factures:
        reste = f.reste_a_payer
        if reste <= 0:
            continue
        total_creances += reste
        retard_jours = (today - f.date_echeance).days

        non_echu = reste if retard_jours <= 0 else 0.0
        retard_1_30 = reste if 1 <= retard_jours <= 30 else 0.0
        retard_31_60 = reste if 31 <= retard_jours <= 60 else 0.0
        retard_plus_60 = reste if retard_jours > 60 else 0.0

        items.append(
            BalanceAgeeItem(
                etudiant_id=f.etudiant.id if f.etudiant else f.etudiant_id,
                matricule=f.etudiant.matricule if f.etudiant else "N/A",
                nom_complet=f"{f.etudiant.nom} {f.etudiant.prenom}" if f.etudiant else "Inconnu",
                filiere=f.etudiant.filiere if f.etudiant else "Générale",
                montant_total_du=reste,
                non_echu=non_echu,
                retard_1_30_jours=retard_1_30,
                retard_31_60_jours=retard_31_60,
                retard_plus_60_jours=retard_plus_60,
            )
        )

    return BalanceAgeeResponse(
        date_calcul=today,
        total_creances=round(total_creances, 2),
        items=items,
    )
