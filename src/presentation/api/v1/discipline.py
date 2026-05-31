"""
Endpoints du module Discipline — Conseil de discipline & Sanctions.

Gestion des dossiers disciplinaires :
    POST   /                     Ouvrir un dossier
    GET    /                     Lister les dossiers (pagine)
    GET    /{id}                 Detail d'un dossier
    POST   /{id}/convoke         Convoquer au conseil de discipline
    POST   /{id}/hearing         Ouvrir l'audience
    POST   /{id}/verdict         Rendre le verdict
    POST   /{id}/execute         Executer la sanction
    POST   /{id}/dismiss         Classer sans suite
    GET    /user/{user_id}/stats Statistiques disciplinaires d'un servant

Accessible a : Aumonier, Admin (toutes operations)
               Censeur/Censeur adjoint (ouverture de dossier, convocation)
"""

import asyncio
import logging
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

logger = logging.getLogger(__name__)
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.discipline_service import DisciplineService
from src.core.entities.discipline import (
    DisciplineCaseStatus,
    OffenseCategory,
    SanctionSeverity,
)
from src.core.entities.user import User, UserRole
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.discipline_repository import (
    DisciplineCaseRepository,
)
from src.infrastructure.repositories.responsable_repository import NominationRepository
from src.infrastructure.repositories.user_repository import UserRepository
from src.presentation.dependencies.auth_deps import (
    get_current_active_user,
    get_current_admin_or_aumonier,
    require_censeur,
)
from src.presentation.schemas.discipline import (
    DisciplineCaseCreate,
    DisciplineCaseResponse,
    DisciplineConvocation,
    DisciplineStatsResponse,
    DisciplineVerdict,
)
from src.presentation.schemas.user import PaginatedResponse

router = APIRouter()


def _get_service(session: AsyncSession) -> DisciplineService:
    from src.infrastructure.repositories.attendance_repository import (
        AttendanceRepository,
    )

    return DisciplineService(
        case_repo=DisciplineCaseRepository(session),
        user_repo=UserRepository(session),
        attendance_repo=AttendanceRepository(session),
    )


# ═══════════════════════════════════════════════════════════════════════════
#  ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/",
    response_model=DisciplineCaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def open_discipline_case(
    data: DisciplineCaseCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(require_censeur)],
):
    """
    Ouvrir un dossier disciplinaire a l'encontre d'un servant.

    **Rôles autorisés** :
    - CENSEUR (via nomination active)
    - CENSEUR_ADJOINT (via nomination active)
    - ADMIN
    - AUMÔNIER
    """
    service = _get_service(session)
    case = await service.open_case(data, reported_by=current_user.id)
    # Notifier le parent via WhatsApp (fire-and-forget)
    asyncio.create_task(_notify_parent_discipline(data.accused_user_id, data.offense_category, session))
    return case


async def _notify_parent_discipline(accused_id: UUID, offense_category, session) -> None:
    """Notifie le parent d'un servant via WhatsApp qu'un dossier disciplinaire a été ouvert."""
    try:
        user_repo = UserRepository(session)
        servant = await user_repo.get(accused_id)
        if servant and servant.parent_id:
            parent = await user_repo.get(servant.parent_id)
            if parent and parent.phone_number:
                from src.infrastructure.services.whatsapp_service import WhatsAppService

                child_name = f"{servant.first_name or ''} {servant.last_name or ''}".strip() or "votre enfant"
                category_label = offense_category.value if hasattr(offense_category, "value") else str(offense_category)
                await WhatsAppService().send_child_discipline_alert(
                    phone_number=parent.phone_number,
                    child_name=child_name,
                    offense_category=category_label,
                )
    except Exception as exc:
        logger.error("Erreur notification discipline parent | error=%s", str(exc))


# ═══════════════════════════════════════════════════════════════════════════
#  WORKFLOW DISCIPLINAIRE
# ═══════════════════════════════════════════════════════════════════════════


@router.post("/{case_id}/convoke", response_model=DisciplineCaseResponse)
async def convoke_to_council(
    case_id: UUID,
    data: DisciplineConvocation,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(require_censeur)],
):
    """
    Convoquer le servant au conseil de discipline.

    **Rôles autorisés** :
    - CENSEUR (via nomination active)
    - CENSEUR_ADJOINT (via nomination active)
    - ADMIN
    - AUMÔNIER
    """
    service = _get_service(session)
    return await service.convoke(case_id, data)


@router.post("/{case_id}/hearing", response_model=DisciplineCaseResponse)
async def start_hearing(
    case_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(require_censeur)],
):
    """
    Ouvrir l'audience du conseil de discipline.

    **Rôles autorisés** :
    - CENSEUR (via nomination active)
    - CENSEUR_ADJOINT (via nomination active)
    - ADMIN
    - AUMÔNIER
    """
    service = _get_service(session)
    return await service.start_hearing(case_id)


@router.post("/{case_id}/verdict", response_model=DisciplineCaseResponse)
async def render_verdict(
    case_id: UUID,
    data: DisciplineVerdict,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(require_censeur)],
):
    """
    Rendre le verdict du conseil de discipline.

    **Rôles autorisés** :
    - CENSEUR (via nomination active)
    - CENSEUR_ADJOINT (via nomination active)
    - ADMIN
    - AUMÔNIER
    """
    service = _get_service(session)
    return await service.render_verdict(case_id, data, verdict_by=current_user.id)


@router.post("/{case_id}/execute", response_model=DisciplineCaseResponse)
async def execute_sanction(
    case_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(require_censeur)],
):
    """
    Executer la sanction (application effective).

    En cas d'exclusion definitive, le compte du servant est desactive.

    **Rôles autorisés** :
    - CENSEUR (via nomination active)
    - CENSEUR_ADJOINT (via nomination active)
    - ADMIN
    - AUMÔNIER
    """
    service = _get_service(session)
    return await service.execute_sanction(case_id)


@router.post("/{case_id}/dismiss", response_model=DisciplineCaseResponse)
async def dismiss_case(
    case_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(require_censeur)],
    notes: Optional[str] = Query(None, max_length=2000),
):
    """
    Classer le dossier sans suite.

    **Rôles autorisés** :
    - CENSEUR (via nomination active)
    - CENSEUR_ADJOINT (via nomination active)
    - ADMIN
    - AUMÔNIER
    """
    service = _get_service(session)
    return await service.dismiss_case(case_id, notes=notes)


# ═══════════════════════════════════════════════════════════════════════════
#  LECTURE
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/", response_model=PaginatedResponse[DisciplineCaseResponse])
async def list_discipline_cases(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(require_censeur)],
    accused_user_id: Optional[UUID] = Query(None),
    case_status: Optional[DisciplineCaseStatus] = Query(None, alias="status"),
    severity: Optional[SanctionSeverity] = Query(None),
    offense_category: Optional[OffenseCategory] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Lister les dossiers disciplinaires (pagine, filtrable).

    **Rôles autorisés** :
    - CENSEUR (via nomination active)
    - CENSEUR_ADJOINT (via nomination active)
    - ADMIN
    - AUMÔNIER
    """
    service = _get_service(session)
    return await service.list_cases(
        accused_user_id=accused_user_id,
        case_status=case_status,
        severity=severity,
        offense_category=offense_category,
        page=page,
        page_size=page_size,
    )


@router.get("/{case_id}", response_model=DisciplineCaseResponse)
async def get_discipline_case(
    case_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(require_censeur)],
):
    """
    Detail d'un dossier disciplinaire.

    **Rôles autorisés** :
    - CENSEUR (via nomination active)
    - CENSEUR_ADJOINT (via nomination active)
    - ADMIN
    - AUMÔNIER
    """
    service = _get_service(session)
    return await service.get_case(case_id)


@router.get(
    "/user/{user_id}/stats",
    response_model=DisciplineStatsResponse,
)
async def get_user_discipline_stats(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(require_censeur)],
):
    """
    Statistiques disciplinaires d'un servant.

    **Rôles autorisés** :
    - CENSEUR (via nomination active)
    - CENSEUR_ADJOINT (via nomination active)
    - ADMIN
    - AUMÔNIER
    """
    service = _get_service(session)
    return await service.get_user_discipline_stats(user_id)


@router.get(
    "/user/{user_id}/compliance",
    response_model=dict,
    summary="Vérifier l'assiduité",
    description="Vérifie si le servant respecte les règles d'assiduité (Art 42, 50)",
)
async def get_attendance_compliance(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(require_censeur)],
):
    """Vérifie la conformité de l'assiduité."""
    service = _get_service(session)
    return await service.check_attendance_compliance(user_id)
