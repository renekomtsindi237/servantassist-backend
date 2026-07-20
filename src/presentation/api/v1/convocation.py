"""
Endpoints du module Convocation — convocation formelle des parents (Art. 48-49).

    POST   /                     Convoquer manuellement les parents d'un servant
    GET    /servant/{id}         Historique des convocations d'un servant
    POST   /{id}/honor           Marquer une convocation comme honoree

Accessible a : Censeur, Secretariat, Admin, Aumonier.
Jamais le parent lui-meme (la convocation est constatee par un responsable,
pas auto-declaree).
"""

from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.convocation_service import ConvocationService
from src.core.entities.user import User
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.convocation_repository import ConvocationRepository
from src.infrastructure.repositories.user_repository import UserRepository
from src.presentation.dependencies.auth_deps import require_convocation_manager
from src.presentation.schemas.convocation import (
    ConvocationCreate,
    ConvocationHonor,
    ConvocationResponse,
)

router = APIRouter()


def _get_service(session: AsyncSession) -> ConvocationService:
    return ConvocationService(
        convocation_repo=ConvocationRepository(session),
        user_repo=UserRepository(session),
    )


@router.post(
    "/",
    response_model=ConvocationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_convocation(
    data: ConvocationCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(require_convocation_manager)],
):
    """
    Convoquer manuellement les parents d'un servant.

    **Accessible a :** Censeur, Secrétariat, Admin, Aumônier.
    """
    service = _get_service(session)
    return await service.create_convocation(data, convened_by=current_user.id)


@router.get(
    "/servant/{servant_id}",
    response_model=List[ConvocationResponse],
)
async def list_servant_convocations(
    servant_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(require_convocation_manager)],
):
    """
    Historique des convocations d'un servant.

    **Accessible a :** Censeur, Secrétariat, Admin, Aumônier.
    """
    service = _get_service(session)
    return await service.list_for_servant(servant_id)


@router.post(
    "/{convocation_id}/honor",
    response_model=ConvocationResponse,
)
async def honor_convocation(
    convocation_id: UUID,
    data: ConvocationHonor,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(require_convocation_manager)],
):
    """
    Marquer une convocation comme honoree (un parent s'est présenté, Art. 49).

    **Accessible a :** Censeur, Secrétariat, Admin, Aumônier.
    """
    service = _get_service(session)
    return await service.mark_honored(convocation_id, honored_by=current_user.id, notes=data.notes)
