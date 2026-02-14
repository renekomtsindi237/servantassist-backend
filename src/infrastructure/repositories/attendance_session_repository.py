"""
Repository pour la gestion des sessions d'appel (CENSEUR).
"""
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.entities.attendance_session import (
    AttendanceRecord,
    AttendanceSession,
    AttendanceStatus,
    ServantAttendanceStats,
)
from src.core.entities.user import User, UserRole


class AttendanceSessionRepository:
    """Repository pour les sessions d'appel."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ══════════════════════════════════════════════════════════════════
    #  SESSIONS - CRÉATION
    # ══════════════════════════════════════════════════════════════════

    async def create_session(self, session_data: AttendanceSession) -> AttendanceSession:
        """Crée une nouvelle session d'appel."""
        self.session.add(session_data)
        await self.session.commit()
        await self.session.refresh(session_data)
        return session_data

    # ══════════════════════════════════════════════════════════════════
    #  SESSIONS - LECTURE
    # ══════════════════════════════════════════════════════════════════

    async def get_session(self, session_id: UUID) -> Optional[AttendanceSession]:
        """Récupère une session par son ID."""
        result = await self.session.execute(
            select(AttendanceSession).where(AttendanceSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def list_sessions(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[list[AttendanceSession], int]:
        """Liste les sessions avec filtres et pagination."""
        query = select(AttendanceSession)

        # Filtres
        conditions = []
        if start_date:
            conditions.append(AttendanceSession.session_date >= start_date)
        if end_date:
            conditions.append(AttendanceSession.session_date <= end_date)

        if conditions:
            query = query.where(and_(*conditions))

        # Compte total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()

        # Pagination
        query = query.order_by(AttendanceSession.session_date.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        sessions = result.scalars().all()

        return list(sessions), total

    # ══════════════════════════════════════════════════════════════════
    #  RECORDS - CRÉATION
    # ══════════════════════════════════════════════════════════════════

    async def create_record(self, record: AttendanceRecord) -> AttendanceRecord:
        """Crée un enregistrement de présence."""
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def create_records_batch(
        self, records: List[AttendanceRecord]
    ) -> List[AttendanceRecord]:
        """Crée plusieurs enregistrements en batch."""
        for record in records:
            self.session.add(record)
        await self.session.commit()
        for record in records:
            await self.session.refresh(record)
        return records

    # ══════════════════════════════════════════════════════════════════
    #  RECORDS - LECTURE
    # ══════════════════════════════════════════════════════════════════

    async def get_record(self, record_id: UUID) -> Optional[AttendanceRecord]:
        """Récupère un enregistrement par son ID."""
        result = await self.session.execute(
            select(AttendanceRecord).where(AttendanceRecord.id == record_id)
        )
        return result.scalar_one_or_none()

    async def get_session_records(
        self, session_id: UUID
    ) -> List[AttendanceRecord]:
        """Récupère tous les enregistrements d'une session."""
        result = await self.session.execute(
            select(AttendanceRecord)
            .where(AttendanceRecord.session_id == session_id)
            .order_by(AttendanceRecord.created_at)
        )
        return list(result.scalars().all())

    async def get_servant_records(
        self,
        servant_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[AttendanceRecord]:
        """Récupère tous les enregistrements d'un servant."""
        # Joindre avec les sessions pour filtrer par date
        query = (
            select(AttendanceRecord)
            .join(AttendanceSession)
            .where(AttendanceRecord.servant_id == servant_id)
        )

        if start_date:
            query = query.where(AttendanceSession.session_date >= start_date)
        if end_date:
            query = query.where(AttendanceSession.session_date <= end_date)

        query = query.order_by(AttendanceSession.session_date.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # ══════════════════════════════════════════════════════════════════
    #  RECORDS - MODIFICATION
    # ══════════════════════════════════════════════════════════════════

    async def update_record(
        self, record_id: UUID, record: AttendanceRecord
    ) -> Optional[AttendanceRecord]:
        """Met à jour un enregistrement."""
        existing = await self.get_record(record_id)
        if not existing:
            return None

        for key, value in record.model_dump(exclude_unset=True).items():
            setattr(existing, key, value)

        existing.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    # ══════════════════════════════════════════════════════════════════
    #  STATISTIQUES
    # ══════════════════════════════════════════════════════════════════

    async def calculate_servant_stats(
        self,
        servant_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> ServantAttendanceStats:
        """Calcule les statistiques de présence d'un servant."""
        # Récupérer le servant
        servant_result = await self.session.execute(
            select(User).where(User.id == servant_id)
        )
        servant = servant_result.scalar_one_or_none()
        servant_name = (
            f"{servant.first_name} {servant.last_name}" if servant else "Inconnu"
        )

        # Récupérer les enregistrements
        records = await self.get_servant_records(servant_id, start_date, end_date)

        # Compter les sessions totales dans la période
        query = select(func.count(AttendanceSession.id))
        if start_date:
            query = query.where(AttendanceSession.session_date >= start_date)
        if end_date:
            query = query.where(AttendanceSession.session_date <= end_date)

        total_result = await self.session.execute(query)
        total_sessions = total_result.scalar()

        # Compter par statut
        present_count = sum(1 for r in records if r.status == AttendanceStatus.PRESENT)
        absent_count = sum(1 for r in records if r.status == AttendanceStatus.ABSENT)
        late_count = sum(1 for r in records if r.status == AttendanceStatus.LATE)
        excused_count = sum(1 for r in records if r.status == AttendanceStatus.EXCUSED)

        # Calculer le taux de présence
        attendance_rate = (
            (present_count + late_count) / total_sessions * 100
            if total_sessions > 0
            else 0
        )

        # Calculer les absences consécutives
        consecutive_absences = 0
        for record in reversed(records):  # Du plus récent au plus ancien
            if record.status == AttendanceStatus.ABSENT:
                consecutive_absences += 1
            else:
                break

        return ServantAttendanceStats(
            servant_id=servant_id,
            servant_name=servant_name,
            total_sessions=total_sessions,
            present_count=present_count,
            absent_count=absent_count,
            late_count=late_count,
            excused_count=excused_count,
            attendance_rate=attendance_rate,
            consecutive_absences=consecutive_absences,
        )

    async def get_all_servants(self) -> List[User]:
        """Récupère tous les servants."""
        result = await self.session.execute(
            select(User).where(User.role == UserRole.SERVANT).order_by(User.last_name)
        )
        return list(result.scalars().all())

    # ══════════════════════════════════════════════════════════════════
    #  ENRICHISSEMENT
    # ══════════════════════════════════════════════════════════════════

    async def enrich_record(self, record: AttendanceRecord) -> dict:
        """Enrichit un enregistrement avec les noms."""
        # Récupérer le servant
        servant_result = await self.session.execute(
            select(User).where(User.id == record.servant_id)
        )
        servant = servant_result.scalar_one_or_none()
        servant_name = (
            f"{servant.first_name} {servant.last_name}" if servant else "Inconnu"
        )

        # Récupérer l'enregistreur
        recorder_result = await self.session.execute(
            select(User).where(User.id == record.recorded_by)
        )
        recorder = recorder_result.scalar_one_or_none()
        recorded_by_name = (
            f"{recorder.first_name} {recorder.last_name}" if recorder else "Inconnu"
        )

        return {
            **record.model_dump(),
            "servant_name": servant_name,
            "recorded_by_name": recorded_by_name,
        }

    async def enrich_session(self, session: AttendanceSession) -> dict:
        """Enrichit une session avec les noms et statistiques."""
        # Récupérer le conducteur
        conductor_result = await self.session.execute(
            select(User).where(User.id == session.conducted_by)
        )
        conductor = conductor_result.scalar_one_or_none()
        conducted_by_name = (
            f"{conductor.first_name} {conductor.last_name}" if conductor else "Inconnu"
        )

        # Récupérer les enregistrements
        records = await self.get_session_records(session.id)

        # Enrichir les enregistrements
        enriched_records = []
        for record in records:
            enriched = await self.enrich_record(record)
            enriched_records.append(enriched)

        # Calculer les statistiques
        total_servants = len(records)
        present_count = sum(1 for r in records if r.status == AttendanceStatus.PRESENT)
        absent_count = sum(1 for r in records if r.status == AttendanceStatus.ABSENT)
        late_count = sum(1 for r in records if r.status == AttendanceStatus.LATE)
        excused_count = sum(1 for r in records if r.status == AttendanceStatus.EXCUSED)

        return {
            **session.model_dump(),
            "conducted_by_name": conducted_by_name,
            "records": enriched_records,
            "total_servants": total_servants,
            "present_count": present_count,
            "absent_count": absent_count,
            "late_count": late_count,
            "excused_count": excused_count,
        }
