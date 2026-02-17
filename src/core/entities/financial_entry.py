"""
Entités pour le module COMMISSAIRE_AUX_COMPTES - Audit financier.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class EntryCategory(str, Enum):
    """Catégorie d'entrée financière."""

    CONTRIBUTION = "CONTRIBUTION"  # Contributions des servants
    DONATION = "DON"  # Dons
    EVENT = "EVENEMENT"  # Revenus d'événements
    COTISATION = "COTISATION"  # Cotisations
    OTHER = "AUTRE"  # Autres revenus


class EntrySource(str, Enum):
    """Source de l'entrée financière."""

    SERVANT = "SERVANT"  # Contribution d'un servant
    EXTERNAL = "EXTERNE"  # Source externe
    EVENT = "EVENEMENT"  # Événement organisé
    PARISH = "PAROISSE"  # Paroisse
    OTHER = "AUTRE"  # Autre source


class VerificationStatus(str, Enum):
    """Statut de vérification."""

    PENDING = "EN_ATTENTE"  # En attente de vérification
    VERIFIED = "VERIFIE"  # Vérifié par le commissaire
    REJECTED = "REJETE"  # Rejeté (anomalie détectée)


class FinancialEntry(SQLModel, table=True):
    """
    Entrée financière pour l'audit.
    """

    __tablename__ = "financial_entries"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    date: datetime
    amount: float = Field(gt=0)
    category: EntryCategory
    source: EntrySource
    reference: Optional[str] = None
    description: str
    recorded_by: UUID = Field(foreign_key="users.id")
    verified_by: Optional[UUID] = Field(default=None, foreign_key="users.id")
    verification_status: VerificationStatus = VerificationStatus.PENDING
    verification_date: Optional[datetime] = None
    notes: Optional[str] = None
    watermark_logo: str = "logo_servant.jpeg"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AuditReport(BaseModel):
    """
    Rapport d'audit financier.

    Attributes:
        id: Identifiant unique
        start_date: Date de début de la période
        end_date: Date de fin de la période
        total_entries: Nombre total d'entrées
        total_amount: Montant total
        verified_entries: Nombre d'entrées vérifiées
        pending_entries: Nombre d'entrées en attente
        rejected_entries: Nombre d'entrées rejetées
        discrepancies: Liste des écarts détectés
        recommendations: Recommandations du commissaire
        generated_by: ID du commissaire
        watermark_logo: Logo en filigrane
        generated_at: Date de génération
    """

    id: UUID = Field(default_factory=uuid4)
    start_date: datetime
    end_date: datetime
    total_entries: int
    total_amount: float
    verified_entries: int
    pending_entries: int
    rejected_entries: int
    discrepancies: list[str] = []
    recommendations: Optional[str] = None
    generated_by: UUID
    watermark_logo: str = "logo_servant.jpeg"
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class FinancialSummary(BaseModel):
    """
    Résumé financier par catégorie.

    Attributes:
        category: Catégorie
        total_amount: Montant total
        entry_count: Nombre d'entrées
        verified_amount: Montant vérifié
        pending_amount: Montant en attente
    """

    category: EntryCategory
    total_amount: float
    entry_count: int
    verified_amount: float
    pending_amount: float

    class Config:
        from_attributes = True


class Discrepancy(SQLModel, table=True):
    """
    Écart ou anomalie détectée.
    """

    __tablename__ = "financial_discrepancies"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    entry_id: UUID = Field(foreign_key="financial_entries.id")
    type: str
    description: str
    expected_amount: Optional[float] = None
    actual_amount: Optional[float] = None
    detected_by: UUID = Field(foreign_key="users.id")
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolution_notes: Optional[str] = None
