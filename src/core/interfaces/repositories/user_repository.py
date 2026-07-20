"""
Interface IUserRepository — contrat du repository utilisateur.
Utilise typing.Protocol (subtyping structurel) : les implémentations concrètes
n'ont pas besoin d'hériter explicitement — elles satisfont le protocole si elles
possèdent les bonnes méthodes.
"""

from typing import List, Optional, Protocol, Tuple, runtime_checkable
from uuid import UUID

from src.core.entities.user import User, UserRole


@runtime_checkable
class IUserRepository(Protocol):
    async def get(self, id: UUID) -> Optional[User]: ...

    async def get_by_email(self, email: str) -> Optional[User]: ...

    async def get_by_phone(self, phone_number: str) -> Optional[User]: ...

    async def get_by_oauth_subject(self, provider: str, subject: str) -> Optional[User]: ...

    async def list(self) -> List[User]: ...

    async def list_paginated(
        self,
        *,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[User], int]: ...

    async def count_by_role(self, role: UserRole) -> int: ...

    async def create(self, user: User) -> User: ...

    async def update(self, id: UUID, entity: User) -> User: ...

    async def delete(self, id: UUID) -> bool: ...

    async def email_exists(self, email: str, exclude_id: Optional[UUID] = None) -> bool: ...

    async def phone_exists(self, phone_number: str, exclude_id: Optional[UUID] = None) -> bool: ...
