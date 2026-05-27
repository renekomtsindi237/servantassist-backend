from typing import List, Optional, Protocol, runtime_checkable
from uuid import UUID

from src.core.entities.api_key import ApiKey


@runtime_checkable
class IApiKeyRepository(Protocol):
    async def create(self, api_key: ApiKey) -> ApiKey:
        ...

    async def get_by_id(self, key_id: UUID) -> Optional[ApiKey]:
        ...

    async def get_by_user(self, user_id: UUID) -> List[ApiKey]:
        ...

    async def list_all(self, limit: int = 50, offset: int = 0) -> List[ApiKey]:
        ...

    async def revoke(self, key_id: UUID) -> Optional[ApiKey]:
        ...

    async def delete(self, key_id: UUID) -> bool:
        ...

    async def touch(self, key_id: UUID) -> None:
        ...
