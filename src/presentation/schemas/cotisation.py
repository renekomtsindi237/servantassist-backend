"""
Schemas Pydantic pour le module Cotisations.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.core.entities.cotisation import (
    CotisationStatus,
    CotisationType,
    PeriodType,
)


# ═══════════════════════════════════════════════════════════════════════════
#  Periodes de cotisation
# ═══════════════════════════════════════════════════════════════════════════

class CotisationPeriodCreate(BaseModel):
    """Creer une periode de cotisation."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    cotisation_type: CotisationType = CotisationType.ORDINAIRE
    period_type: PeriodType = PeriodType.MENSUEL
    amount_expected: float = Field(..., ge=0)
    start_date: datetime
    end_date: datetime
    event_id: Optional[UUID] = None


class CotisationPeriodUpdate(BaseModel):
    """Modifier une periode de cotisation."""
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    amount_expected: Optional[float] = Field(None, ge=0)
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None


class CotisationPeriodResponse(BaseModel):
    """Reponse pour une periode de cotisation."""
    id: UUID
    title: str
    description: Optional[str] = None
    cotisation_type: CotisationType
    period_type: PeriodType
    amount_expected: float
    start_date: datetime
    end_date: datetime
    event_id: Optional[UUID] = None
    is_active: bool
    created_by: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Stats enrichies
    total_members: int = 0
    total_paid: int = 0
    total_amount_collected: float = 0
    collection_rate: float = 0  # Pourcentage

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════════════════
#  Paiements individuels
# ═══════════════════════════════════════════════════════════════════════════

class MemberCotisationCreate(BaseModel):
    """Enregistrer un paiement de cotisation."""
    period_id: UUID
    user_id: UUID
    amount_paid: float = Field(..., ge=0)
    payment_method: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)


class MemberCotisationUpdate(BaseModel):
    """Modifier un paiement."""
    amount_paid: Optional[float] = Field(None, ge=0)
    status: Optional[CotisationStatus] = None
    payment_method: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)


class MemberCotisationResponse(BaseModel):
    """Reponse pour un paiement de cotisation."""
    id: UUID
    period_id: UUID
    user_id: UUID
    amount_paid: float
    status: CotisationStatus
    payment_date: Optional[datetime] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None
    recorded_by: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Enrichissement
    user_first_name: Optional[str] = None
    user_last_name: Optional[str] = None
    period_title: Optional[str] = None
    amount_expected: Optional[float] = None

    class Config:
        from_attributes = True


class CotisationBilanResponse(BaseModel):
    """Bilan financier d'une periode."""
    period: CotisationPeriodResponse
    payments: List[MemberCotisationResponse]
    total_expected: float
    total_collected: float
    total_remaining: float
    taux_recouvrement: float  # Pourcentage

