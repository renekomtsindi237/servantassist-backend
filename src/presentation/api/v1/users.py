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

from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.user_service import UserService
from src.core.entities.user import User, UserRole
from src.core.utils import utc_now
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.responsable_repository import NominationRepository
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
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Recuperer mon profil."""
    user_repo = UserRepository(session)
    response = UserProfileResponse.model_validate(current_user)
    if current_user.role == UserRole.SERVANT:
        nominations = await NominationRepository(session).get_active_by_user(current_user.id)
        if nominations:
            response.active_poste = nominations[0].poste.value
        response.parent_ids = [p.id for p in await user_repo.get_parents_of(current_user.id)]
    return response


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
            await storage.delete_file(current_user.profile_photo_url)

        photo_url = await storage.upload_profile_photo(
            user_id=str(current_user.id),
            file_data=file_data,
            content_type=file.content_type or "image/jpeg",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    # Mettre a jour le profil
    current_user.profile_photo_url = photo_url
    current_user.updated_at = utc_now()
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
    await storage.delete_file(current_user.profile_photo_url)

    current_user.profile_photo_url = None
    current_user.updated_at = utc_now()
    user_repo = UserRepository(session)
    await user_repo.update(current_user.id, current_user)


@router.post("/me/accept-terms", response_model=UserProfileResponse, status_code=200)
async def accept_terms(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Enregistre l'acceptation des CGU (traçabilité Loi 2024/017)."""
    from src.core.utils import utc_now as _utc_now

    user_repo = UserRepository(session)
    current_user.terms_accepted_at = _utc_now()
    current_user.updated_at = _utc_now()
    updated = await user_repo.update(current_user.id, current_user)
    return UserProfileResponse.model_validate(updated)


@router.post("/me/data-consent", response_model=UserProfileResponse, status_code=200)
async def record_data_consent(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Enregistre le consentement explicite au traitement des données personnelles.

    Conformément à l'article 9 de la Loi n° 2024/017 du 22 décembre 2024 :
    le consentement est libre, spécifique, éclairé et non-ambigu (action positive).
    Le timestamp UTC est enregistré pour traçabilité légale.
    """
    user_repo = UserRepository(session)
    current_user.data_consent_at = utc_now()
    current_user.updated_at = utc_now()
    updated = await user_repo.update(current_user.id, current_user)
    return UserProfileResponse.model_validate(updated)


class SelfLinkParentRequest(BaseModel):
    parent_phone: str


@router.post("/me/link-parent", response_model=UserProfileResponse)
async def self_link_parent(
    data: SelfLinkParentRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Lier le servant connecté à un parent via son numéro de téléphone."""
    if current_user.role != UserRole.SERVANT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Réservé aux servants.")
    user_repo = UserRepository(session)
    parent = await user_repo.get_by_phone(data.parent_phone.strip())
    if not parent or parent.role != UserRole.PARENT:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucun compte parent trouvé avec ce numéro.")
    await user_repo.add_parent_link(current_user.id, parent.id)
    updated = await user_repo.get(current_user.id)
    response = UserProfileResponse.model_validate(updated)
    response.parent_ids = [p.id for p in await user_repo.get_parents_of(current_user.id)]
    return response


@router.delete("/me/link-parent/{parent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def self_unlink_parent(
    parent_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Délier le servant connecté d'un parent."""
    if current_user.role != UserRole.SERVANT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Réservé aux servants.")
    user_repo = UserRepository(session)
    await user_repo.remove_parent_link(current_user.id, parent_id)


# ══════════════════════════════════════════════════════════════════════════
#  RÉPERTOIRE — accessible à tout utilisateur authentifié
# ══════════════════════════════════════════════════════════════════════════


@router.get("/directory", response_model=PaginatedResponse[UserProfileResponse])
async def list_directory(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    role: Optional[UserRole] = Query(None, description="Filtrer par rôle"),
    is_active: Optional[bool] = Query(True, description="Filtrer par statut actif"),
    search: Optional[str] = Query(None, max_length=100, description="Recherche par nom"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """
    Répertoire des membres — accessible à tout utilisateur authentifié.

    Utile pour les pages «Membres», sélecteurs de servant, etc.
    """
    service = _get_user_service(session)
    return await service.list_users(
        role=role,
        is_active=is_active,
        search=search,
        page=page,
        page_size=page_size,
    )


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
    user = await service.get_user(user_id)
    user_repo = UserRepository(session)
    response = UserProfileResponse.model_validate(user)
    if user.role == UserRole.SERVANT:
        response.parent_ids = [p.id for p in await user_repo.get_parents_of(user_id)]
    return response


@router.get("/{user_id}/children", response_model=list[UserProfileResponse])
async def get_user_children(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_user)],
):
    """Servants liés à un parent. Admin uniquement."""
    user_repo = UserRepository(session)
    children = await user_repo.get_children_of(user_id)
    return [UserProfileResponse.model_validate(c) for c in children]


class LinkParentRequest(BaseModel):
    parent_id: Optional[UUID]
    unlink: bool = False


@router.patch("/{user_id}/link-parent", response_model=UserProfileResponse)
async def link_parent(
    user_id: UUID,
    data: LinkParentRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_user)],
):
    """Lier ou délier un servant à un parent. Admin uniquement.
    Pour délier : passer unlink=true + parent_id du parent à retirer.
    Un servant peut avoir au maximum 3 parents."""
    service = _get_user_service(session)
    return await service.link_parent(user_id, data.parent_id, unlink=data.unlink)


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
