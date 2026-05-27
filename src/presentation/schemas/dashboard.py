"""
Schémas Pydantic pour le Dashboard / Statistiques globales.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    """Vue d'ensemble globale de l'application."""

    total_servants: int
    total_parents: int
    total_active_users: int
    total_events: int
    total_assignments: int
    attendance_rate_percent: float  # Taux de présence global (0-100)
    cotisation_rate_percent: float  # Taux de cotisations payées (0-100)
    generated_at: datetime


class AttendancePoint(BaseModel):
    """Point de données pour les courbes de présence."""

    period: str  # Ex. "2026-03", "Semaine 12", etc.
    total: int  # Nombre total d'appels
    present: int  # Nombre de présents
    absent: int  # Nombre d'absents
    rate_percent: float  # Taux de présence


class AttendanceTrend(BaseModel):
    """Tendance de présence sur une période."""

    period_label: str
    points: List[AttendancePoint]
    average_rate_percent: float


class CotisationStatus(BaseModel):
    """Statut des cotisations de la période courante."""

    period_id: Optional[UUID]
    period_name: str
    total_members: int
    paid_count: int
    partial_count: int
    unpaid_count: int
    total_expected: float  # Montant total attendu (FCFA)
    total_collected: float  # Montant effectivement collecté (FCFA)
    rate_percent: float  # Taux de paiement


class UpcomingEvent(BaseModel):
    """Résumé d'un événement à venir."""

    id: UUID
    title: str
    event_date: datetime
    location: str
    total_assignments: int
    confirmed_assignments: int


class TopServant(BaseModel):
    """Servant dans le classement des meilleurs assidus."""

    rank: int
    user_id: UUID
    full_name: str
    total_sessions: int
    present_count: int
    attendance_rate_percent: float
