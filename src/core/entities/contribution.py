"""
Entités pour le module de gestion des contributions financières (ECONOME).

Gère les contributions mensuelles des servants :
- Hebdomadaire : 100 FCFA/samedi
- Mensuel : 500 FCFA/mois
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class PaymentMode(str, Enum):
    """Mode de paiement des contributions."""

    WEEKLY = "HEBDOMADAIRE"  # 100 FCFA/samedi
    MONTHLY = "MENSUEL"  # 500 FCFA/mois


class PaymentStatus(str, Enum):
    """Statut du paiement."""

    PAID = "PAYE"
    PENDING = "EN_ATTENTE"
    LATE = "EN_RETARD"


class Contribution(SQLModel, table=True):
    """
    Contribution financière d'un servant.
    """

    __tablename__ = "contributions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    servant_id: UUID = Field(foreign_key="users.id")
    amount: float  # Montant en FCFA
    payment_mode: PaymentMode
    payment_date: datetime
    month: int  # 1-12
    year: int
    week_number: Optional[int] = None  # 1-4 pour paiement hebdomadaire
    recorded_by: UUID = Field(foreign_key="users.id")
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MonthlyContributionSummary(BaseModel):
    """
    Résumé des contributions pour un servant sur un mois.

    Attributes:
        servant_id: ID du servant
        servant_name: Nom complet du servant
        month: Mois
        year: Année
        expected_amount: Montant attendu
        paid_amount: Montant payé
        payment_mode: Mode de paiement
        status: Statut du paiement
        payments: Liste des paiements effectués
    """

    servant_id: UUID
    servant_name: str
    month: int
    year: int
    expected_amount: float  # 400 ou 500 FCFA
    paid_amount: float
    payment_mode: PaymentMode
    status: PaymentStatus
    payments: list[Contribution] = []

    class Config:
        from_attributes = True


class FinancialReport(BaseModel):
    """
    Rapport financier pour une période donnée.

    Attributes:
        start_date: Date de début
        end_date: Date de fin
        total_expected: Montant total attendu
        total_collected: Montant total collecté
        collection_rate: Taux de collecte (%)
        servants_paid: Nombre de servants à jour
        servants_late: Nombre de servants en retard
        contributions: Liste des contributions
        generated_by: ID de l'ECONOME
        generated_at: Date de génération
        watermark_logo: Logo en filigrane
    """

    start_date: datetime
    end_date: datetime
    total_expected: float
    total_collected: float
    collection_rate: float  # Pourcentage
    servants_paid: int
    servants_late: int
    contributions: list[MonthlyContributionSummary]
    generated_by: UUID
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    watermark_logo: str = "logo_servant.jpeg"

    class Config:
        from_attributes = True
