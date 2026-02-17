from typing import Generic, List, Optional, TypeVar
from uuid import UUID

from sqlmodel import SQLModel

T = TypeVar("T", bound=SQLModel)


class IRepository(Generic[T]):
    async def get(self, id: UUID) -> Optional[T]:
        raise NotImplementedError

    async def list(self) -> List[T]:
        raise NotImplementedError

    async def create(self, entity: T) -> T:
        raise NotImplementedError

    async def update(self, id: UUID, entity: T) -> T:
        raise NotImplementedError

    async def delete(self, id: UUID) -> bool:
        raise NotImplementedError
