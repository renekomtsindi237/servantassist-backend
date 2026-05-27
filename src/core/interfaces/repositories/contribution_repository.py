from typing import Dict, List, Optional, Protocol, Tuple, runtime_checkable
from uuid import UUID

from src.core.entities.contribution import Contribution


@runtime_checkable
class IContributionRepository(Protocol):
    async def create(self, contribution: Contribution) -> Contribution:
        ...

    async def get(self, contribution_id: UUID) -> Optional[Contribution]:
        ...

    async def list(
        self, *, page: int = 1, page_size: int = 20, **filters
    ) -> Tuple[List[Contribution], int]:
        ...

    async def get_servant_contributions(self, user_id: UUID) -> List[Contribution]:
        ...

    async def get_monthly_contributions(
        self, year: int, month: int
    ) -> List[Contribution]:
        ...

    async def update(self, contribution_id: UUID, **kwargs) -> Optional[Contribution]:
        ...

    async def delete(self, contribution_id: UUID) -> bool:
        ...

    async def get_monthly_summary(self, year: int, month: int) -> Dict:
        ...

    async def calculate_period_stats(self, **filters) -> Dict:
        ...

    async def enrich_contribution(self, contribution: Contribution) -> Dict:
        ...
