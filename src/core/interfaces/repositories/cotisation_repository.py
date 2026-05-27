from typing import Dict, List, Optional, Protocol, runtime_checkable
from uuid import UUID

from src.core.entities.cotisation import CotisationPeriod, MemberCotisation


@runtime_checkable
class ICotisationPeriodRepository(Protocol):
    async def get(self, period_id: UUID) -> Optional[CotisationPeriod]:
        ...

    async def list_active(self) -> List[CotisationPeriod]:
        ...

    async def list_all(
        self, *, page: int = 1, page_size: int = 20
    ) -> List[CotisationPeriod]:
        ...

    async def create(self, period: CotisationPeriod) -> CotisationPeriod:
        ...

    async def update(self, period: CotisationPeriod) -> CotisationPeriod:
        ...

    async def delete(self, period_id: UUID) -> bool:
        ...


@runtime_checkable
class IMemberCotisationRepository(Protocol):
    async def get(self, cotisation_id: UUID) -> Optional[MemberCotisation]:
        ...

    async def get_by_period_and_user(
        self, period_id: UUID, user_id: UUID
    ) -> Optional[MemberCotisation]:
        ...

    async def list_by_period(self, period_id: UUID) -> List[MemberCotisation]:
        ...

    async def list_by_user(self, user_id: UUID) -> List[MemberCotisation]:
        ...

    async def get_period_stats(self, period_id: UUID) -> Dict:
        ...

    async def enrich_cotisation(self, cotisation: MemberCotisation) -> Dict:
        ...

    async def create(self, cotisation: MemberCotisation) -> MemberCotisation:
        ...

    async def update(self, cotisation: MemberCotisation) -> MemberCotisation:
        ...

    async def delete(self, cotisation_id: UUID) -> bool:
        ...
