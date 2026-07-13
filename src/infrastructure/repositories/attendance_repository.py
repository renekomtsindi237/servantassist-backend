"""
Repository pour le suivi de présence.

Chiffrement PII (Loi 2024/017 Cameroun) :
  Le champ justification peut contenir des raisons de santé ou personnelles —
  il est chiffré (Art. 5 données sensibles, santé).
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import String, cast, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.core.entities.attendance import Attendance, AttendanceStatus, AttendanceType
from src.core.entities.user import User
from src.infrastructure.security.encrypted_model_mixin import EncryptedModelMixin
from src.infrastructure.security.field_encryption import decrypt_str_fields

_USER_PII = ("first_name", "last_name")


class AttendanceRepository(EncryptedModelMixin):
    ENCRYPTED_FIELDS = ("justification",)

    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Lecture ────────────────────────────────────────────────────────

    async def get(self, attendance_id: UUID) -> Optional[Attendance]:
        stmt = select(Attendance).where(Attendance.id == attendance_id)
        result = await self.session.exec(stmt)
        att = result.first()
        if att:
            self._decrypt_model(att)
        return att

    async def get_by_user_date_type(
        self, user_id: UUID, attendance_date: datetime, attendance_type: AttendanceType
    ) -> Optional[Attendance]:
        """Verifie si un enregistrement existe deja pour cet utilisateur, date et type."""
        stmt = select(Attendance).where(
            Attendance.user_id == user_id,
            Attendance.attendance_date == attendance_date,
            Attendance.attendance_type == attendance_type,
        )
        result = await self.session.exec(stmt)
        return result.first()

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
        stmt = select(Attendance)

        if user_id:
            stmt = stmt.where(Attendance.user_id == user_id)
        if attendance_type:
            stmt = stmt.where(Attendance.attendance_type == attendance_type)
        if status:
            stmt = stmt.where(cast(Attendance.status, String) == status.value)
        if start_date:
            stmt = stmt.where(Attendance.attendance_date >= start_date)
        if end_date:
            stmt = stmt.where(Attendance.attendance_date <= end_date)
        if event_id:
            stmt = stmt.where(Attendance.event_id == event_id)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.exec(count_stmt)).one()

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size).order_by(Attendance.attendance_date.desc())
        result = await self.session.exec(stmt)
        atts = list(result.all())
        self._decrypt_list(atts)
        return atts, total

    async def get_user_stats(
        self,
        user_id: UUID,
        *,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, int]:
        """Statistiques de presence d'un utilisateur."""
        counts = {}
        for s in AttendanceStatus:
            stmt = select(func.count()).where(
                Attendance.user_id == user_id,
                cast(Attendance.status, String) == s.value,
            )
            if start_date:
                stmt = stmt.where(Attendance.attendance_date >= start_date)
            if end_date:
                stmt = stmt.where(Attendance.attendance_date <= end_date)
            result = await self.session.exec(stmt)
            counts[s.value] = result.one()
        return counts

    # ── Enrichissement ─────────────────────────────────────────────────

    async def enrich_attendance(self, attendance: Attendance) -> Dict:
        user = (await self.session.exec(select(User).where(User.id == attendance.user_id))).first()
        if user:
            decrypt_str_fields(user, _USER_PII)

        return {
            "id": attendance.id,
            "user_id": attendance.user_id,
            "event_id": attendance.event_id,
            "attendance_type": attendance.attendance_type,
            "attendance_date": attendance.attendance_date,
            "title": attendance.title,
            "status": attendance.status,
            "justification": attendance.justification,
            "justified_at": attendance.justified_at,
            "recorded_by": attendance.recorded_by,
            "created_at": attendance.created_at,
            "updated_at": attendance.updated_at,
            "user_first_name": user.first_name if user else None,
            "user_last_name": user.last_name if user else None,
        }

    async def enrich_attendances(self, attendances: List[Attendance]) -> List[Dict]:
        return [await self.enrich_attendance(a) for a in attendances]

    # ── Ecriture ──────────────────────────────────────────────────────

    async def create(self, attendance: Attendance) -> Attendance:
        self._encrypt_model(attendance)
        self.session.add(attendance)
        await self.session.commit()
        await self.session.refresh(attendance)
        self._decrypt_model(attendance)
        self.session.expunge(attendance)
        return attendance

    async def update(self, attendance: Attendance) -> Attendance:
        self._encrypt_model(attendance)
        self.session.add(attendance)
        await self.session.commit()
        await self.session.refresh(attendance)
        self._decrypt_model(attendance)
        self.session.expunge(attendance)
        return attendance

    async def delete(self, attendance_id: UUID) -> bool:
        attendance = await self.get(attendance_id)
        if attendance:
            await self.session.delete(attendance)
            await self.session.commit()
            return True
        return False
