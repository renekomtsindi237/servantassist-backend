"""
Endpoints de gestion des API Keys.

- ADMIN : gestion globale (list all, revoke/delete n'importe quelle clé)
- ADMIN/AUMÔNIER : peuvent créer des clés pour leur propre compte
- Tout utilisateur actif : lister et révoquer ses propres clés
"""
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.api_key_service import ApiKeyService
from src.core.entities.user import User, UserRole
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.api_key_repository import ApiKeyRepository
from src.presentation.dependencies.auth_deps import (
    get_current_active_user,
    get_current_admin_user,
)
from src.presentation.schemas.api_key import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyResponse,
)

router = APIRouter()


def _get_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiKeyService:
    return ApiKeyService(ApiKeyRepository(session))


# ── Créer une clé ─────────────────────────────────────────────────────────


@router.post(
    "/",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une API Key",
    description="Génère une nouvelle API Key. La clé brute est retournée une seule fois.",
)
async def create_api_key(
    data: ApiKeyCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    service: Annotated[ApiKeyService, Depends(_get_service)],
):
    api_key, raw_key = await service.create_key(
        user_id=current_user.id,
        name=data.name,
        scopes=data.scopes,
    )
    return ApiKeyCreatedResponse(
        **api_key.model_dump(),
        raw_key=raw_key,
    )


# ── Lister ses propres clés ───────────────────────────────────────────────


@router.get(
    "/me",
    response_model=List[ApiKeyResponse],
    summary="Mes API Keys",
    description="Liste les API Keys de l'utilisateur connecté.",
)
async def list_my_api_keys(
    current_user: Annotated[User, Depends(get_current_active_user)],
    service: Annotated[ApiKeyService, Depends(_get_service)],
):
    return await service.list_user_keys(current_user.id)


# ── Lister toutes les clés (admin) ────────────────────────────────────────


@router.get(
    "/",
    response_model=List[ApiKeyResponse],
    summary="Toutes les API Keys (admin)",
    description="Liste toutes les API Keys — réservé ADMIN.",
)
async def list_all_api_keys(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    service: Annotated[ApiKeyService, Depends(_get_service)],
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return await service.list_all_keys(limit=limit, offset=offset)


# ── Révoquer une clé ─────────────────────────────────────────────────────


@router.post(
    "/{key_id}/revoke",
    response_model=ApiKeyResponse,
    summary="Révoquer une API Key",
    description="Désactive une API Key sans la supprimer.",
)
async def revoke_api_key(
    key_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    service: Annotated[ApiKeyService, Depends(_get_service)],
):
    is_admin = current_user.role == UserRole.ADMIN
    return await service.revoke_key(key_id, current_user.id, is_admin)


# ── Supprimer une clé ─────────────────────────────────────────────────────


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une API Key",
    description="Supprime définitivement une API Key.",
)
async def delete_api_key(
    key_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    service: Annotated[ApiKeyService, Depends(_get_service)],
):
    is_admin = current_user.role == UserRole.ADMIN
    await service.delete_key(key_id, current_user.id, is_admin)
