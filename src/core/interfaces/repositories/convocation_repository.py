from typing import List, Optional, Protocol, runtime_checkable
from uuid import UUID

from src.core.entities.convocation import Convocation, ConvocationMotif


@runtime_checkable
class IConvocationRepository(Protocol):
    async def get(self, convocation_id: UUID) -> Optional[Convocation]: ...

    async def create(self, convocation: Convocation) -> Convocation: ...

    async def update(self, convocation: Convocation) -> Convocation: ...

    async def list_by_servant(self, servant_id: UUID) -> List[Convocation]: ...

    async def get_pending_by_servant_and_motif(
        self, servant_id: UUID, motif: ConvocationMotif
    ) -> Optional[Convocation]: ...

    async def list_pending_past_deadline(self) -> List[Convocation]: ...
