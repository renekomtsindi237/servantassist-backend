"""
Endpoints du module Presence — suivi d'assiduite.

Enregistrement :
    POST   /                     Enregistrer une presence individuelle
    POST   /batch                Enregistrer par lot (appel nominal)

Lecture :
    GET    /                     Lister les presences (pagine)
    GET    /{id}                 Detail
    PATCH  /{id}                 Modifier (justification)

Self-service :
    GET    /my                   Mon historique de presence
    GET    /my/stats             Mes statistiques

Statistiques :
    GET    /user/{user_id}/stats Statistiques d'un servant

Accessible a : Aumonier, Admin (toutes operations)
               Tout utilisateur (consulter ses propres presences)
"""
from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.attendance_service import AttendanceService
from src.core.entities.attendance import AttendanceStatus, AttendanceType
from src.core.entities.user import User
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.attendance_repository import AttendanceRepository
from src.infrastructure.repositories.user_repository import UserRepository
from src.presentation.dependencies.auth_deps import (
    get_current_active_user,
    get_current_admin_or_aumonier,
)
from src.presentation.schemas.attendance import (
    AttendanceBatchCreate,
    AttendanceBatchResponse,
    AttendanceCreate,
    AttendanceResponse,
    AttendanceStatsResponse,
    AttendanceUpdate,
)
from src.presentation.schemas.user import PaginatedResponse

router = APIRouter()


def _get_service(session: AsyncSession) -> AttendanceService:
    return AttendanceService(
        attendance_repo=AttendanceRepository(session),
        user_repo=UserRepository(session),
    )


# ═══════════════════════════════════════════════════════════════════════════
#  ENREGISTREMENT
# ═══════════════════════════════════════════════════════════════════════════

@router.post(
    "/",
    response_model=AttendanceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_attendance(
    data: AttendanceCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Enregistrer la presence/absence d'un servant.

    **Accessible a :** Aumonier, Admin.
    """
    service = _get_service(session)
    return await service.record_attendance(data, recorded_by=current_user.id)


@router.post(
    "/batch",
    response_model=AttendanceBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_batch_attendance(
    data: AttendanceBatchCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Enregistrer la presence de plusieurs servants en une fois (appel nominal).

    **Accessible a :** Aumonier, Admin.
    """
    service = _get_service(session)
    return await service.record_batch(data, recorded_by=current_user.id)


# ═══════════════════════════════════════════════════════════════════════════
#  SELF-SERVICE (AVANT les routes parametrees)
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/my", response_model=PaginatedResponse[AttendanceResponse])
async def get_my_attendances(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    attendance_type: Optional[AttendanceType] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Mon historique de presence.

    **Accessible a :** Tout utilisateur authentifie.
    """
    service = _get_service(session)
    return await service.list_attendances(
        user_id=current_user.id,
        attendance_type=attendance_type,
        page=page,
        page_size=page_size,
    )


@router.get("/my/stats", response_model=AttendanceStatsResponse)
async def get_my_stats(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
):
    """
    Mes statistiques de presence.

    **Accessible a :** Tout utilisateur authentifie.
    """
    service = _get_service(session)
    return await service.get_user_stats(
        current_user.id, start_date=start_date, end_date=end_date
    )


# ═══════════════════════════════════════════════════════════════════════════
#  LECTURE
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/", response_model=PaginatedResponse[AttendanceResponse])
async def list_attendances(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
    user_id: Optional[UUID] = Query(None),
    attendance_type: Optional[AttendanceType] = Query(None),
    attendance_status: Optional[AttendanceStatus] = Query(None, alias="status"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    event_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Lister toutes les presences (pagine, filtrable).

    **Accessible a :** Aumonier, Admin.
    """
    service = _get_service(session)
    return await service.list_attendances(
        user_id=user_id,
        attendance_type=attendance_type,
        attendance_status=attendance_status,
        start_date=start_date,
        end_date=end_date,
        event_id=event_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/user/{user_id}/stats",
    response_model=AttendanceStatsResponse,
)
async def get_user_stats(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
):
    """
    Statistiques de presence d'un servant.

    **Accessible a :** Aumonier, Admin.
    """
    service = _get_service(session)
    return await service.get_user_stats(
        user_id, start_date=start_date, end_date=end_date
    )


@router.get("/{attendance_id}", response_model=AttendanceResponse)
async def get_attendance(
    attendance_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Detail d'un enregistrement de presence.

    **Accessible a :** Tout utilisateur authentifie.
    """
    service = _get_service(session)
    return await service.get_attendance(attendance_id)


@router.patch("/{attendance_id}", response_model=AttendanceResponse)
async def update_attendance(
    attendance_id: UUID,
    data: AttendanceUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Modifier un enregistrement (statut, justification).

    Si une justification est fournie et le statut est ABSENT,
    il passe automatiquement a ABSENT_JUSTIFIE.

    **Accessible a :** Aumonier, Admin.
    """
    service = _get_service(session)
    return await service.update_attendance(attendance_id, data)

