from datetime import datetime
from typing import Dict, List, Optional, Protocol, Tuple, runtime_checkable
from uuid import UUID

from src.core.entities.discipline import (
    DisciplineCase,
    DisciplineCaseStatus,
    DisciplineCaseVote,
    OffenseCategory,
    SanctionSeverity,
    SanctionType,
)


@runtime_checkable
class IDisciplineCaseRepository(Protocol):
    async def get(self, case_id: UUID) -> Optional[DisciplineCase]: ...

    async def list_paginated(
        self,
        *,
        accused_user_id: Optional[UUID] = None,
        status: Optional[DisciplineCaseStatus] = None,
        severity: Optional[SanctionSeverity] = None,
        offense_category: Optional[OffenseCategory] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[DisciplineCase], int]: ...

    async def list_by_user(self, user_id: UUID) -> List[DisciplineCase]: ...

    async def count_sanctions_by_user(self, user_id: UUID) -> Dict[str, int]: ...

    async def count_active_cases(self, user_id: UUID) -> int: ...

    async def count_by_offense_category_since(
        self, user_id: UUID, category: OffenseCategory, since: datetime
    ) -> int: ...

    async def enrich_case(self, case: DisciplineCase) -> Dict: ...

    async def enrich_cases(self, cases: List[DisciplineCase]) -> List[Dict]: ...

    async def create(self, case: DisciplineCase) -> DisciplineCase: ...

    async def update(self, case: DisciplineCase) -> DisciplineCase: ...

    async def delete(self, case_id: UUID) -> bool: ...

    async def upsert_vote(
        self,
        case_id: UUID,
        poste: str,
        voter_user_id: UUID,
        sanction_type: SanctionType,
        notes: Optional[str] = None,
    ) -> DisciplineCaseVote: ...

    async def list_votes(self, case_id: UUID) -> List[DisciplineCaseVote]: ...

    async def delete_votes(self, case_id: UUID) -> None: ...
