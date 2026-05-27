"""
Endpoints du module Cotisations — contributions financieres.

Periodes de cotisation :
    POST   /periods              Creer une periode
    GET    /periods              Lister les periodes
    GET    /periods/{id}         Detail d'une periode
    PATCH  /periods/{id}         Modifier une periode
    DELETE /periods/{id}         Supprimer une periode
    GET    /periods/{id}/bilan   Bilan financier d'une periode

Paiements :
    POST   /payments             Enregistrer un paiement
    GET    /periods/{id}/payments  Paiements d'une periode
    GET    /my                   Mes cotisations (self-service)

Accessible a : Aumonier, Admin (toutes operations)
               Econome (enregistrement de paiements via son poste)
               Tout utilisateur (consulter ses propres cotisations)
"""

from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.cotisation_service import CotisationService
from src.core.entities.cotisation import CotisationType
from src.core.entities.user import User
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.cotisation_repository import (
    CotisationPeriodRepository,
    MemberCotisationRepository,
)
from src.infrastructure.repositories.user_repository import UserRepository
from src.presentation.dependencies.auth_deps import (
    get_current_active_user,
    get_current_admin_or_aumonier,
    require_econome,
)
from src.presentation.schemas.cotisation import (
    CotisationBilanResponse,
    CotisationPeriodCreate,
    CotisationPeriodResponse,
    CotisationPeriodUpdate,
    MemberCotisationCreate,
    MemberCotisationResponse,
)
from src.presentation.schemas.user import PaginatedResponse

router = APIRouter()


def _get_service(session: AsyncSession) -> CotisationService:
    return CotisationService(
        period_repo=CotisationPeriodRepository(session),
        payment_repo=MemberCotisationRepository(session),
        user_repo=UserRepository(session),
    )


# ═══════════════════════════════════════════════════════════════════════════
#  PERIODES
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/periods",
    response_model=CotisationPeriodResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_period(
    data: CotisationPeriodCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Creer une nouvelle periode de cotisation.

    **Accessible a :** Aumonier, Admin.
    """
    service = _get_service(session)
    return await service.create_period(data, created_by=current_user.id)


@router.get(
    "/periods",
    response_model=PaginatedResponse[CotisationPeriodResponse],
)
async def list_periods(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    cotisation_type: Optional[CotisationType] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Lister les periodes de cotisation.

    **Accessible a :** Tout utilisateur authentifie.
    """
    service = _get_service(session)
    return await service.list_periods(
        cotisation_type=cotisation_type,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )


@router.get("/periods/{period_id}", response_model=CotisationPeriodResponse)
async def get_period(
    period_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Detail d'une periode de cotisation.

    **Accessible a :** Tout utilisateur authentifie.
    """
    service = _get_service(session)
    return await service.get_period(period_id)


@router.patch(
    "/periods/{period_id}",
    response_model=CotisationPeriodResponse,
)
async def update_period(
    period_id: UUID,
    data: CotisationPeriodUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Modifier une periode de cotisation.

    **Accessible a :** Aumonier, Admin.
    """
    service = _get_service(session)
    return await service.update_period(period_id, data)


@router.delete(
    "/periods/{period_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_period(
    period_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Supprimer une periode de cotisation.

    **Accessible a :** Aumonier, Admin.
    """
    service = _get_service(session)
    await service.delete_period(period_id)


@router.get(
    "/periods/{period_id}/bilan",
    response_model=CotisationBilanResponse,
)
async def get_period_bilan(
    period_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(require_econome)],
):
    """
    Bilan financier d'une periode de cotisation.

    **Rôles autorisés** :
    - ECONOME (via nomination active)
    - ADMIN
    - AUMÔNIER

    **Contenu du bilan** :
    - Total collecté
    - Nombre de cotisants
    - Détail par cotisant
    - Taux de participation
    """
    service = _get_service(session)
    return await service.get_bilan(period_id)


# ═══════════════════════════════════════════════════════════════════════════
#  PAIEMENTS
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/payments",
    response_model=MemberCotisationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_payment(
    data: MemberCotisationCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(require_econome)],
):
    """
    Enregistrer un paiement de cotisation.

    Si un paiement existe deja pour cette periode et cet utilisateur,
    le montant sera ajoute (paiement supplementaire).

    **Rôles autorisés** :
    - ECONOME (via nomination active)
    - ADMIN
    - AUMÔNIER

    **Processus** :
    1. Vérifier l'accès ECONOME (nomination active ou ADMIN/AUMÔNIER)
    2. Enregistrer le paiement en base de données
    3. Retourner l'objet créé

    **Réponse 201** : Paiement enregistré
    **Réponse 403** : Non autorisé (pas ECONOME)
    **Réponse 400** : Validation échouée
    """
    service = _get_service(session)
    return await service.record_payment(data, recorded_by=current_user.id)


@router.get(
    "/periods/{period_id}/payments",
    response_model=List[MemberCotisationResponse],
)
async def get_period_payments(
    period_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(require_econome)],
):
    """
    Paiements d'une periode de cotisation.

    **Rôles autorisés** :
    - ECONOME (via nomination active)
    - ADMIN
    - AUMÔNIER

    **Visibilité** :
    - Les ECONOME voient TOUS les paiements de la période
    - ADMIN/AUMÔNIER voient aussi tous les paiements
    """
    service = _get_service(session)
    return await service.get_period_payments(period_id)


@router.get(
    "/my",
    response_model=List[MemberCotisationResponse],
)
async def get_my_cotisations(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Mes cotisations (historique de paiements).

    **Accessible a :** Tout utilisateur authentifie.
    """
    service = _get_service(session)
    return await service.get_user_payments(current_user.id)
