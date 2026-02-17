"""
Endpoints API pour la gestion des appels (CENSEUR).
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.application.services.attendance_session_service import AttendanceSessionService
from src.core.entities.user import User
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.attendance_session_repository import AttendanceSessionRepository
from src.infrastructure.repositories.user_repository import UserRepository
from src.presentation.dependencies.auth_deps import get_current_user, require_censeur, require_censeur_strict
from src.presentation.schemas.attendance_session import (
    AttendanceRecordCreate,
    AttendanceRecordResponse,
    AttendanceRecordUpdate,
    AttendanceReportRequest,
    AttendanceReportResponse,
    AttendanceSessionCreate,
    AttendanceSessionResponse,
    ServantAttendanceStatsResponse,
    ServantListItem,
)
from src.presentation.schemas.user import PaginatedResponse

router = APIRouter()


# ══════════════════════════════════════════════════════════════════
#  DÉPENDANCES
# ══════════════════════════════════════════════════════════════════


async def get_attendance_service(
    session=Depends(get_db_session),
) -> AttendanceSessionService:
    """Injecte le service d'appels."""
    attendance_repo = AttendanceSessionRepository(session)
    user_repo = UserRepository(session)
    return AttendanceSessionService(attendance_repo, user_repo)


# ══════════════════════════════════════════════════════════════════
#  ENDPOINTS - SESSIONS
# ══════════════════════════════════════════════════════════════════


@router.post(
    "/",
    response_model=AttendanceSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une session d'appel",
    description="Crée une nouvelle session d'appel (CENSEUR uniquement)",
)
async def create_session(
    data: AttendanceSessionCreate,
    current_user: User = Depends(require_censeur_strict),
    service: AttendanceSessionService = Depends(get_attendance_service),
):
    """Crée une nouvelle session d'appel."""
    return await service.create_session(data, current_user.id)


@router.get(
    "/",
    response_model=PaginatedResponse[AttendanceSessionResponse],
    summary="Liste des sessions",
    description="Liste paginée des sessions d'appel",
)
async def list_sessions(
    start_date: Optional[datetime] = Query(None, description="Date de début"),
    end_date: Optional[datetime] = Query(None, description="Date de fin"),
    page: int = Query(1, ge=1, description="Numéro de page"),
    page_size: int = Query(50, ge=1, le=100, description="Taille de page"),
    current_user: User = Depends(get_current_user),
    service: AttendanceSessionService = Depends(get_attendance_service),
):
    """Liste les sessions d'appel."""
    return await service.list_sessions(
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{session_id}",
    response_model=AttendanceSessionResponse,
    summary="Détail d'une session",
    description="Récupère les détails d'une session d'appel",
)
async def get_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    service: AttendanceSessionService = Depends(get_attendance_service),
):
    """Récupère une session par son ID."""
    return await service.get_session(session_id)


# ══════════════════════════════════════════════════════════════════
#  ENDPOINTS - ENREGISTREMENTS
# ══════════════════════════════════════════════════════════════════


@router.post(
    "/{session_id}/records",
    response_model=AttendanceRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Marquer la présence",
    description="Marque la présence d'un servant (CENSEUR uniquement)",
)
async def mark_attendance(
    session_id: UUID,
    data: AttendanceRecordCreate,
    current_user: User = Depends(require_censeur),
    service: AttendanceSessionService = Depends(get_attendance_service),
):
    """Marque la présence d'un servant."""
    return await service.mark_attendance(session_id, data, current_user.id)


@router.patch(
    "/records/{record_id}",
    response_model=AttendanceRecordResponse,
    summary="Modifier un enregistrement",
    description="Modifie un enregistrement de présence (CENSEUR uniquement)",
)
async def update_attendance(
    record_id: UUID,
    data: AttendanceRecordUpdate,
    current_user: User = Depends(require_censeur),
    service: AttendanceSessionService = Depends(get_attendance_service),
):
    """Met à jour un enregistrement de présence."""
    return await service.update_attendance(record_id, data)


# ══════════════════════════════════════════════════════════════════
#  ENDPOINTS - STATISTIQUES
# ══════════════════════════════════════════════════════════════════


@router.get(
    "/servants/{servant_id}/stats",
    response_model=ServantAttendanceStatsResponse,
    summary="Statistiques d'un servant",
    description="Calcule les statistiques de présence d'un servant",
)
async def get_servant_stats(
    servant_id: UUID,
    start_date: Optional[datetime] = Query(None, description="Date de début"),
    end_date: Optional[datetime] = Query(None, description="Date de fin"),
    current_user: User = Depends(get_current_user),
    service: AttendanceSessionService = Depends(get_attendance_service),
):
    """Calcule les statistiques de présence d'un servant."""
    return await service.get_servant_stats(servant_id, start_date, end_date)


@router.post(
    "/report",
    response_model=AttendanceReportResponse,
    summary="Générer un rapport",
    description="Génère un rapport de présence (CENSEUR uniquement)",
)
async def generate_report(
    request: AttendanceReportRequest,
    current_user: User = Depends(require_censeur),
    service: AttendanceSessionService = Depends(get_attendance_service),
):
    """Génère un rapport de présence."""
    return await service.generate_report(request, current_user.id)


# ══════════════════════════════════════════════════════════════════
#  ENDPOINTS - LISTE DES SERVANTS
# ══════════════════════════════════════════════════════════════════


@router.get(
    "/servants/list",
    response_model=list[ServantListItem],
    summary="Liste des servants",
    description="Récupère la liste complète des servants pour l'appel",
)
async def get_servants_list(
    current_user: User = Depends(get_current_user),
    service: AttendanceSessionService = Depends(get_attendance_service),
):
    """Récupère la liste complète des servants."""
    return await service.get_servants_list()
