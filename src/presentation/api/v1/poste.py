"""
Endpoints d'actions par poste de responsable.

Chaque responsable accede a ses propres endpoints via le prefixe de son poste :
    /api/v1/poste/{slug}/dashboard     Tableau de bord
    /api/v1/poste/{slug}/actions       CRUD des actions

Slugs disponibles :
    conseiller, delegue, vice-delegue, secretariat, secretariat-adjoint,
    censeur, censeur-adjoint, economat, finances, liturgie, liturgie-adjoint,
    ceremoniaire, classement-dimanche, classement-semaine, intendance,
    sport-culture

L'Aumonier et l'Admin peuvent aussi acceder a tous les postes en lecture.
"""
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.responsable_service import ResponsableService
from src.core.entities.responsable import SLUG_TO_POSTE, ActionCategory, ActionStatus, PosteResponsable
from src.core.entities.user import User, UserRole
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.responsable_repository import NominationRepository, PosteActionRepository
from src.infrastructure.repositories.user_repository import UserRepository
from src.presentation.dependencies.auth_deps import get_current_active_user
from src.presentation.schemas.responsable import (
    PosteActionCreate,
    PosteActionResponse,
    PosteActionUpdate,
    PosteDashboardResponse,
)
from src.presentation.schemas.user import PaginatedResponse

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


def _resolve_slug(slug: str) -> PosteResponsable:
    """Convertit un slug URL en PosteResponsable ou leve 404."""
    poste = SLUG_TO_POSTE.get(slug)
    if not poste:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Poste inconnu : '{slug}'. Slugs valides : {', '.join(SLUG_TO_POSTE.keys())}",
        )
    return poste


async def _verify_poste_access(
    session: AsyncSession,
    user: User,
    poste: PosteResponsable,
) -> None:
    """
    Verifie que l'utilisateur a acces au poste :
    - Admin / Aumonier : acces total (lecture et ecriture)
    - Servant avec nomination active pour ce poste : acces total
    - Sinon : 403
    """
    if user.role in (UserRole.ADMIN, UserRole.AUMÔNIER):
        return  # Acces total

    nom_repo = NominationRepository(session)
    nomination = await nom_repo.get_active_by_user_and_poste(user.id, poste)
    if not nomination:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Vous n'occupez pas le poste de {poste.value}. Acces refuse.",
        )


async def _verify_write_access(
    session: AsyncSession,
    user: User,
    poste: PosteResponsable,
) -> None:
    """
    Verifie que l'utilisateur peut ecrire pour ce poste :
    - Admin / Aumonier : autorise
    - Servant avec nomination active : autorise
    - Sinon : 403
    """
    if user.role in (UserRole.ADMIN, UserRole.AUMÔNIER):
        return

    nom_repo = NominationRepository(session)
    nomination = await nom_repo.get_active_by_user_and_poste(user.id, poste)
    if not nomination:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Vous n'occupez pas le poste de {poste.value}. "
                f"Seul le responsable nomme peut effectuer cette action."
            ),
        )


# ═══════════════════════════════════════════════════════════════════════════
#  TABLEAU DE BORD
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/{slug}/dashboard", response_model=PosteDashboardResponse)
async def get_poste_dashboard(
    slug: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Tableau de bord d'un poste de responsable.

    Affiche les missions, statistiques d'actions et actions recentes.

    **Accessible a :** Le responsable concerne, Aumonier, Admin.
    """
    poste = _resolve_slug(slug)
    await _verify_poste_access(session, current_user, poste)
    service = _get_service(session)
    return await service.get_dashboard(poste)


# ═══════════════════════════════════════════════════════════════════════════
#  ACTIONS — CRUD
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/{slug}/actions",
    response_model=PosteActionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_action(
    slug: str,
    data: PosteActionCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Creer une action pour ce poste.

    **Accessible a :** Le responsable nomme a ce poste, Aumonier, Admin.

    La categorie doit faire partie des categories autorisees pour ce poste.
    """
    poste = _resolve_slug(slug)
    await _verify_write_access(session, current_user, poste)
    service = _get_service(session)
    return await service.create_action(poste, data, created_by=current_user.id)


@router.get(
    "/{slug}/actions",
    response_model=PaginatedResponse[PosteActionResponse],
)
async def list_actions(
    slug: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    category: Optional[ActionCategory] = Query(
    None, description="Filtrer par categorie"),
    action_status: Optional[ActionStatus] = Query(
    None, alias="status", description="Filtrer par statut"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Liste paginee des actions d'un poste.

    **Accessible a :** Le responsable concerne, Aumonier, Admin.
    """
    poste = _resolve_slug(slug)
    await _verify_poste_access(session, current_user, poste)
    service = _get_service(session)
    return await service.list_actions(
        poste,
        category=category,
        action_status=action_status,
        page=page,
        page_size=page_size,
    )


@router.get("/{slug}/actions/{action_id}", response_model=PosteActionResponse)
async def get_action(
    slug: str,
    action_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Detail d'une action.

    **Accessible a :** Le responsable concerne, Aumonier, Admin.
    """
    poste = _resolve_slug(slug)
    await _verify_poste_access(session, current_user, poste)
    service = _get_service(session)
    return await service.get_action(action_id)


@router.patch("/{slug}/actions/{action_id}",
              response_model=PosteActionResponse)
async def update_action(
    slug: str,
    action_id: UUID,
    data: PosteActionUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Modifier une action.

    **Accessible a :** Le createur de l'action uniquement (ou Admin/Aumonier).
    """
    poste = _resolve_slug(slug)
    await _verify_write_access(session, current_user, poste)
    service = _get_service(session)
    return await service.update_action(action_id, data, updated_by=current_user.id)


@router.delete(
    "/{slug}/actions/{action_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_action(
    slug: str,
    action_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Supprimer une action.

    **Accessible a :** Le createur de l'action uniquement (ou Admin/Aumonier).
    """
    poste = _resolve_slug(slug)
    await _verify_write_access(session, current_user, poste)
    service = _get_service(session)
    await service.delete_action(action_id, deleted_by=current_user.id)
