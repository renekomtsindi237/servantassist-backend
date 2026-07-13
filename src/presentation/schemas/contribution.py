"""
Schémas Pydantic pour le module de gestion des contributions (ECONOME).
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.core.entities.contribution import PaymentMode, PaymentStatus

# ══════════════════════════════════════════════════════════════════
#  CRÉATION
# ══════════════════════════════════════════════════════════════════


class ContributionCreate(BaseModel):
    """Schéma pour créer une contribution."""

    payment_mode: PaymentMode
    servant_id: UUID
    amount: float = Field(gt=0, description="Montant en FCFA")
    payment_date: datetime
    month: int = Field(ge=1, le=12, description="Mois (1-12)")
    year: int = Field(ge=2020, le=2100, description="Année")
    week_number: Optional[int] = Field(None, ge=1, le=4, description="Semaine (1-4) si hebdomadaire")
    notes: Optional[str] = None

    @field_validator("week_number")
    @classmethod
    def validate_week_number(cls, v, info):
        """Valide que week_number est fourni pour paiement hebdomadaire."""
        payment_mode = info.data.get("payment_mode")
        if payment_mode == PaymentMode.WEEKLY and v is None:
            raise ValueError("week_number est requis pour un paiement hebdomadaire")
        if payment_mode == PaymentMode.MONTHLY and v is not None:
            raise ValueError("week_number ne doit pas être fourni pour un paiement mensuel")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v, info):
        """Valide le montant selon le mode de paiement."""
        payment_mode = info.data.get("payment_mode")
        if payment_mode == PaymentMode.WEEKLY and v != 100:
            raise ValueError("Le montant hebdomadaire doit être 100 FCFA")
        if payment_mode == PaymentMode.MONTHLY and v != 500:
            raise ValueError("Le montant mensuel doit être 500 FCFA")
        return v


class ContributionUpdate(BaseModel):
    """Schéma pour modifier une contribution."""

    amount: Optional[float] = Field(None, gt=0)
    payment_date: Optional[datetime] = None
    notes: Optional[str] = None


# ══════════════════════════════════════════════════════════════════
#  RÉPONSES
# ══════════════════════════════════════════════════════════════════


class ContributionResponse(BaseModel):
    """Schéma de réponse pour une contribution."""

    id: UUID
    servant_id: UUID
    servant_name: str  # Enrichi
    amount: float
    payment_mode: PaymentMode
    payment_date: datetime
    month: int
    year: int
    week_number: Optional[int] = None
    recorded_by: UUID
    recorded_by_name: str  # Enrichi
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MonthlyContributionSummaryResponse(BaseModel):
    """Schéma de réponse pour le résumé mensuel d'un servant."""

    servant_id: UUID
    servant_name: str
    month: int
    year: int
    expected_amount: float
    paid_amount: float
    payment_mode: PaymentMode
    status: PaymentStatus
    payments: List[ContributionResponse]

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════════
#  RAPPORTS
# ══════════════════════════════════════════════════════════════════


class FinancialReportRequest(BaseModel):
    """Paramètres pour générer un rapport financier."""

    start_date: datetime
    end_date: datetime
    # Filtrer par servants spécifiques
    servant_ids: Optional[list[UUID]] = None


class FinancialReportResponse(BaseModel):
    """Schéma de réponse pour un rapport financier."""

    start_date: datetime
    end_date: datetime
    total_expected: float
    total_collected: float
    collection_rate: float
    servants_paid: int
    servants_late: int
    contributions: List[MonthlyContributionSummaryResponse]
    generated_by: UUID
    generated_by_name: str  # Enrichi
    generated_at: datetime
    watermark_logo: str = "logo_servant.jpeg"

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════════
#  STATISTIQUES
# ══════════════════════════════════════════════════════════════════


class ServantContributionStats(BaseModel):
    """Statistiques de contribution d'un servant."""

    servant_id: UUID
    servant_name: str
    total_expected: float
    total_paid: float
    payment_rate: float  # Pourcentage
    months_paid: int
    months_late: int
    last_payment_date: Optional[datetime] = None

    class Config:
        from_attributes = True
