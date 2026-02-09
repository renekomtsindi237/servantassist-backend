"""
Endpoints de gestion des utilisateurs.

Self-service (authentifie) :
    GET    /me                  Mon profil
    PATCH  /me                  Modifier mon profil
    PATCH  /me/password         Changer mon mot de passe
    POST   /me/photo            Uploader ma photo de profil
    DELETE /me/photo            Supprimer ma photo de profil

Administration (admin requis) :
    GET    /                    Liste paginee des utilisateurs
    GET    /{user_id}           Detail d'un utilisateur
    PATCH  /{user_id}           Modifier un utilisateur
    PATCH  /{user_id}/activate  Activer un compte
    PATCH  /{user_id}/deactivate  Desactiver un compte
    POST   /{user_id}/reset-password  Reinitialiser le mot de passe
    DELETE /{user_id}           Supprimer un utilisateur
"""
from datetime import datetime, timezone
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.user_service import UserService
from src.core.entities.user import User, UserRole
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.user_repository import UserRepository
from src.infrastructure.services.storage_service import StorageService
from src.presentation.dependencies.auth_deps import (
    get_current_active_user,
    get_current_admin_user,
)
from src.presentation.schemas.user import (
    ChangePasswordRequest,
    PaginatedResponse,
    UserAdminResetPassword,
    UserAdminUpdate,
    UserProfileResponse,
    UserProfileUpdate,
)

router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────────────────
def _get_user_service(session: AsyncSession) -> UserService:
    return UserService(UserRepository(session))


# ══════════════════════════════════════════════════════════════════════════
#  SELF-SERVICE — l'utilisateur connecte gere son propre profil
# ══════════════════════════════════════════════════════════════════════════


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Recuperer mon profil."""
    return current_user


@router.patch("/me", response_model=UserProfileResponse)
async def update_my_profile(
    data: UserProfileUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Modifier mon profil.

    Champs modifiables : **first_name**, **last_name**, **phone_number**.
    Seuls les champs fournis sont mis a jour (PATCH partiel).
    """
    service = _get_user_service(session)
    return await service.update_profile(current_user, data)


@router.patch("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_my_password(
    data: ChangePasswordRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Changer mon mot de passe.

    L'ancien mot de passe est requis pour verification.
    Le nouveau doit respecter la politique de securite (8+ chars, majuscule, minuscule, chiffre).
    """
    service = _get_user_service(session)
    await service.change_password(current_user, data)


@router.post("/me/photo", response_model=UserProfileResponse)
async def upload_my_photo(
    file: Annotated[UploadFile, File(description="Photo de profil (JPEG, PNG ou WebP, max 5 Mo)")],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Uploader ou remplacer ma photo de profil.

    **Formats acceptes :** JPEG, PNG, WebP
    **Taille max :** 5 Mo

    Si une photo existe deja, elle sera supprimee et remplacee.
    """
    storage = StorageService()

    # Lire le contenu du fichier
    file_data = await file.read()

    # Valider et uploader
    try:
        # Supprimer l'ancienne photo si elle existe
        if current_user.profile_photo_url:
            await storage.delete_profile_photo(current_user.profile_photo_url)

        photo_url = await storage.upload_profile_photo(
            user_id=str(current_user.id),
            file_data=file_data,
            content_type=file.content_type or "image/jpeg",
            filename=file.filename or "photo.jpg",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    # Mettre a jour le profil
    current_user.profile_photo_url = photo_url
    current_user.updated_at = datetime.now(timezone.utc)
    user_repo = UserRepository(session)
    updated_user = await user_repo.update(current_user.id, current_user)
    return updated_user


@router.delete("/me/photo", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_photo(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Supprimer ma photo de profil.
    """
    if not current_user.profile_photo_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune photo de profil a supprimer.",
        )

    storage = StorageService()
    await storage.delete_profile_photo(current_user.profile_photo_url)

    current_user.profile_photo_url = None
    current_user.updated_at = datetime.now(timezone.utc)
    user_repo = UserRepository(session)
    await user_repo.update(current_user.id, current_user)


# ══════════════════════════════════════════════════════════════════════════
#  ADMINISTRATION — reserve aux admins
# ══════════════════════════════════════════════════════════════════════════


@router.get("/", response_model=PaginatedResponse[UserProfileResponse])
async def list_users(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_user)],
    role: Optional[UserRole] = Query(None, description="Filtrer par role"),
    is_active: Optional[bool] = Query(None, description="Filtrer par statut actif"),
    search: Optional[str] = Query(None, max_length=100, description="Recherche par nom ou email"),
    page: int = Query(1, ge=1, description="Numero de page"),
    page_size: int = Query(20, ge=1, le=100, description="Taille de page"),
):
    """
    Liste paginee des utilisateurs avec filtres.

    **Filtres disponibles :**
    - `role` : ADMIN, SERVANT, PARENT, AUMONIER
    - `is_active` : true/false
    - `search` : recherche textuelle (nom, prenom, email)
    - `page` / `page_size` : pagination
    """
    service = _get_user_service(session)
    return await service.list_users(
        role=role,
        is_active=is_active,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get("/{user_id}", response_model=UserProfileResponse)
async def get_user(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_user)],
):
    """Detail d'un utilisateur. Admin uniquement."""
    service = _get_user_service(session)
    return await service.get_user(user_id)


@router.patch("/{user_id}", response_model=UserProfileResponse)
async def admin_update_user(
    user_id: UUID,
    data: UserAdminUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_user)],
):
    """
    Modifier un utilisateur. Admin uniquement.

    Champs modifiables : **first_name**, **last_name**, **email**, **phone_number**, **is_active**.
    """
    service = _get_user_service(session)
    return await service.admin_update_user(user_id, data, current_user)


@router.patch("/{user_id}/deactivate", response_model=UserProfileResponse)
async def deactivate_user(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_user)],
):
    """Desactiver un compte utilisateur. Admin uniquement."""
    service = _get_user_service(session)
    return await service.deactivate_user(user_id, current_user)


@router.patch("/{user_id}/activate", response_model=UserProfileResponse)
async def activate_user(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_user)],
):
    """Reactiver un compte utilisateur. Admin uniquement."""
    service = _get_user_service(session)
    return await service.activate_user(user_id)


@router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def admin_reset_password(
    user_id: UUID,
    data: UserAdminResetPassword,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_user)],
):
    """
    Reinitialiser le mot de passe d'un utilisateur. Admin uniquement.

    Le nouveau mot de passe doit respecter la politique de securite.
    """
    service = _get_user_service(session)
    await service.admin_reset_password(user_id, data)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_user)],
):
    """
    Supprimer un utilisateur. Admin uniquement.

    **Restrictions :**
    - Impossible de se supprimer soi-meme
    - Impossible de supprimer le dernier administrateur
    """
    service = _get_user_service(session)
    await service.delete_user(user_id, current_user)
