"""
Service metier pour la gestion des utilisateurs.

Regles :
- Un utilisateur peut modifier son propre profil (nom, prenom, telephone).
- Un utilisateur peut changer son mot de passe (ancien mot de passe requis).
- L'admin peut modifier n'importe quel utilisateur.
- L'admin peut activer/desactiver un compte.
- L'admin peut reinitialiser un mot de passe.
- L'admin ne peut pas se desactiver lui-meme.
- On ne peut pas supprimer le dernier ADMIN.
- Les emails et telephones restent uniques.
"""

import math
from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status

from src.core.entities.user import User, UserRole
from src.core.utils import utc_now
from src.core.events.domain_events import (
    PasswordReset,
    UserActivated,
    UserDeactivated,
    UserDeleted,
)
from src.core.interfaces.repositories import IUserRepository
from src.infrastructure.events.bus import event_bus
from src.infrastructure.security.utils import SecurityUtils
from src.presentation.schemas.user import (
    ChangePasswordRequest,
    PaginatedResponse,
    UserAdminResetPassword,
    UserAdminUpdate,
    UserProfileResponse,
    UserProfileUpdate,
)


class UserService:
    def __init__(self, user_repository: IUserRepository):
        self.user_repository = user_repository

    # ══════════════════════════════════════════════════════════════════
    #  SELF-SERVICE (l'utilisateur connecte)
    # ══════════════════════════════════════════════════════════════════

    async def get_profile(self, user: User) -> User:
        """Retourne le profil de l'utilisateur connecte."""
        return user

    async def update_profile(self, user: User, data: UserProfileUpdate) -> User:
        """
        Mise a jour du profil par l'utilisateur lui-meme.
        Seuls first_name, last_name, phone_number sont modifiables.
        """
        # Verifier l'unicite du telephone si modifie
        if data.phone_number is not None and data.phone_number != user.phone_number:
            if data.phone_number != "" and await self.user_repository.phone_exists(
                data.phone_number, exclude_id=user.id
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Ce numero de telephone est deja utilise par un autre compte.",
                )

        # Appliquer les modifications (seuls les champs fournis)
        if data.first_name is not None:
            user.first_name = data.first_name
        if data.last_name is not None:
            user.last_name = data.last_name
        if data.phone_number is not None:
            user.phone_number = data.phone_number if data.phone_number != "" else None

        user.updated_at = utc_now()
        return await self.user_repository.update(user.id, user)

    async def change_password(self, user: User, data: ChangePasswordRequest) -> None:
        """
        Changement de mot de passe par l'utilisateur.
        L'ancien mot de passe est requis pour verification.
        """
        # Verifier l'ancien mot de passe
        if not SecurityUtils.verify_password(data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le mot de passe actuel est incorrect.",
            )

        # Verifier que le nouveau mot de passe est different
        if SecurityUtils.verify_password(data.new_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le nouveau mot de passe doit etre different de l'ancien.",
            )

        user.hashed_password = SecurityUtils.get_password_hash(data.new_password)
        user.updated_at = utc_now()
        await self.user_repository.update(user.id, user)

    # ══════════════════════════════════════════════════════════════════
    #  ADMINISTRATION (reserve a l'admin)
    # ══════════════════════════════════════════════════════════════════

    async def list_users(
        self,
        *,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[UserProfileResponse]:
        """Liste paginee des utilisateurs avec filtres."""
        users, total = await self.user_repository.list_paginated(
            role=role,
            is_active=is_active,
            search=search,
            page=page,
            page_size=page_size,
        )
        total_pages = math.ceil(total / page_size) if total > 0 else 1
        return PaginatedResponse(
            items=[UserProfileResponse.model_validate(u) for u in users],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_user(self, user_id: UUID) -> User:
        """Recupere un utilisateur par son ID."""
        user = await self.user_repository.get(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur introuvable.",
            )
        return user

    async def admin_update_user(self, user_id: UUID, data: UserAdminUpdate, admin: User) -> User:
        """
        Mise a jour d'un utilisateur par l'admin.
        Peut modifier email, nom, prenom, telephone, statut actif.
        """
        user = await self.get_user(user_id)

        # Verifier l'unicite de l'email si modifie
        if data.email is not None and data.email != user.email:
            if await self.user_repository.email_exists(data.email, exclude_id=user.id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cet email est deja utilise par un autre compte.",
                )
            user.email = data.email

        # Verifier l'unicite du telephone si modifie
        if data.phone_number is not None and data.phone_number != user.phone_number:
            if data.phone_number != "" and await self.user_repository.phone_exists(
                data.phone_number, exclude_id=user.id
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Ce numero de telephone est deja utilise par un autre compte.",
                )
            user.phone_number = data.phone_number if data.phone_number != "" else None

        if data.first_name is not None:
            user.first_name = data.first_name
        if data.last_name is not None:
            user.last_name = data.last_name
        if data.position is not None:
            user.position = data.position

        # Activation / desactivation
        if data.is_active is not None and data.is_active != user.is_active:
            # L'admin ne peut pas se desactiver lui-meme
            if user.id == admin.id and not data.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Vous ne pouvez pas desactiver votre propre compte.",
                )
            user.is_active = data.is_active

        user.updated_at = utc_now()
        return await self.user_repository.update(user.id, user)

    async def link_parent(self, servant_id: UUID, parent_id: Optional[UUID]) -> User:
        """Lie ou délie un servant à un parent."""
        servant = await self.get_user(servant_id)
        if servant.role != UserRole.SERVANT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seul un SERVANT peut être lié à un parent.",
            )
        if parent_id is not None:
            parent = await self.get_user(parent_id)
            if parent.role != UserRole.PARENT:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="L'utilisateur cible doit avoir le rôle PARENT.",
                )
        servant.parent_id = parent_id
        servant.updated_at = utc_now()
        return await self.user_repository.update(servant.id, servant)

    async def deactivate_user(self, user_id: UUID, admin: User) -> User:
        """Desactive un compte utilisateur."""
        user = await self.get_user(user_id)

        if user.id == admin.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vous ne pouvez pas desactiver votre propre compte.",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce compte est deja desactive.",
            )

        user.is_active = False
        user.updated_at = utc_now()
        result = await self.user_repository.update(user.id, user)
        await event_bus.publish(UserDeactivated(user_id=user_id, deactivated_by_id=admin.id))
        return result

    async def activate_user(self, user_id: UUID) -> User:
        """Reactive un compte utilisateur."""
        user = await self.get_user(user_id)

        if user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce compte est deja actif.",
            )

        user.is_active = True
        user.updated_at = utc_now()
        result = await self.user_repository.update(user.id, user)
        await event_bus.publish(UserActivated(user_id=user_id))
        return result

    async def admin_reset_password(self, user_id: UUID, data: UserAdminResetPassword) -> None:
        """Reinitialisation forcee du mot de passe par l'admin."""
        user = await self.get_user(user_id)
        user.hashed_password = SecurityUtils.get_password_hash(data.new_password)
        user.updated_at = utc_now()
        await self.user_repository.update(user.id, user)
        await event_bus.publish(PasswordReset(user_id=user_id))

    async def delete_user(self, user_id: UUID, admin: User) -> None:
        """
        Suppression d'un utilisateur.
        Regles :
        - L'admin ne peut pas se supprimer lui-meme
        - On ne peut pas supprimer le dernier admin
        """
        user = await self.get_user(user_id)

        if user.id == admin.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vous ne pouvez pas supprimer votre propre compte.",
            )

        # Verifier qu'on ne supprime pas le dernier admin
        if user.role == UserRole.ADMIN:
            admin_count = await self.user_repository.count_by_role(UserRole.ADMIN)
            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Impossible de supprimer le dernier administrateur.",
                )

        deleted = await self.user_repository.delete(user_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la suppression de l'utilisateur.",
            )
        await event_bus.publish(UserDeleted(user_id=user_id, deleted_by_id=admin.id))
