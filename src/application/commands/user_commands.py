"""
User commands — modifications utilisateur (CQRS).

Chaque command encapsule une intention métier précise.
Elle délègue l'exécution à UserService (compatible avec l'existant),
émet des événements et peut être retentée ou journalisée.

Pattern : Command = intention + handler inline.
Pour une architecture plus formelle, on peut séparer Command (DTO)
et CommandHandler (exécuteur). Ici on les fusionne pour garder
la simplicité sur un système de taille modérée.
"""

from dataclasses import dataclass
from uuid import UUID

from src.application.services.user_service import UserService
from src.core.entities.user import User
from src.core.interfaces.repositories import IUserRepository
from src.presentation.schemas.user import UserAdminResetPassword


@dataclass
class RegisterUserCommand:
    """
    Crée un nouvel utilisateur.
    Point d'entrée CQRS propre — délègue à AuthService.
    """

    # Données de création injectées à l'exécution
    pass  # Voir AuthService.register_user() — déjà complet


@dataclass
class ResetPasswordCommand:
    """Réinitialise le mot de passe d'un utilisateur (admin only)."""

    user_id: UUID
    new_password: str
    admin: User

    async def execute(self, service: UserService) -> None:
        await service.admin_reset_password(
            self.user_id,
            UserAdminResetPassword(new_password=self.new_password),
        )


@dataclass
class DeactivateUserCommand:
    """Désactive un compte utilisateur."""

    user_id: UUID
    admin: User

    async def execute(self, service: UserService) -> User:
        return await service.deactivate_user(self.user_id, self.admin)


@dataclass
class ActivateUserCommand:
    """Active un compte utilisateur."""

    user_id: UUID

    async def execute(self, service: UserService) -> User:
        return await service.activate_user(self.user_id)


@dataclass
class DeleteUserCommand:
    """Supprime un compte utilisateur."""

    user_id: UUID
    admin: User

    async def execute(self, service: UserService) -> None:
        await service.delete_user(self.user_id, self.admin)
