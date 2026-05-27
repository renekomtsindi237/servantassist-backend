from typing import Dict, List, Optional, Protocol, Tuple, runtime_checkable
from uuid import UUID

from src.core.entities.weekly_schedule import (
    SlotServantAssignment,
    WeeklyScheduleSlot,
    WeeklyScheduleTemplate,
)


@runtime_checkable
class IWeeklyScheduleRepository(Protocol):
    async def create_template(
        self, template: WeeklyScheduleTemplate
    ) -> WeeklyScheduleTemplate:
        ...

    async def get_template(self, template_id: UUID) -> Optional[WeeklyScheduleTemplate]:
        ...

    async def update_template(
        self, template_id: UUID, **kwargs
    ) -> Optional[WeeklyScheduleTemplate]:
        ...

    async def delete_template(self, template_id: UUID) -> bool:
        ...

    async def list_templates(
        self, *, page: int = 1, page_size: int = 20, **filters
    ) -> Tuple[List[WeeklyScheduleTemplate], int]:
        ...

    async def get_published_templates(self) -> List[WeeklyScheduleTemplate]:
        ...

    async def create_slot(self, slot: WeeklyScheduleSlot) -> WeeklyScheduleSlot:
        ...

    async def get_slot(self, slot_id: UUID) -> Optional[WeeklyScheduleSlot]:
        ...

    async def update_slot(
        self, slot_id: UUID, **kwargs
    ) -> Optional[WeeklyScheduleSlot]:
        ...

    async def delete_slot(self, slot_id: UUID) -> bool:
        ...

    async def get_template_slots(self, template_id: UUID) -> List[WeeklyScheduleSlot]:
        ...

    async def create_assignment(
        self, assignment: SlotServantAssignment
    ) -> SlotServantAssignment:
        ...

    async def get_assignment(
        self, assignment_id: UUID
    ) -> Optional[SlotServantAssignment]:
        ...

    async def get_slot_assignments(self, slot_id: UUID) -> List[SlotServantAssignment]:
        ...

    async def delete_assignment(self, assignment_id: UUID) -> bool:
        ...

    async def enrich_template(self, template: WeeklyScheduleTemplate) -> Dict:
        ...

    async def enrich_slot(self, slot: WeeklyScheduleSlot) -> Dict:
        ...

    async def enrich_assignment(self, assignment: SlotServantAssignment) -> Dict:
        ...

    async def get_template_summary(self, template_id: UUID) -> Dict:
        ...
