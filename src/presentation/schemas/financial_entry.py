"""
Schémas Pydantic pour le module COMMISSAIRE_AUX_COMPTES - Audit financier.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.core.entities.financial_entry import EntryCategory, EntrySource, VerificationStatus


# ── Schémas de création ──────────────────────────────────────────────────
class FinancialEntryCreate(BaseModel):
    """Schéma pour créer une entrée financière."""

    date: datetime
    amount: float = Field(gt=0)
    category: EntryCategory
    source: EntrySource
    reference: Optional[str] = None
    description: str = Field(min_length=1)


class FinancialEntryUpdate(BaseModel):
    """Schéma pour modifier une entrée financière."""

    date: Optional[datetime] = None
    amount: Optional[float] = Field(None, gt=0)
    category: Optional[EntryCategory] = None
    source: Optional[EntrySource] = None
    reference: Optional[str] = None
    description: Optional[str] = Field(None, min_length=1)


class FinancialEntryVerify(BaseModel):
    """Schéma pour vérifier une entrée."""

    verification_status: VerificationStatus
    notes: Optional[str] = None


# ── Schémas de réponse ───────────────────────────────────────────────────
class FinancialEntryResponse(BaseModel):
    """Schéma de réponse pour une entrée financière."""

    id: UUID
    date: datetime
    amount: float
    category: EntryCategory
    source: EntrySource
    reference: Optional[str]
    description: str
    recorded_by: UUID
    verified_by: Optional[UUID]
    verification_status: VerificationStatus
    verification_date: Optional[datetime]
    notes: Optional[str]
    watermark_logo: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FinancialEntryListResponse(BaseModel):
    """Schéma de réponse pour une liste d'entrées."""

    items: List[FinancialEntryResponse]
    total: int
    skip: int
    limit: int


# ── Schémas pour rapport d'audit ─────────────────────────────────────────
class AuditReportRequest(BaseModel):
    """Schéma pour demander un rapport d'audit."""

    start_date: datetime
    end_date: datetime
    include_discrepancies: bool = True
    include_recommendations: bool = True


class FinancialSummaryResponse(BaseModel):
    """Schéma de réponse pour un résumé financier."""

    category: EntryCategory
    total_amount: float
    entry_count: int
    verified_amount: float
    pending_amount: float

    class Config:
        from_attributes = True


class AuditReportResponse(BaseModel):
    """Schéma de réponse pour un rapport d'audit."""

    id: UUID
    start_date: datetime
    end_date: datetime
    total_entries: int
    total_amount: float
    verified_entries: int
    pending_entries: int
    rejected_entries: int
    discrepancies: List[str]
    recommendations: Optional[str]
    summaries: List[FinancialSummaryResponse]
    generated_by: UUID
    watermark_logo: str
    generated_at: datetime

    class Config:
        from_attributes = True


# ── Schémas pour écarts ──────────────────────────────────────────────────
class DiscrepancyCreate(BaseModel):
    """Schéma pour créer un écart."""

    entry_id: UUID
    type: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1)
    expected_amount: Optional[float] = None
    actual_amount: Optional[float] = None


class DiscrepancyResolve(BaseModel):
    """Schéma pour résoudre un écart."""

    resolved: bool = True
    resolution_notes: str = Field(min_length=1)


class DiscrepancyResponse(BaseModel):
    """Schéma de réponse pour un écart."""

    id: UUID
    entry_id: UUID
    type: str
    description: str
    expected_amount: Optional[float]
    actual_amount: Optional[float]
    detected_by: UUID
    detected_at: datetime
    resolved: bool
    resolution_notes: Optional[str]

    class Config:
        from_attributes = True


# ── Schémas pour statistiques ────────────────────────────────────────────
class FinancialStatsResponse(BaseModel):
    """Schéma de réponse pour les statistiques financières."""

    total_amount: float
    total_entries: int
    verified_amount: float
    verified_entries: int
    pending_amount: float
    pending_entries: int
    rejected_amount: float
    rejected_entries: int
    verification_rate: float  # Pourcentage
    average_entry_amount: float
    period_start: datetime
    period_end: datetime
