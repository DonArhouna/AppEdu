"""
Schémas Pydantic V2 pour les Finances :
- Factures
- Encaissements / Paiements
- Reçus structurés
- Balance Âgée & Reporting
"""

from datetime import date, datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Facture
# ---------------------------------------------------------------------------
class FactureBase(BaseModel):
    etudiant_id: str
    session_id: str
    montant_total: float = Field(..., gt=0.0, example=375000.0)
    date_emission: date
    date_echeance: date
    description: Optional[str] = None


class FactureCreate(FactureBase):
    id: Optional[str] = None
    numero_facture: Optional[str] = None


class FactureResponse(FactureBase):
    id: str
    numero_facture: str
    montant_paye: float
    reste_a_payer: float
    statut: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Paiement
# ---------------------------------------------------------------------------
class PaiementCreate(BaseModel):
    etudiant_id: str
    session_id: str
    facture_id: Optional[str] = None
    periode_id: Optional[str] = None
    montant: float = Field(..., gt=0.0, example=280000.0)
    date_paiement: Optional[date] = None
    mode_paiement: str = Field("Espèces", example="Espèces")  # Espèces, Wave, Orange Money, Chèque, Virement
    reference: Optional[str] = None


class PaiementResponse(BaseModel):
    id: str
    facture_id: Optional[str] = None
    etudiant_id: str
    session_id: str
    periode_id: Optional[str] = None
    montant: float
    date_paiement: date
    mode_paiement: str
    reference: str
    statut: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Reçu
# ---------------------------------------------------------------------------
class RecuResponse(BaseModel):
    id: str
    numero_recu: str
    paiement_id: str
    date_emission: date
    donnees_json: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Balance Âgée
# ---------------------------------------------------------------------------
class BalanceAgeeItem(BaseModel):
    etudiant_id: str
    matricule: str
    nom_complet: str
    filiere: str
    montant_total_du: float
    non_echu: float
    retard_1_30_jours: float
    retard_31_60_jours: float
    retard_plus_60_jours: float


class BalanceAgeeResponse(BaseModel):
    date_calcul: date
    total_creances: float
    items: List[BalanceAgeeItem]
