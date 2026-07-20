"""
Endpoints du module Discipline — Conseil de discipline & Sanctions.

Gestion des dossiers disciplinaires :
    POST   /                     Ouvrir un dossier
    GET    /                     Lister les dossiers (pagine)
    GET    /{id}                 Detail d'un dossier
    POST   /{id}/convoke         Convoquer au conseil de discipline
    POST   /{id}/hearing         Ouvrir l'audience
    POST   /{id}/votes           Voter (membre du conseil de discipline, Art. 16-17)
    GET    /{id}/votes           Etat d'avancement du vote collegial
    POST   /{id}/verdict         Rendre directement un verdict (override Aumonier)
    POST   /{id}/execute         Executer la sanction
    POST   /{id}/dismiss         Classer sans suite
    GET    /user/{user_id}/stats Statistiques disciplinaires d'un servant

Accessible a : Aumonier, Admin (toutes operations)
               Censeur/Censeur adjoint (ouverture de dossier, convocation)
               Ceremoniaire (ouverture de dossier — Art. 41)
               Delegue/Vice-Delegue (convocation — Art. 16)
               Conseil de discipline (7 sieges, vote collegial)
               Verdict direct : Aumonier (tout type), Censeur/Censeur Adjoint/
               Secretaire General/Ceremoniaire (selon le type de sanction)
"""

import asyncio
import logging
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

logger = logging.getLogger(__name__)
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.discipline_service import DisciplineService
from src.application.services.notification_service import NotificationService
from src.core.entities.discipline import (
    DisciplineCaseStatus,
    OffenseCategory,
    SanctionSeverity,
)
from src.core.entities.notification import NotificationChannel, NotificationPriority, NotificationType
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
    require_convoke_discipline,
    require_discipline_council_member,
    require_open_discipline_case,
    require_verdict_authority,
)
from src.presentation.schemas.discipline import (
    DisciplineCaseCreate,
    DisciplineCaseResponse,
    DisciplineConvocation,
    DisciplineStatsResponse,
    DisciplineVerdict,
    DisciplineVoteCast,
    DisciplineVoteStatusResponse,
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
        nomination_repo=NominationRepository(session),
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
    request: Request,
    data: DisciplineCaseCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(require_open_discipline_case)],
):
    """
    Ouvrir un dossier disciplinaire a l'encontre d'un servant.

    **Rôles autorisés** :
    - CENSEUR (via nomination active)
    - CENSEUR_ADJOINT (via nomination active)
    - CEREMONIAIRE (via nomination active) — trouble durant la célébration eucharistique (Art. 41)
    - ADMIN
    - AUMÔNIER
    """
    service = _get_service(session)
    case = await service.open_case(data, reported_by=current_user.id)
    ws_manager = getattr(request.app.state, "ws_manager", None)
    asyncio.create_task(_notify_parent_discipline(data.accused_user_id, data.offense_category, session, ws_manager))
    return case


async def _notify_parent_discipline(accused_id: UUID, offense_category, session, ws_manager=None) -> None:
    """Crée une notification in-app pour TOUS les parents d'un servant sanctionné."""
    try:
        user_repo = UserRepository(session)
        servant = await user_repo.get(accused_id)
        if not servant:
            return
        parents = await user_repo.get_parents_of(servant.id)
        if not parents:
            return
        child_name = f"{servant.first_name or ''} {servant.last_name or ''}".strip() or "votre enfant"
        category_label = offense_category.value if hasattr(offense_category, "value") else str(offense_category)
        notif_svc = NotificationService(session, ws_manager=ws_manager)
        for parent in parents:
            await notif_svc.send_notification(
                recipient_id=parent.id,
                notification_type=NotificationType.DISCIPLINE,
                channel=NotificationChannel.IN_APP,
                priority=NotificationPriority.URGENT,
                title="Dossier disciplinaire ouvert",
                body=f"Un dossier disciplinaire a été ouvert pour {child_name} (motif : {category_label}).",
                related_entity_type="discipline_case",
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
    current_user: Annotated[User, Depends(require_convoke_discipline)],
):
    """
    Convoquer le servant au conseil de discipline.

    **Rôles autorisés** :
    - CENSEUR (via nomination active)
    - CENSEUR_ADJOINT (via nomination active)
    - DELEGUE (via nomination active) — Art. 16 : "sous convocation du responsable Délégué"
    - VICE_DELEGUE (via nomination active)
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
    current_user: Annotated[User, Depends(require_verdict_authority)],
):
    """
    Rendre directement un verdict, sans attendre le quorum du conseil
    (`POST /{case_id}/votes`).

    L'Aumonier garde le dernier mot sur tout type de sanction. Les autres
    responsables sont limites a certains types de sanction selon le
    règlement :
    - CENSEUR : tout type (punitions courantes Art. 39-44 ET radiation Art. 51)
    - CENSEUR_ADJOINT : punitions courantes uniquement (pas la radiation)
    - SECRETAIRE_GENERAL : radiation (EXCLUSION_DEFINITIVE) uniquement (Art. 51)
    - CEREMONIAIRE : punitions mineures uniquement (Art. 41 — trouble durant la messe)

    **Rôles autorisés** :
    - AUMÔNIER (tout type de sanction)
    - CENSEUR, CENSEUR_ADJOINT, SECRETAIRE_GENERAL, CEREMONIAIRE (selon le type de sanction)
    """
    service = _get_service(session)
    return await service.render_verdict(case_id, data, decider=current_user)


@router.post("/{case_id}/votes", response_model=DisciplineCaseResponse)
async def cast_council_vote(
    case_id: UUID,
    data: DisciplineVoteCast,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(require_discipline_council_member)],
):
    """
    Voter en tant que membre du conseil de discipline (Art. 16-17).

    Le verdict est rendu automatiquement des qu'une majorite simple des
    sieges actuellement pourvus (parmi les 7 du conseil : Delegue, Vice-
    Delegue, Secretaire General, Secretaire General Adjoint, Censeur,
    Censeur Adjoint, Ceremoniaire) se prononce pour la meme sanction. Un
    siege vacant ne bloque pas le quorum. Un revote ecrase le choix
    precedent du meme siege.

    **Rôles autorisés** :
    - Titulaire actif de l'un des 7 sieges du conseil de discipline
    """
    service = _get_service(session)
    return await service.cast_vote(case_id, current_user, data)


@router.get("/{case_id}/votes", response_model=DisciplineVoteStatusResponse)
async def get_council_vote_status(
    case_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(require_censeur)],
):
    """
    Etat d'avancement du vote collegial sur un dossier.

    **Rôles autorisés** :
    - CENSEUR (via nomination active)
    - CENSEUR_ADJOINT (via nomination active)
    - ADMIN
    - AUMÔNIER
    """
    service = _get_service(session)
    return await service.get_vote_status(case_id)


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
