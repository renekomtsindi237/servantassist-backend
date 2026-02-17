"""
Service metier pour le module Presence.

Regles du reglement interieur :
- Le Censeur adjoint veille a l'assiduite des servants
- Les absences non justifiees repetees entrainent des sanctions
- La justification d'absence doit etre fournie dans les 48h
- Le taux de presence est un critere pour les responsabilites
"""
import math
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status

from src.core.entities.attendance import Attendance, AttendanceStatus, AttendanceType
from src.core.entities.user import UserRole
from src.infrastructure.repositories.attendance_repository import AttendanceRepository
from src.infrastructure.repositories.user_repository import UserRepository
from src.presentation.schemas.attendance import (
    AttendanceBatchCreate,
    AttendanceBatchResponse,
    AttendanceCreate,
    AttendanceResponse,
    AttendanceStatsResponse,
    AttendanceUpdate,
)
from src.presentation.schemas.user import PaginatedResponse


class AttendanceService:
    """Logique metier du suivi de presence."""

    def __init__(
        self,
        attendance_repo: AttendanceRepository,
        user_repo: UserRepository,
    ):
        self.attendance_repo = attendance_repo
        self.user_repo = user_repo

    # ══════════════════════════════════════════════════════════════════
    #  ENREGISTREMENT INDIVIDUEL
    # ══════════════════════════════════════════════════════════════════

    async def record_attendance(
        self, data: AttendanceCreate, recorded_by: UUID
    ) -> AttendanceResponse:
        user = await self.user_repo.get(data.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur introuvable.",
            )

        # Verifier doublon
        existing = await self.attendance_repo.get_by_user_date_type(
            data.user_id, data.attendance_date, data.attendance_type
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Un enregistrement de presence existe deja pour cette date et ce type.",
            )

        attendance = Attendance(
            user_id=data.user_id,
            event_id=data.event_id,
            attendance_type=data.attendance_type,
            attendance_date=data.attendance_date,
            title=data.title,
            status=data.status,
            justification=data.justification,
            justified_at=datetime.now(timezone.utc) if data.justification else None,
            recorded_by=recorded_by,
        )
        created = await self.attendance_repo.create(attendance)
        enriched = await self.attendance_repo.enrich_attendance(created)
        return AttendanceResponse(**enriched)

    # ══════════════════════════════════════════════════════════════════
    #  ENREGISTREMENT PAR LOT (APPEL NOMINAL)
    # ══════════════════════════════════════════════════════════════════

    async def record_batch(
        self, data: AttendanceBatchCreate, recorded_by: UUID
    ) -> AttendanceBatchResponse:
        created_list: List[AttendanceResponse] = []
        errors: List[str] = []

        for entry in data.entries:
            try:
                user = await self.user_repo.get(entry.user_id)
                if not user:
                    errors.append(f"Utilisateur {entry.user_id} introuvable.")
                    continue

                existing = await self.attendance_repo.get_by_user_date_type(
                    entry.user_id, data.attendance_date, data.attendance_type
                )
                if existing:
                    errors.append(
                        f"{user.first_name} {user.last_name} : deja enregistre."
                    )
                    continue

                attendance = Attendance(
                    user_id=entry.user_id,
                    event_id=data.event_id,
                    attendance_type=data.attendance_type,
                    attendance_date=data.attendance_date,
                    title=data.title,
                    status=entry.status,
                    justification=entry.justification,
                    justified_at=(
                        datetime.now(timezone.utc) if entry.justification else None
                    ),
                    recorded_by=recorded_by,
                )
                created = await self.attendance_repo.create(attendance)
                enriched = await self.attendance_repo.enrich_attendance(created)
                created_list.append(AttendanceResponse(**enriched))

            except Exception as exc:
                errors.append(f"Erreur pour {entry.user_id}: {str(exc)}")

        return AttendanceBatchResponse(
            created=created_list,
            errors=errors,
            total_created=len(created_list),
            total_errors=len(errors),
        )

    # ══════════════════════════════════════════════════════════════════
    #  MODIFIER / JUSTIFIER UNE ABSENCE
    # ══════════════════════════════════════════════════════════════════

    async def update_attendance(
        self, attendance_id: UUID, data: AttendanceUpdate
    ) -> AttendanceResponse:
        attendance = await self.attendance_repo.get(attendance_id)
        if not attendance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enregistrement de presence introuvable.",
            )

        if data.status is not None:
            attendance.status = data.status
        if data.justification is not None:
            attendance.justification = data.justification
            attendance.justified_at = datetime.now(timezone.utc)
            if attendance.status == AttendanceStatus.ABSENT:
                attendance.status = AttendanceStatus.ABSENT_JUSTIFIE
        attendance.updated_at = datetime.now(timezone.utc)

        updated = await self.attendance_repo.update(attendance)
        enriched = await self.attendance_repo.enrich_attendance(updated)
        return AttendanceResponse(**enriched)

    # ══════════════════════════════════════════════════════════════════
    #  LECTURE
    # ══════════════════════════════════════════════════════════════════

    async def get_attendance(self, attendance_id: UUID) -> AttendanceResponse:
        attendance = await self.attendance_repo.get(attendance_id)
        if not attendance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enregistrement de presence introuvable.",
            )
        enriched = await self.attendance_repo.enrich_attendance(attendance)
        return AttendanceResponse(**enriched)

    async def list_attendances(
        self,
        *,
        user_id: Optional[UUID] = None,
        attendance_type: Optional[AttendanceType] = None,
        attendance_status: Optional[AttendanceStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[AttendanceResponse]:
        attendances, total = await self.attendance_repo.list_paginated(
            user_id=user_id,
            attendance_type=attendance_type,
            status=attendance_status,
            start_date=start_date,
            end_date=end_date,
            event_id=event_id,
            page=page,
            page_size=page_size,
        )
        total_pages = math.ceil(total / page_size) if total > 0 else 1
        enriched = await self.attendance_repo.enrich_attendances(attendances)
        items = [AttendanceResponse(**e) for e in enriched]
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    # ══════════════════════════════════════════════════════════════════
    #  STATISTIQUES
    # ══════════════════════════════════════════════════════════════════

    async def get_user_stats(
        self,
        user_id: UUID,
        *,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> AttendanceStatsResponse:
        user = await self.user_repo.get(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur introuvable.",
            )

        counts = await self.attendance_repo.get_user_stats(
            user_id, start_date=start_date, end_date=end_date
        )
        total = sum(counts.values())
        presents = counts.get(AttendanceStatus.PRESENT.value, 0)
        taux = (presents / total * 100) if total > 0 else 0

        return AttendanceStatsResponse(
            user_id=user_id,
            user_first_name=user.first_name,
            user_last_name=user.last_name,
            total_entries=total,
            presents=presents,
            absents=counts.get(AttendanceStatus.ABSENT.value, 0),
            absents_justifies=counts.get(AttendanceStatus.ABSENT_JUSTIFIE.value, 0),
            retards=counts.get(AttendanceStatus.EN_RETARD.value, 0),
            excuses=counts.get(AttendanceStatus.EXCUSE.value, 0),
            taux_presence=round(taux, 1),
        )
