"""
Schémas Pydantic V2 pour les Finances :
- Factures
- Encaissements / Paiements
- Reçus structurés
- Balance Âgée & Reporting
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.montant import Montant


# ---------------------------------------------------------------------------
# Grille tarifaire
# ---------------------------------------------------------------------------
class GrilleTarifaireBase(BaseModel):
    filiere: str = Field(..., min_length=1, max_length=255)
    niveau: str = Field(..., min_length=1, max_length=100)
    droits_inscription: Montant = Field(..., ge=Decimal("0"), max_digits=14, decimal_places=2)
    scolarite_mensuelle: Montant = Field(..., ge=Decimal("0"), max_digits=14, decimal_places=2)
    nombre_mois: int = Field(..., ge=1, le=24)
    actif: bool = True


class GrilleTarifaireCreate(GrilleTarifaireBase):
    id: Optional[str] = None
    filiere_id: Optional[str] = None


class GrilleTarifaireUpdate(BaseModel):
    filiere: Optional[str] = Field(None, min_length=1, max_length=255)
    filiere_id: Optional[str] = None
    niveau: Optional[str] = Field(None, min_length=1, max_length=100)
    droits_inscription: Optional[Montant] = Field(None, ge=Decimal("0"), max_digits=14, decimal_places=2)
    scolarite_mensuelle: Optional[Montant] = Field(None, ge=Decimal("0"), max_digits=14, decimal_places=2)
    nombre_mois: Optional[int] = Field(None, ge=1, le=24)
    actif: Optional[bool] = None


class GrilleTarifaireResponse(GrilleTarifaireBase):
    id: str
    filiere_id: Optional[str] = None
    total_annuel: Montant
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Facture
# ---------------------------------------------------------------------------
class FactureBase(BaseModel):
    etudiant_id: str
    session_id: str
    montant_total: Montant = Field(..., gt=Decimal("0"), max_digits=14, decimal_places=2)
    date_emission: date
    date_echeance: date
    description: Optional[str] = None


class FactureCreate(FactureBase):
    id: Optional[str] = None
    numero_facture: Optional[str] = None


class FactureResponse(FactureBase):
    id: str
    numero_facture: str
    montant_paye: Montant
    reste_a_payer: Montant
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
    montant: Montant = Field(..., gt=Decimal("0"), max_digits=14, decimal_places=2)
    date_paiement: Optional[date] = None
    mode_paiement: str = Field("Espèces", example="Espèces")  # Espèces, Wave, Orange Money, Chèque, Virement
    reference: Optional[str] = None


class PaiementResponse(BaseModel):
    id: str
    facture_id: Optional[str] = None
    etudiant_id: str
    session_id: str
    periode_id: Optional[str] = None
    montant: Montant
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
    montant_total_du: Montant
    non_echu: Montant
    retard_1_30_jours: Montant
    retard_31_60_jours: Montant
    retard_plus_60_jours: Montant


class BalanceAgeeResponse(BaseModel):
    date_calcul: date
    total_creances: Montant
    items: List[BalanceAgeeItem]
