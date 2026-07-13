"""
Repository pour le Conseil des Responsables.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.core.entities.council_meeting import CouncilAttendance, CouncilMeeting


class CouncilMeetingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_meeting(self, meeting: CouncilMeeting) -> CouncilMeeting:
        self.session.add(meeting)
        await self.session.commit()
        await self.session.refresh(meeting)
        return meeting

    async def get_meeting(self, meeting_id: UUID) -> Optional[CouncilMeeting]:
        return await self.session.get(CouncilMeeting, meeting_id)

    async def add_attendance(self, attendance: CouncilAttendance) -> CouncilAttendance:
        self.session.add(attendance)
        await self.session.commit()
        await self.session.refresh(attendance)
        return attendance

    async def get_responsable_attendances(self, responsable_id: UUID, limit: int = 3) -> List[CouncilAttendance]:
        """Récupère les dernières présences d'un responsable."""
        stmt = (
            select(CouncilAttendance)
            .where(CouncilAttendance.responsable_id == responsable_id)
            .order_by(CouncilAttendance.recorded_at.desc())
            .limit(limit)
        )
        result = await self.session.exec(stmt)
        return result.all()
