"""
Service métier pour la gestion des appels (CENSEUR).

Règles métier :
- Seul le CENSEUR/CENSEUR_ADJOINT peut créer/modifier les sessions
- Les appels se font chaque samedi après la messe de 06h15
- Tous les servants doivent être appelés
- Traçabilité complète de tous les enregistrements
"""

import logging
import math
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID, uuid4

from fastapi import HTTPException, status

from src.core.entities.attendance_session import (
    AttendanceRecord,
    AttendanceSession,
    AttendanceStatus,
)
from src.core.entities.notification import (
    Notification,
    NotificationChannel,
    NotificationPriority,
    NotificationType,
)
from src.core.entities.user import User, UserRole
from src.core.interfaces.repositories import IAttendanceSessionRepository, IUserRepository
from src.core.utils import utc_now
from src.infrastructure.repositories.notification_repository import (
    NotificationRepository,
)
from src.infrastructure.services.email_service import EmailService
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

logger = logging.getLogger(__name__)


class AttendanceSessionService:
    """Logique métier des sessions d'appel."""

    def __init__(
        self,
        attendance_repo: IAttendanceSessionRepository,
        user_repo: IUserRepository,
        notification_repo: Optional[NotificationRepository] = None,
        email_service: Optional[EmailService] = None,
    ):
        self.attendance_repo = attendance_repo
        self.user_repo = user_repo
        self.notification_repo = notification_repo
        self.email_service = email_service or EmailService()

    # ══════════════════════════════════════════════════════════════════
    #  SESSIONS
    # ══════════════════════════════════════════════════════════════════

    async def create_session(self, data: AttendanceSessionCreate, conducted_by: UUID) -> AttendanceSessionResponse:
        """Crée une nouvelle session d'appel."""
        session = AttendanceSession(
            session_date=data.session_date,
            session_time=data.session_time,
            location=data.location,
            session_type=data.session_type,
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

    # ══════════════════════════════════════════════════════════════════
    #  SEUILS D'ABSENCE — NOTIFICATIONS AUTOMATIQUES
    # ══════════════════════════════════════════════════════════════════

    async def _handle_absence_thresholds(
        self,
        servant: User,
        session: AttendanceSession,
    ) -> None:
        """Vérifie les seuils 3/5 absences et déclenche les alertes."""
        if self.notification_repo is None:
            return

        stats = await self.attendance_repo.calculate_servant_stats(servant.id)
        total_absences = stats.absent_count

        session_date_str = session.session_date.strftime("%d/%m/%Y") if session.session_date else "—"

        # ── 3 absences : avertissement au servant ─────────────────────
        if total_absences == 3:
            try:
                await self.email_service.send_absence_warning_email(
                    to_email=servant.email,
                    servant_first_name=servant.first_name,
                    servant_last_name=servant.last_name,
                    absent_count=3,
                    session_date=session_date_str,
                )
            except Exception as exc:
                logger.warning("Absence warning email failed: %s", exc)

            notif = Notification(
                id=uuid4(),
                recipient_id=servant.id,
                notification_type=NotificationType.AVERTISSEMENT_ABSENCE,
                channel=NotificationChannel.IN_APP,
                priority=NotificationPriority.HIGH,
                title="⚠️ Avertissement — 3 absences enregistrées",
                body=(
                    "Vous avez cumulé 3 absences non justifiées. "
                    "Un email d'avertissement vous a été envoyé. "
                    "Attention : 5 absences entraîneront la convocation de vos parents."
                ),
            )
            self.notification_repo.session.add(notif)
            await self.notification_repo.session.commit()
            logger.info("Avertissement 3 absences créé pour servant=%s", servant.id)

        # ── 5 absences : convocation des parents ──────────────────────
        elif total_absences == 5:
            # Notification in-app au servant
            notif_servant = Notification(
                id=uuid4(),
                recipient_id=servant.id,
                notification_type=NotificationType.CONVOCATION_PARENT,
                channel=NotificationChannel.IN_APP,
                priority=NotificationPriority.URGENT,
                title="🔴 Convocation des parents — 5 absences",
                body=(
                    "Vous avez atteint 5 absences. Vos parents ont été convoqués "
                    "pour un entretien avec l'Aumônier et le Censeur."
                ),
            )
            self.notification_repo.session.add(notif_servant)

            # Email + notification in-app au parent si lié
            if servant.parent_id:
                parent = await self.user_repo.get(servant.parent_id)
                if parent:
                    try:
                        await self.email_service.send_parent_convocation_email(
                            to_email=parent.email,
                            parent_first_name=parent.first_name,
                            servant_first_name=servant.first_name,
                            servant_last_name=servant.last_name,
                            absent_count=5,
                        )
                    except Exception as exc:
                        logger.warning("Parent convocation email failed: %s", exc)

                    notif_parent = Notification(
                        id=uuid4(),
                        recipient_id=parent.id,
                        notification_type=NotificationType.CONVOCATION_PARENT,
                        channel=NotificationChannel.IN_APP,
                        priority=NotificationPriority.URGENT,
                        title=f"Convocation — {servant.first_name} {servant.last_name}",
                        body=(
                            f"Votre enfant {servant.first_name} {servant.last_name} "
                            f"a cumulé 5 absences. Vous êtes convoqué(e) pour un entretien "
                            f"avec l'Aumônier et le Censeur. Un email vous a été envoyé."
                        ),
                    )
                    self.notification_repo.session.add(notif_parent)
            else:
                logger.info(
                    "Servant %s a 5 absences mais aucun parent lié — pas d'email de convocation.",
                    servant.id,
                )

            await self.notification_repo.session.commit()
            logger.info("Convocation 5 absences créée pour servant=%s", servant.id)

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

        # Vérifier qu'il n'existe pas déjà un enregistrement pour ce servant
        # dans cette session
        existing = await self.attendance_repo.get_record_by_session_and_servant(session_id, data.servant_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La présence de {servant.first_name} {servant.last_name} est déjà enregistrée dans cette session.",  # noqa: E501
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

        if data.status == AttendanceStatus.ABSENT:
            await self._handle_absence_thresholds(servant, session)

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

        new_status = data.status
        if new_status is not None:
            record.status = new_status
        if data.arrival_time is not None:
            record.arrival_time = data.arrival_time
        if data.notes is not None:
            record.notes = data.notes

        updated = await self.attendance_repo.update_record(record_id, record)

        if new_status == AttendanceStatus.ABSENT:
            servant = await self.user_repo.get(record.servant_id)
            if servant:
                session = await self.attendance_repo.get_session(record.session_id)
                if session:
                    await self._handle_absence_thresholds(servant, session)

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
            generated_at=utc_now(),
        )

    # ══════════════════════════════════════════════════════════════════
    #  LISTE DES SERVANTS
    # ══════════════════════════════════════════════════════════════════

    async def get_all_servants_stats(self) -> list[dict]:
        """Stats agrégées pour tous les servants actifs."""
        servants = await self.attendance_repo.get_all_servants()
        result = []
        for servant in servants:
            stats = await self.attendance_repo.calculate_servant_stats(servant.id)
            result.append(
                {
                    "servant_id": str(servant.id),
                    "servant_name": f"{servant.first_name} {servant.last_name}",
                    "absent_count": stats.absent_count,
                    "present_count": stats.present_count,
                    "late_count": stats.late_count,
                    "excused_count": stats.excused_count,
                    "total_sessions": stats.total_sessions,
                    "attendance_rate": stats.attendance_rate,
                    "consecutive_absences": stats.consecutive_absences,
                }
            )
        return result

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

    # ══════════════════════════════════════════════════════════════════
    #  APPEL AUTOMATIQUE
    # ══════════════════════════════════════════════════════════════════

    async def init_roll_call(self, session_id: UUID, recorded_by: UUID) -> AttendanceSessionResponse:
        """Initialise l'appel en créant un enregistrement ABSENT pour chaque servant actif."""
        session = await self.attendance_repo.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session introuvable.")

        servants = await self.attendance_repo.get_all_servants()
        for servant in servants:
            if not servant.is_active:
                continue
            existing = await self.attendance_repo.get_record_by_session_and_servant(session_id, servant.id)
            if not existing:
                record = AttendanceRecord(
                    session_id=session_id,
                    servant_id=servant.id,
                    status=AttendanceStatus.ABSENT,
                    recorded_by=recorded_by,
                )
                self.attendance_repo.session.add(record)

        await self.attendance_repo.session.commit()
        enriched = await self.attendance_repo.enrich_session(session)
        return AttendanceSessionResponse(**enriched)
