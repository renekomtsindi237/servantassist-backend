"""
Service métier pour la gestion des appels (CENSEUR).

Règles métier :
- Seul le CENSEUR/CENSEUR_ADJOINT peut créer/modifier les sessions
- Les appels se font chaque samedi après la messe de 06h15
- Tous les servants doivent être appelés
- Traçabilité complète de tous les enregistrements
"""
import math
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status

from src.core.entities.attendance_session import AttendanceRecord, AttendanceSession, AttendanceStatus
from src.core.entities.user import UserRole
from src.infrastructure.repositories.attendance_session_repository import AttendanceSessionRepository
from src.infrastructure.repositories.user_repository import UserRepository
from src.presentation.schemas.attendance_session import (
    AttendanceRecordCreate,
    AttendanceRecordResponse,
    AttendanceRecordUpdate,
    AttendanceReportRequest,
    AttendanceReportResponse,
    AttendanceSessionCreate,
    AttendanceSessionResponse,
    ServantAttendanceStatsResponse,
    ServantListItem,
)
from src.presentation.schemas.user import PaginatedResponse


class AttendanceSessionService:
    """Logique métier des sessions d'appel."""

    def __init__(
        self,
        attendance_repo: AttendanceSessionRepository,
        user_repo: UserRepository,
    ):
        self.attendance_repo = attendance_repo
        self.user_repo = user_repo

    # ══════════════════════════════════════════════════════════════════
    #  SESSIONS
    # ══════════════════════════════════════════════════════════════════

    async def create_session(self, data: AttendanceSessionCreate, conducted_by: UUID) -> AttendanceSessionResponse:
        """Crée une nouvelle session d'appel."""
        session = AttendanceSession(
            session_date=data.session_date,
            session_time=data.session_time,
            location=data.location,
            conducted_by=conducted_by,
            notes=data.notes,
        )

        created = await self.attendance_repo.create_session(session)
        enriched = await self.attendance_repo.enrich_session(created)
        return AttendanceSessionResponse(**enriched)

    async def get_session(self, session_id: UUID) -> AttendanceSessionResponse:
        """Récupère une session par son ID."""
        session = await self.attendance_repo.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session d'appel introuvable.",
            )

        enriched = await self.attendance_repo.enrich_session(session)
        return AttendanceSessionResponse(**enriched)

    async def list_sessions(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResponse[AttendanceSessionResponse]:
        """Liste les sessions avec filtres."""
        sessions, total = await self.attendance_repo.list_sessions(
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
        )

        total_pages = math.ceil(total / page_size) if total > 0 else 1

        # Enrichir les sessions
        enriched_list = []
        for session in sessions:
            enriched = await self.attendance_repo.enrich_session(session)
            enriched_list.append(AttendanceSessionResponse(**enriched))

        return PaginatedResponse(
            items=enriched_list,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    # ══════════════════════════════════════════════════════════════════
    #  RECORDS
    # ══════════════════════════════════════════════════════════════════

    async def mark_attendance(
        self, session_id: UUID, data: AttendanceRecordCreate, recorded_by: UUID
    ) -> AttendanceRecordResponse:
        """Marque la présence d'un servant."""
        # Vérifier que la session existe
        session = await self.attendance_repo.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session d'appel introuvable.",
            )

        # Vérifier que le servant existe
        servant = await self.user_repo.get(data.servant_id)
        if not servant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Servant introuvable.",
            )

        if servant.role != UserRole.SERVANT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{servant.first_name} {servant.last_name} n'est pas un servant.",
            )

        # Vérifier qu'il n'existe pas déjà un enregistrement pour ce servant dans cette session
        existing = await self.attendance_repo.get_record_by_session_and_servant(session_id, data.servant_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La présence de {servant.first_name} {servant.last_name} est déjà enregistrée dans cette session.",
            )

        record = AttendanceRecord(
            session_id=session_id,
            servant_id=data.servant_id,
            status=data.status,
            arrival_time=data.arrival_time,
            notes=data.notes,
            recorded_by=recorded_by,
        )

        created = await self.attendance_repo.create_record(record)
        enriched = await self.attendance_repo.enrich_record(created)
        return AttendanceRecordResponse(**enriched)

    async def update_attendance(self, record_id: UUID, data: AttendanceRecordUpdate) -> AttendanceRecordResponse:
        """Met à jour un enregistrement de présence."""
        record = await self.attendance_repo.get_record(record_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enregistrement introuvable.",
            )

        if data.status is not None:
            record.status = data.status
        if data.arrival_time is not None:
            record.arrival_time = data.arrival_time
        if data.notes is not None:
            record.notes = data.notes

        updated = await self.attendance_repo.update_record(record_id, record)
        enriched = await self.attendance_repo.enrich_record(updated)
        return AttendanceRecordResponse(**enriched)

    # ══════════════════════════════════════════════════════════════════
    #  STATISTIQUES
    # ══════════════════════════════════════════════════════════════════

    async def get_servant_stats(
        self,
        servant_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> ServantAttendanceStatsResponse:
        """Calcule les statistiques de présence d'un servant."""
        # Vérifier que le servant existe
        servant = await self.user_repo.get(servant_id)
        if not servant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Servant introuvable.",
            )

        stats = await self.attendance_repo.calculate_servant_stats(servant_id, start_date, end_date)
        return ServantAttendanceStatsResponse(**stats.model_dump())

    async def generate_report(self, request: AttendanceReportRequest, generated_by: UUID) -> AttendanceReportResponse:
        """Génère un rapport de présence."""
        # Récupérer toutes les sessions de la période
        sessions, _ = await self.attendance_repo.list_sessions(
            start_date=request.start_date,
            end_date=request.end_date,
            page=1,
            page_size=1000,  # Toutes les sessions
        )

        # Récupérer tous les servants
        servants = await self.attendance_repo.get_all_servants()

        # Filtrer par servants si spécifié
        if request.servant_ids:
            servants = [s for s in servants if s.id in request.servant_ids]

        # Calculer les statistiques pour chaque servant
        servants_stats = []
        total_attendance_rate = 0

        for servant in servants:
            stats = await self.attendance_repo.calculate_servant_stats(servant.id, request.start_date, request.end_date)
            servants_stats.append(ServantAttendanceStatsResponse(**stats.model_dump()))
            total_attendance_rate += stats.attendance_rate

        average_attendance_rate = total_attendance_rate / len(servants) if servants else 0

        # Récupérer le générateur
        generator = await self.user_repo.get(generated_by)
        generated_by_name = f"{generator.first_name} {generator.last_name}" if generator else "Inconnu"

        return AttendanceReportResponse(
            start_date=request.start_date,
            end_date=request.end_date,
            total_sessions=len(sessions),
            total_servants=len(servants),
            average_attendance_rate=average_attendance_rate,
            servants_stats=servants_stats,
            generated_by=generated_by,
            generated_by_name=generated_by_name,
            generated_at=datetime.utcnow(),
        )

    # ══════════════════════════════════════════════════════════════════
    #  LISTE DES SERVANTS
    # ══════════════════════════════════════════════════════════════════

    async def get_servants_list(self) -> List[ServantListItem]:
        """Récupère la liste complète des servants pour l'appel."""
        servants = await self.attendance_repo.get_all_servants()

        return [
            ServantListItem(
                id=s.id,
                first_name=s.first_name,
                last_name=s.last_name,
                full_name=f"{s.first_name} {s.last_name}",
                phone_number=s.phone_number,
                is_active=s.is_active,
            )
            for s in servants
        ]
