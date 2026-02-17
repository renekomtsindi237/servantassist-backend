"""
Endpoints du module Sous-groupes — organisation interne.

Sous-groupes :
    POST   /                       Creer un sous-groupe
    GET    /                       Lister les sous-groupes
    GET    /{id}                   Detail d'un sous-groupe
    PATCH  /{id}                   Modifier un sous-groupe
    DELETE /{id}                   Supprimer un sous-groupe

Membres :
    POST   /{id}/members           Ajouter un servant
    DELETE /{id}/members/{user_id} Retirer un servant

Self-service :
    GET    /my                     Mon sous-groupe actuel

Accessible a : Aumonier, Admin (toutes operations)
               Tout servant (consulter son sous-groupe)
"""
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.subgroup_service import SubGroupService
from src.core.entities.user import User
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.subgroup_repository import SubGroupRepository
from src.infrastructure.repositories.user_repository import UserRepository
from src.presentation.dependencies.auth_deps import get_current_active_user, get_current_admin_or_aumonier
from src.presentation.schemas.subgroup import (
    SubGroupCreate,
    SubGroupMemberAdd,
    SubGroupMemberResponse,
    SubGroupResponse,
    SubGroupUpdate,
)

router = APIRouter()


def _get_service(session: AsyncSession) -> SubGroupService:
    from src.infrastructure.repositories.training_repository import TrainingParticipationRepository

    return SubGroupService(
        group_repo=SubGroupRepository(session),
        user_repo=UserRepository(session),
        training_repo=TrainingParticipationRepository(session),
    )


# ═══════════════════════════════════════════════════════════════════════════
#  SELF-SERVICE (AVANT les routes parametrees)
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/my", response_model=Optional[SubGroupResponse])
async def get_my_subgroup(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Mon sous-groupe actuel (null si aucun).

    **Accessible a :** Tout utilisateur authentifie.
    """
    service = _get_service(session)
    return await service.get_my_group(current_user.id)


# ═══════════════════════════════════════════════════════════════════════════
#  CRUD SOUS-GROUPES
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/",
    response_model=SubGroupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_subgroup(
    data: SubGroupCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Creer un sous-groupe.

    **Accessible a :** Aumonier, Admin.
    """
    service = _get_service(session)
    return await service.create_group(data, created_by=current_user.id)


@router.get("/", response_model=List[SubGroupResponse])
async def list_subgroups(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    active_only: bool = Query(
        True, description="Afficher uniquement les sous-groupes actifs"
    ),
):
    """
    Lister les sous-groupes.

    **Accessible a :** Tout utilisateur authentifie.
    """
    service = _get_service(session)
    return await service.list_groups(active_only=active_only)


@router.get("/{group_id}", response_model=SubGroupResponse)
async def get_subgroup(
    group_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Detail d'un sous-groupe.

    **Accessible a :** Tout utilisateur authentifie.
    """
    service = _get_service(session)
    return await service.get_group(group_id)


@router.patch("/{group_id}", response_model=SubGroupResponse)
async def update_subgroup(
    group_id: UUID,
    data: SubGroupUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Modifier un sous-groupe.

    **Accessible a :** Aumonier, Admin.
    """
    service = _get_service(session)
    return await service.update_group(group_id, data)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subgroup(
    group_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Supprimer un sous-groupe.

    **Accessible a :** Aumonier, Admin.
    """
    service = _get_service(session)
    await service.delete_group(group_id)


# ═══════════════════════════════════════════════════════════════════════════
#  GESTION DES MEMBRES
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/{group_id}/members",
    response_model=SubGroupMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    group_id: UUID,
    data: SubGroupMemberAdd,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Ajouter un servant a un sous-groupe.

    Validations :
    - L'utilisateur doit etre un SERVANT actif
    - Le servant ne doit pas deja etre dans un autre sous-groupe
    - Le sous-groupe ne doit pas avoir atteint sa capacite maximale

    **Accessible a :** Aumonier, Admin.
    """
    service = _get_service(session)
    return await service.add_member(group_id, data, added_by=current_user.id)


@router.delete(
    "/{group_id}/members/{user_id}",
    response_model=SubGroupMemberResponse,
)
async def remove_member(
    group_id: UUID,
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Retirer un servant d'un sous-groupe.

    **Accessible a :** Aumonier, Admin.
    """
    service = _get_service(session)
    return await service.remove_member(group_id, user_id)


@router.post(
    "/members/{user_id}/reclassify",
    response_model=Optional[SubGroupResponse],
    summary="Reclassifier un servant",
    description="Applique les règles d'âge et de notes pour changer de sous-groupe (Art 26)",
)
async def reclassify_servant(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """Reclassifie un servant selon le RI."""
    service = _get_service(session)
    return await service.reclassify_servant(user_id)
