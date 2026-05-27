from typing import Dict, List, Optional, Protocol, Tuple, runtime_checkable
from uuid import UUID

from src.core.entities.attendance_session import AttendanceRecord, AttendanceSession


@runtime_checkable
class IAttendanceSessionRepository(Protocol):
    async def create_session(self, session: AttendanceSession) -> AttendanceSession:
        ...

    async def get_session(self, session_id: UUID) -> Optional[AttendanceSession]:
        ...

    async def list_sessions(
        self, *, page: int = 1, page_size: int = 20, **filters
    ) -> Tuple[List[AttendanceSession], int]:
        ...

    async def create_record(self, record: AttendanceRecord) -> AttendanceRecord:
        ...

    async def create_records_batch(
        self, records: List[AttendanceRecord]
    ) -> List[AttendanceRecord]:
        ...

    async def get_record(self, record_id: UUID) -> Optional[AttendanceRecord]:
        ...

    async def get_record_by_session_and_servant(
        self, session_id: UUID, servant_id: UUID
    ) -> Optional[AttendanceRecord]:
        ...

    async def get_session_records(self, session_id: UUID) -> List[AttendanceRecord]:
        ...

    async def get_servant_records(
        self, servant_id: UUID, **filters
    ) -> List[AttendanceRecord]:
        ...

    async def update_record(
        self, record_id: UUID, **kwargs
    ) -> Optional[AttendanceRecord]:
        ...

    async def calculate_servant_stats(self, servant_id: UUID) -> Dict:
        ...

    async def get_all_servants(self) -> List:
        ...

    async def enrich_session(self, session: AttendanceSession) -> Dict:
        ...
