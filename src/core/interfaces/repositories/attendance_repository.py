from datetime import datetime
from typing import Dict, List, Optional, Protocol, Tuple, runtime_checkable
from uuid import UUID

from src.core.entities.attendance import Attendance, AttendanceStatus, AttendanceType


@runtime_checkable
class IAttendanceRepository(Protocol):
    async def get(self, attendance_id: UUID) -> Optional[Attendance]:
        ...

    async def get_by_user_date_type(
        self, user_id: UUID, attendance_date: datetime, attendance_type: AttendanceType
    ) -> Optional[Attendance]:
        ...

    async def list_paginated(
        self,
        *,
        user_id: Optional[UUID] = None,
        attendance_type: Optional[AttendanceType] = None,
        status: Optional[AttendanceStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Attendance], int]:
        ...

    async def get_user_stats(self, user_id: UUID, year: Optional[int] = None) -> Dict:
        ...

    async def enrich_attendance(self, attendance: Attendance) -> Dict:
        ...

    async def enrich_attendances(self, attendances: List[Attendance]) -> List[Dict]:
        ...

    async def create(self, attendance: Attendance) -> Attendance:
        ...

    async def update(self, attendance: Attendance) -> Attendance:
        ...

    async def delete(self, attendance_id: UUID) -> bool:
        ...
