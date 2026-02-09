"""
Endpoints de gestion des evenements et des participants.

Evenements (Admin / Aumonier) :
    POST   /                          Creer un evenement (avec participants)
    PATCH  /{event_id}                Modifier un evenement
    DELETE /{event_id}                Supprimer un evenement

Evenements (tous les utilisateurs authentifies) :
    GET    /                          Liste paginee des evenements
    GET    /me                        Mes evenements (en tant que participant)
    GET    /{event_id}                Detail d'un evenement + participants

Participants (Admin / Aumonier) :
    POST   /{event_id}/participants                Ajouter un participant
    PATCH  /{event_id}/participants/{id}           Modifier un participant
    DELETE /{event_id}/participants/{id}            Retirer un participant

Participants (self-service) :
    PATCH  /{event_id}/my-participation            Confirmer/decliner ma participation
"""
from datetime import datetime
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.event_service import EventService
from src.core.entities.event import EventStatus, EventType, ParticipantStatus
from src.core.entities.user import User
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.event_repository import EventRepository
from src.infrastructure.repositories.user_repository import UserRepository
from src.presentation.dependencies.auth_deps import (
    get_current_active_user,
    get_current_admin_or_aumonier,
)
from src.presentation.schemas.event import (
    EventCreate,
    EventDetailResponse,
    EventResponse,
    EventUpdate,
    ParticipantAdd,
    ParticipantResponse,
    ParticipantUpdate,
)
from src.presentation.schemas.user import PaginatedResponse

router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────────────────
def _get_event_service(session: AsyncSession) -> EventService:
    return EventService(
        event_repository=EventRepository(session),
        user_repository=UserRepository(session),
    )


# ═══════════════════════════════════════════════════════════════════════════
#  CRUD EVENEMENTS
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/", response_model=PaginatedResponse[EventResponse])
async def list_events(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    event_type: Optional[EventType] = Query(None, description="Filtrer par type"),
    event_status: Optional[EventStatus] = Query(None, alias="status", description="Filtrer par statut"),
    start_date: Optional[datetime] = Query(None, description="Date de debut minimum"),
    end_date: Optional[datetime] = Query(None, description="Date de debut maximum"),
    search: Optional[str] = Query(None, max_length=100, description="Recherche par titre ou lieu"),
    page: int = Query(1, ge=1, description="Numero de page"),
    page_size: int = Query(20, ge=1, le=100, description="Taille de page"),
):
    """
    Liste paginee des evenements avec filtres.

    Accessible a **tous les utilisateurs authentifies**.
    """
    service = _get_event_service(session)
    return await service.list_events(
        event_type=event_type,
        event_status=event_status,
        start_date=start_date,
        end_date=end_date,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get("/me", response_model=List[EventResponse])
async def get_my_events(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Mes evenements (ceux auxquels je participe).

    Accessible a **tous les utilisateurs authentifies**.
    """
    service = _get_event_service(session)
    return await service.get_my_events(current_user.id)


@router.get("/{event_id}", response_model=EventDetailResponse)
async def get_event(
    event_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Detail d'un evenement avec la liste de ses participants.

    Accessible a **tous les utilisateurs authentifies**.
    """
    service = _get_event_service(session)
    return await service.get_event(event_id)


@router.post("/", response_model=EventDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_data: EventCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Creer un evenement avec des participants optionnels.

    **Accessible a :** Admin, Aumonier.

    On peut passer une liste de `participants` directement a la creation
    pour eviter de faire plusieurs appels.
    """
    service = _get_event_service(session)
    return await service.create_event(event_data, created_by=current_user.id)


@router.patch("/{event_id}", response_model=EventDetailResponse)
async def update_event(
    event_id: UUID,
    event_data: EventUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Modifier un evenement existant (modification partielle).

    **Accessible a :** Admin, Aumonier.
    """
    service = _get_event_service(session)
    return await service.update_event(event_id, event_data, updated_by=current_user.id)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Supprimer un evenement et tous ses participants.

    **Accessible a :** Admin, Aumonier.
    """
    service = _get_event_service(session)
    await service.delete_event(event_id)


# ═══════════════════════════════════════════════════════════════════════════
#  GESTION DES PARTICIPANTS
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/{event_id}/participants", response_model=List[ParticipantResponse])
async def list_participants(
    event_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Liste des participants d'un evenement.

    Accessible a **tous les utilisateurs authentifies**.
    """
    service = _get_event_service(session)
    return await service.get_event_participants(event_id)


@router.post(
    "/{event_id}/participants",
    response_model=ParticipantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_participant(
    event_id: UUID,
    data: ParticipantAdd,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Ajouter un participant a un evenement.

    **Accessible a :** Admin, Aumonier.

    Le participant recevra le statut `INVITE` par defaut.
    """
    service = _get_event_service(session)
    return await service.add_participant(event_id, data, added_by=current_user.id)


@router.patch(
    "/{event_id}/participants/{participant_id}",
    response_model=ParticipantResponse,
)
async def update_participant(
    event_id: UUID,
    participant_id: UUID,
    data: ParticipantUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Modifier un participant (role, statut, notes).

    **Accessible a :** Admin, Aumonier.
    """
    service = _get_event_service(session)
    return await service.update_participant(event_id, participant_id, data)


@router.delete(
    "/{event_id}/participants/{participant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_participant(
    event_id: UUID,
    participant_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Retirer un participant d'un evenement.

    **Accessible a :** Admin, Aumonier.
    """
    service = _get_event_service(session)
    await service.remove_participant(event_id, participant_id)


# ═══════════════════════════════════════════════════════════════════════════
#  SELF-SERVICE PARTICIPANT
# ═══════════════════════════════════════════════════════════════════════════


@router.patch("/{event_id}/my-participation", response_model=ParticipantResponse)
async def update_my_participation(
    event_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    new_status: ParticipantStatus = Query(
        ..., description="Nouveau statut : CONFIRME ou DECLINE"
    ),
):
    """
    Confirmer ou decliner ma participation a un evenement.

    **Accessible a :** Tout utilisateur authentifie qui est participant.
    """
    service = _get_event_service(session)
    return await service.update_my_participation(event_id, current_user.id, new_status)
