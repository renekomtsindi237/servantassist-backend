"""
Endpoints de gestion des postes de responsable.

Gestion des nominations :
    POST   /nominations              Nommer un servant a un poste (Aumonier uniquement)
    DELETE /nominations/{id}         Revoquer une nomination (Aumonier uniquement)
    GET    /nominations              Toutes les nominations actives
    GET    /nominations/history      Historique des nominations
    GET    /nominations/me           Mes nominations (servant)

Reference des postes :
    GET    /postes                   Liste de tous les postes (avec titulaires)
    GET    /postes/{poste}           Detail d'un poste

Conseil des Responsables (Art. 12) :
    POST   /council-meetings                        Creer une reunion (Delegue/SG)
    GET    /council-meetings                         Historique paginee des reunions
    POST   /council-meetings/{id}/attendance          Enregistrer les presences (Delegue/SG)
    GET    /council-meetings/{id}/attendance          Presences enregistrees pour une reunion
    GET    /council-meetings/responsable/{id}/monitor Controle d'assiduite (Art. 15)
"""

import asyncio
import logging
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from src.application.services.responsable_service import ResponsableService
from src.core.entities.responsable import PosteResponsable
from src.core.entities.user import User
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.responsable_repository import (
    NominationRepository,
    PosteActionRepository,
)
from src.infrastructure.repositories.user_repository import UserRepository
from src.presentation.dependencies.auth_deps import (
    get_current_active_user,
    get_current_admin_or_aumonier,
    get_current_aumonier_user,
    require_delegue,
    require_delegue_or_sg,
)
from src.presentation.schemas.responsable import (
    CouncilAttendanceRecordList,
    CouncilAttendanceResponse,
    CouncilMeetingCreate,
    CouncilMeetingResponse,
    NominationCreate,
    NominationResponse,
    PosteDetailResponse,
    PosteListResponse,
)
from src.presentation.schemas.user import PaginatedResponse

router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────────────────
def _get_service(session: AsyncSession) -> ResponsableService:
    from src.infrastructure.repositories.council_meeting_repository import (
        CouncilMeetingRepository,
    )

    return ResponsableService(
        nomination_repo=NominationRepository(session),
        action_repo=PosteActionRepository(session),
        user_repo=UserRepository(session),
        council_repo=CouncilMeetingRepository(session),
    )


# ═══════════════════════════════════════════════════════════════════════════
#  NOMINATIONS — Aumonier / Admin
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/nominations",
    response_model=NominationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_nomination(
    data: NominationCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_aumonier_user)],
):
    """
    Nommer un servant a un poste de responsable.

    **Accessible a :** Aumonier uniquement (Art. 2.1 du reglement interieur).

    Validations :
    - L'utilisateur doit etre un SERVANT actif
    - Le poste ne doit pas etre deja occupe
    - Le servant ne doit pas deja occuper un autre poste
    """
    service = _get_service(session)
    nomination = await service.nominate(data, nominated_by=current_user.id)
    asyncio.create_task(
        _notify_nomination(
            nomination.user_id,
            nomination.poste.value if hasattr(nomination.poste, "value") else str(nomination.poste),
            session,
        )
    )
    return nomination


async def _notify_nomination(user_id: UUID, poste_label: str, session) -> None:
    """Notifie un servant de sa nouvelle nomination."""
    try:
        from src.infrastructure.repositories.user_repository import UserRepository
        from src.infrastructure.services.email_service import EmailService

        user_repo = UserRepository(session)
        servant = await user_repo.get(user_id)
        if servant and servant.email:
            await EmailService().send_assignment_notification(
                to_email=servant.email,
                user_first_name=servant.first_name or "Servant",
                event_title="Nouvelle nomination",
                event_date="",
                liturgical_role=poste_label,
            )
    except Exception as exc:
        logger.error("Erreur notification nomination | error=%s", str(exc))


@router.delete(
    "/nominations/{nomination_id}",
    response_model=NominationResponse,
)
async def revoke_nomination(
    nomination_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_aumonier_user)],
):
    """
    Revoquer une nomination (retirer un servant de son poste).

    **Accessible a :** Aumonier uniquement (Art. 2.1 du reglement interieur).
    """
    service = _get_service(session)
    return await service.revoke(nomination_id, revoked_by=current_user.id)


# Self-service (AVANT les routes parametrees)
@router.get("/nominations/me", response_model=List[NominationResponse])
async def get_my_nominations(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Mes nominations actives (pour savoir quel poste j'occupe).

    **Accessible a :** Tout utilisateur authentifie.
    """
    service = _get_service(session)
    return await service.get_my_nominations(current_user.id)


@router.get("/nominations/history", response_model=List[NominationResponse])
async def get_nomination_history(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
    user_id: Optional[UUID] = Query(None, description="Filtrer par servant"),
    poste: Optional[PosteResponsable] = Query(None, description="Filtrer par poste"),
):
    """
    Historique complet des nominations (actives et revoquees).

    **Accessible a :** Aumonier, Admin.
    """
    service = _get_service(session)
    return await service.get_nomination_history(user_id=user_id, poste=poste)


@router.get("/nominations", response_model=List[NominationResponse])
async def list_active_nominations(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Toutes les nominations actives (qui occupe quel poste).

    **Accessible a :** Tout utilisateur authentifie.
    """
    service = _get_service(session)
    return await service.list_active_nominations()


# ═══════════════════════════════════════════════════════════════════════════
#  REFERENCE DES POSTES
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/postes", response_model=PosteListResponse)
async def list_postes(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Liste de tous les postes de responsable avec titulaires et missions.

    **Accessible a :** Tout utilisateur authentifie.
    """
    service = _get_service(session)
    return await service.list_postes()


@router.get("/postes/{poste}", response_model=PosteDetailResponse)
async def get_poste_detail(
    poste: PosteResponsable,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Detail d'un poste (missions, categories autorisees, titulaire actuel).

    **Accessible a :** Tout utilisateur authentifie.
    """
    service = _get_service(session)
    return await service.get_poste_detail(poste)


# ═══════════════════════════════════════════════════════════════════════════
#  CONSEIL DES RESPONSABLES (Art 12, 15)
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/council-meetings",
    response_model=CouncilMeetingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une réunion du conseil",
    description="Accessible au Délégué ou au Secrétaire Général (Art 12)",
)
async def create_council_meeting(
    data: CouncilMeetingCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(require_delegue_or_sg)],
):
    """Crée une réunion du conseil."""
    service = _get_service(session)
    return await service.create_council_meeting(data, created_by=current_user.id)


@router.get(
    "/council-meetings",
    response_model=PaginatedResponse[CouncilMeetingResponse],
    summary="Historique des réunions du conseil",
    description="Liste paginée, les plus récentes d'abord, avec décompte des présences. Accessible au Délégué ou au Secrétaire Général.",  # noqa: E501
)
async def list_council_meetings(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(require_delegue_or_sg)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Historique paginé des réunions du conseil des responsables."""
    service = _get_service(session)
    return await service.list_council_meetings(page=page, page_size=page_size)


@router.post(
    "/council-meetings/{meeting_id}/attendance",
    response_model=List[dict],
    summary="Enregistrer les présences au conseil",
    description="Accessible au Délégué ou au Secrétaire Général",
)
async def record_council_attendance(
    meeting_id: UUID,
    data: CouncilAttendanceRecordList,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(require_delegue_or_sg)],
):
    """Enregistre les présences au conseil."""
    service = _get_service(session)
    return await service.record_council_attendance(meeting_id, data, recorded_by=current_user.id)


@router.get(
    "/council-meetings/{meeting_id}/attendance",
    response_model=List[CouncilAttendanceResponse],
    summary="Présences enregistrées pour une réunion",
    description="Accessible au Délégué ou au Secrétaire Général",
)
async def get_council_attendance(
    meeting_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(require_delegue_or_sg)],
):
    """Liste des présences enregistrées pour une réunion donnée."""
    service = _get_service(session)
    return await service.list_council_attendances(meeting_id)


@router.get(
    "/council-meetings/responsable/{responsable_id}/monitor",
    response_model=dict,
    summary="Contrôler l'assiduité d'un responsable",
    description="Vérifie si le responsable doit être destitué pour 3 absences consécutives (Art 15). Accessible au Délégué.",  # noqa: E501
)
async def monitor_responsable_attendance(
    responsable_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(require_delegue)],
):
    """Lance le contrôle d'assiduité et destitution automatique."""
    service = _get_service(session)
    return await service.monitor_council_attendance(responsable_id)
