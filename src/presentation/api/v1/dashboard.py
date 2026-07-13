"""
Endpoints Dashboard — statistiques globales cross-module.

Accessible aux admins et aumôniers.

GET /summary          → Vue d'ensemble (comptages + taux)
GET /attendance       → Tendance de présence sur une période
GET /cotisations      → Statut cotisations de la période courante
GET /events/upcoming  → 5 prochains événements
GET /top-servants     → Top 10 servants par taux de présence
"""

from datetime import datetime
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.dashboard_service import DashboardService
from src.core.entities.user import User
from src.infrastructure.database.session import get_db_session
from src.presentation.dependencies.auth_deps import (
    get_current_active_user,
    get_current_admin_or_aumonier,
)
from src.presentation.schemas.dashboard import (
    AttendanceTrend,
    CotisationStatus,
    DashboardSummary,
    TopServant,
    UpcomingEvent,
)

router = APIRouter()


def _get_service(session: AsyncSession) -> DashboardService:
    return DashboardService(session)


@router.get(
    "/summary",
    response_model=DashboardSummary,
    summary="Vue d'ensemble globale",
)
async def get_dashboard_summary(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Retourne les métriques globales de l'application : comptages, taux de présence et cotisations."""
    service = _get_service(session)
    return await service.get_summary()


@router.get(
    "/attendance",
    response_model=AttendanceTrend,
    summary="Tendance de présence",
)
async def get_attendance_trend(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
    start_date: Optional[datetime] = Query(None, description="Date de début"),
    end_date: Optional[datetime] = Query(None, description="Date de fin"),
    group_by: str = Query("month", description="Grouper par 'month' ou 'week'"),
):
    """Retourne la tendance de présence groupée par mois ou par semaine."""
    if group_by not in ("month", "week"):
        group_by = "month"
    service = _get_service(session)
    return await service.get_attendance_trend(
        start_date=start_date,
        end_date=end_date,
        group_by=group_by,
    )


@router.get(
    "/cotisations",
    response_model=CotisationStatus,
    summary="Statut des cotisations",
)
async def get_cotisation_status(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """Retourne le statut des cotisations de la période la plus récente."""
    service = _get_service(session)
    result = await service.get_cotisation_status()
    if result is None:
        return CotisationStatus(
            period_id=None,
            period_name="Aucune période",
            total_members=0,
            paid_count=0,
            partial_count=0,
            unpaid_count=0,
            total_expected=0.0,
            total_collected=0.0,
            rate_percent=0.0,
        )
    return result


@router.get(
    "/events/upcoming",
    response_model=List[UpcomingEvent],
    summary="Prochains événements",
)
async def get_upcoming_events(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    limit: int = Query(5, ge=1, le=20, description="Nombre d'événements à retourner"),
):
    """Retourne les N prochains événements avec leur nombre d'assignments."""
    service = _get_service(session)
    return await service.get_upcoming_events(limit=limit)


@router.get(
    "/top-servants",
    response_model=List[TopServant],
    summary="Top servants par assiduité",
)
async def get_top_servants(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
    limit: int = Query(10, ge=1, le=20, description="Nombre de servants à retourner"),
):
    """Retourne le classement des servants les plus assidus."""
    service = _get_service(session)
    return await service.get_top_servants(limit=limit)
