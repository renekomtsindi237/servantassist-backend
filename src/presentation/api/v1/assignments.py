"""
Endpoints de gestion des affectations liturgiques.

Planification (Admin / Aumonier) :
    POST   /                              Creer une affectation
    POST   /batch                         Creer plusieurs affectations
    GET    /                              Liste paginee avec filtres
    GET    /{assignment_id}               Detail d'une affectation
    GET    /event/{event_id}              Affectations d'un evenement
    PATCH  /{assignment_id}               Modifier une affectation
    PATCH  /{assignment_id}/presence      Marquer presence/absence
    PATCH  /{assignment_id}/cancel        Annuler une affectation
    DELETE /{assignment_id}               Supprimer une affectation

Self-service (Servant authentifie) :
    GET    /me                            Mes affectations
    GET    /me/upcoming                   Mes affectations a venir
    PATCH  /{assignment_id}/my-status     Accepter/decliner
"""
from datetime import datetime
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.assignment_service import AssignmentService
from src.core.entities.assignment import AssignmentStatus, LiturgicalRole
from src.core.entities.user import User
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.assignment_repository import AssignmentRepository
from src.infrastructure.repositories.event_repository import EventRepository
from src.infrastructure.repositories.user_repository import UserRepository
from src.presentation.dependencies.auth_deps import get_current_active_user, get_current_admin_or_aumonier
from src.presentation.schemas.assignment import (
    AssignmentBatchCreate,
    AssignmentBatchResponse,
    AssignmentCreate,
    AssignmentResponse,
    AssignmentStatusUpdate,
    AssignmentUpdate,
)
from src.presentation.schemas.user import PaginatedResponse

router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────────────────
def _get_service(session: AsyncSession) -> AssignmentService:
    return AssignmentService(
        assignment_repository=AssignmentRepository(session),
        event_repository=EventRepository(session),
        user_repository=UserRepository(session),
    )


# ═══════════════════════════════════════════════════════════════════════════
#  CREATION — Admin / Aumonier
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED
)
async def create_assignment(
    data: AssignmentCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Creer une affectation liturgique.

    **Accessible a :** Admin, Aumonier.

    Validations :
    - L'evenement doit exister
    - L'utilisateur doit etre un SERVANT actif
    - Pas de doublon (meme servant + meme evenement + meme role)
    """
    service = _get_service(session)
    return await service.create_assignment(data, assigned_by=current_user.id)


@router.post(
    "/batch",
    response_model=AssignmentBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_batch_assignments(
    data: AssignmentBatchCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Creer plusieurs affectations pour un evenement en une seule requete.

    **Accessible a :** Admin, Aumonier.

    Chaque affectation est traitee independamment : une erreur sur l'une
    n'empeche pas la creation des autres. Le rapport contient les affectations
    creees et les erreurs.
    """
    service = _get_service(session)
    return await service.create_batch(data, assigned_by=current_user.id)


# ═══════════════════════════════════════════════════════════════════════════
#  SELF-SERVICE — Servant  (AVANT les routes parametrees /{id})
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/me", response_model=List[AssignmentResponse])
async def get_my_assignments(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Toutes mes affectations (historique complet).

    **Accessible a :** Tout utilisateur authentifie.
    """
    service = _get_service(session)
    return await service.get_my_assignments(current_user.id)


@router.get("/me/upcoming", response_model=List[AssignmentResponse])
async def get_my_upcoming_assignments(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Mes affectations a venir (evenements futurs, statut PENDING ou ACCEPTED).

    **Accessible a :** Tout utilisateur authentifie.
    """
    service = _get_service(session)
    return await service.get_my_upcoming(current_user.id)


# ═══════════════════════════════════════════════════════════════════════════
#  LECTURE — Admin / Aumonier
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/", response_model=PaginatedResponse[AssignmentResponse])
async def list_assignments(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
    event_id: Optional[UUID] = Query(None, description="Filtrer par evenement"),
    user_id: Optional[UUID] = Query(None, description="Filtrer par servant"),
    assignment_status: Optional[AssignmentStatus] = Query(
        None, alias="status", description="Filtrer par statut"
    ),
    liturgical_role: Optional[LiturgicalRole] = Query(
        None, description="Filtrer par role liturgique"
    ),
    start_date: Optional[datetime] = Query(
        None, description="Evenements a partir de cette date"
    ),
    end_date: Optional[datetime] = Query(
        None, description="Evenements jusqu'a cette date"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Liste paginee de toutes les affectations avec filtres.

    **Accessible a :** Admin, Aumonier.

    **Filtres disponibles :**
    - ``event_id`` : affectations d'un evenement specifique
    - ``user_id`` : affectations d'un servant specifique
    - ``status`` : PENDING, ACCEPTED, DECLINED, PRESENT, ABSENT, CANCELLED
    - ``liturgical_role`` : CRUCIFER, THURIFER, ACOLYTE, etc.
    - ``start_date`` / ``end_date`` : plage de dates des evenements
    """
    service = _get_service(session)
    return await service.list_assignments(
        event_id=event_id,
        user_id=user_id,
        assignment_status=assignment_status,
        liturgical_role=liturgical_role,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )


@router.get("/event/{event_id}", response_model=List[AssignmentResponse])
async def get_event_assignments(
    event_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Toutes les affectations actives d'un evenement.

    **Accessible a :** Tout utilisateur authentifie.
    """
    service = _get_service(session)
    return await service.get_event_assignments(event_id)


@router.get("/{assignment_id}", response_model=AssignmentResponse)
async def get_assignment(
    assignment_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Detail d'une affectation.

    **Accessible a :** Tout utilisateur authentifie.
    """
    service = _get_service(session)
    return await service.get_assignment(assignment_id)


@router.patch(
    "/{assignment_id}/my-status",
    response_model=AssignmentResponse,
)
async def update_my_assignment_status(
    assignment_id: UUID,
    data: AssignmentStatusUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Accepter ou decliner une affectation qui m'est attribuee.

    **Accessible a :** Le servant concerne uniquement.

    Seules les transitions suivantes sont autorisees :
    - PENDING → ACCEPTED
    - PENDING → DECLINED
    """
    service = _get_service(session)
    return await service.update_my_status(assignment_id, data, user_id=current_user.id)


# ═══════════════════════════════════════════════════════════════════════════
#  MODIFICATION — Admin / Aumonier
# ═══════════════════════════════════════════════════════════════════════════


@router.patch("/{assignment_id}", response_model=AssignmentResponse)
async def update_assignment(
    assignment_id: UUID,
    data: AssignmentUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Modifier une affectation (role, statut, notes).

    **Accessible a :** Admin, Aumonier.
    """
    service = _get_service(session)
    return await service.update_assignment(
        assignment_id, data, updated_by=current_user.id
    )


@router.patch(
    "/{assignment_id}/presence",
    response_model=AssignmentResponse,
)
async def mark_presence(
    assignment_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
    present: bool = Query(..., description="true = PRESENT, false = ABSENT"),
):
    """
    Marquer la presence ou l'absence d'un servant le jour J.

    **Accessible a :** Admin, Aumonier.
    """
    service = _get_service(session)
    return await service.mark_presence(
        assignment_id, present=present, marked_by=current_user.id
    )


@router.patch(
    "/{assignment_id}/cancel",
    response_model=AssignmentResponse,
)
async def cancel_assignment(
    assignment_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Annuler une affectation (soft-delete, reste dans l'historique).

    **Accessible a :** Admin, Aumonier.
    """
    service = _get_service(session)
    return await service.cancel_assignment(assignment_id, cancelled_by=current_user.id)


# ═══════════════════════════════════════════════════════════════════════════
#  SUPPRESSION — Admin / Aumonier
# ═══════════════════════════════════════════════════════════════════════════


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    assignment_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Supprimer definitivement une affectation.

    **Accessible a :** Admin, Aumonier.

    Pour une suppression logique (garder l'historique), utilisez
    ``PATCH /{id}/cancel`` a la place.
    """
    service = _get_service(session)
    await service.delete_assignment(assignment_id)
