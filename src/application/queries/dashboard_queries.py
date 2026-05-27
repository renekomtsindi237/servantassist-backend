"""
Dashboard queries — lecture des métriques globales (CQRS).

DashboardService reste intact (compatibilité ascendante).
DashboardQuery est le point d'entrée CQRS propre pour les futurs
consommateurs (mobile v2, export CSV, etc.).

Avantage : les lectures analytics peuvent être mise en cache,
déplacées vers une base de données en lecture seule, ou parallélisées
sans toucher aux services d'écriture.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.dashboard_service import DashboardService
from src.presentation.schemas.dashboard import (
    AttendanceTrend,
    CotisationStatus,
    DashboardSummary,
    TopServant,
    UpcomingEvent,
)


class DashboardQuery:
    """
    Façade CQRS pour les lectures du dashboard.

    Délègue à DashboardService (compatible avec l'existant).
    Peut être remplacé par une implémentation directe SQL optimisée
    sans changer les consommateurs.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._service = DashboardService(session)

    async def summary(self) -> DashboardSummary:
        return await self._service.get_summary()

    async def attendance_trend(self, weeks: int = 8) -> AttendanceTrend:
        return await self._service.get_attendance_trend(weeks=weeks)

    async def cotisation_status(self) -> CotisationStatus:
        return await self._service.get_cotisation_status()

    async def upcoming_events(self, limit: int = 5) -> list[UpcomingEvent]:
        return await self._service.get_upcoming_events(limit=limit)

    async def top_servants(self, limit: int = 10) -> list[TopServant]:
        return await self._service.get_top_servants(limit=limit)
