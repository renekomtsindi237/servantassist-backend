"""
User queries — lectures utilisateur (CQRS).

Séparées de UserService (commandes) pour permettre :
- Optimisation indépendante (cache par rôle, etc.)
- Réutilisation dans le dashboard et les rapports
- Testabilité isolée des lectures
"""
from typing import List, Optional
from uuid import UUID

from src.core.entities.user import User, UserRole
from src.core.interfaces.repositories import IUserRepository


class UserListQuery:
    """Lecture paginée et filtrée des utilisateurs."""

    def __init__(self, user_repository: IUserRepository) -> None:
        self._repo = user_repository

    async def execute(
        self,
        *,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[User], int]:
        """Retourne (users, total_count)."""
        return await self._repo.list_paginated(
            role=role,
            is_active=is_active,
            search=search,
            page=page,
            page_size=page_size,
        )


class UserStatsQuery:
    """Statistiques d'effectif par rôle."""

    def __init__(self, user_repository: IUserRepository) -> None:
        self._repo = user_repository

    async def execute(self) -> dict:
        """Retourne le compte de chaque rôle."""
        counts = {}
        for role in UserRole:
            counts[role.value] = await self._repo.count_by_role(role)
        counts["total"] = sum(counts.values())
        return counts


class UserSearchQuery:
    """
    Recherche d'un utilisateur par critère.
    Utilisée par les dropdowns et l'autocomplétion.
    """

    def __init__(self, user_repository: IUserRepository) -> None:
        self._repo = user_repository

    async def by_id(self, user_id: UUID) -> Optional[User]:
        return await self._repo.get(user_id)

    async def by_email(self, email: str) -> Optional[User]:
        return await self._repo.get_by_email(email)

    async def by_phone(self, phone_number: str) -> Optional[User]:
        return await self._repo.get_by_phone(phone_number)
