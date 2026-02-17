"""
Endpoints de gestion des postes de responsable (Aumonier / Admin).

Gestion des nominations :
    POST   /nominations              Nommer un servant a un poste
    DELETE /nominations/{id}         Revoquer une nomination
    GET    /nominations              Toutes les nominations actives
    GET    /nominations/history      Historique des nominations
    GET    /nominations/me           Mes nominations (servant)

Reference des postes :
    GET    /postes                   Liste de tous les postes (avec titulaires)
    GET    /postes/{poste}           Detail d'un poste
"""
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

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
    require_delegue,
    require_delegue_or_sg,
)
from src.presentation.schemas.responsable import (
    NominationCreate,
    NominationResponse,
    PosteDetailResponse,
    PosteListResponse,
    CouncilMeetingCreate,
    CouncilMeetingResponse,
    CouncilAttendanceRecordList,
)

router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────────────────
def _get_service(session: AsyncSession) -> ResponsableService:
    from src.infrastructure.repositories.council_meeting_repository import CouncilMeetingRepository
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
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Nommer un servant a un poste de responsable.

    **Accessible a :** Aumonier, Admin.

    Validations :
    - L'utilisateur doit etre un SERVANT actif
    - Le poste ne doit pas etre deja occupe
    - Le servant ne doit pas deja occuper un autre poste
    """
    service = _get_service(session)
    return await service.nominate(data, nominated_by=current_user.id)


@router.delete(
    "/nominations/{nomination_id}",
    response_model=NominationResponse,
)
async def revoke_nomination(
    nomination_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Revoquer une nomination (retirer un servant de son poste).

    **Accessible a :** Aumonier, Admin.
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
    return await service.record_council_attendance(meeting_id, data)


@router.get(
    "/council-meetings/responsable/{responsable_id}/monitor",
    response_model=dict,
    summary="Contrôler l'assiduité d'un responsable",
    description="Vérifie si le responsable doit être destitué pour 3 absences consécutives (Art 15). Accessible au Délégué.",
)
async def monitor_responsable_attendance(
    responsable_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(require_delegue)],
):
    """Lance le contrôle d'assiduité et destitution automatique."""
    service = _get_service(session)
    return await service.monitor_council_attendance(responsable_id)

