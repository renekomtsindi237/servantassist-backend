"""
Service de Dashboard — agrégation de statistiques cross-module.

Fournit des métriques globales pour l'écran de tableau de bord admin :
- Vue d'ensemble (utilisateurs, événements, taux de présence)
- Tendance de présence sur une période
- Statut des cotisations de la période courante
- 5 prochains événements
- Top 10 servants par taux de présence
"""
from datetime import datetime, timezone
from src.core.utils import utc_now
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, func, select

from src.core.entities.attendance import Attendance, AttendanceStatus
from src.core.entities.assignment import Assignment, AssignmentStatus
from src.core.entities.cotisation import CotisationPeriod, CotisationStatus as CotisationPaymentStatus, MemberCotisation
from src.core.entities.event import Event
from src.core.entities.user import User, UserRole
from src.presentation.schemas.dashboard import (
    AttendancePoint,
    AttendanceTrend,
    CotisationStatus as CotisationStatusSchema,
    DashboardSummary,
    TopServant,
    UpcomingEvent,
)


class DashboardService:
    """Service d'agrégation des statistiques pour le dashboard."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Vue d'ensemble ────────────────────────────────────────────────────

    async def get_summary(self) -> DashboardSummary:
        """Retourne les métriques globales de l'application."""
        # Comptages utilisateurs
        stmt_users = select(User).where(User.is_active == True)
        result = await self.session.exec(stmt_users)
        all_users = result.all()
        total_servants = sum(1 for u in all_users if u.role == UserRole.SERVANT)
        total_parents = sum(1 for u in all_users if u.role == UserRole.PARENT)
        total_active = len(all_users)

        # Événements
        stmt_events = select(func.count(Event.id))
        total_events = (await self.session.exec(stmt_events)).one() or 0

        # Assignments
        stmt_assign = select(func.count(Assignment.id))
        total_assign = (await self.session.exec(stmt_assign)).one() or 0

        # Taux de présence global (sur toutes les Attendance)
        stmt_att = select(Attendance)
        result_att = await self.session.exec(stmt_att)
        all_att = result_att.all()
        total_att = len(all_att)
        present_att = sum(
            1 for a in all_att
            if getattr(a, "status", None) in (
                AttendanceStatus.PRESENT,
                AttendanceStatus.EN_RETARD,
            )
        )
        att_rate = (present_att / total_att * 100) if total_att else 0.0

        # Taux de cotisations (période la plus récente)
        cot_status = await self.get_cotisation_status()
        cot_rate = cot_status.rate_percent if cot_status else 0.0

        return DashboardSummary(
            total_servants=total_servants,
            total_parents=total_parents,
            total_active_users=total_active,
            total_events=total_events,
            total_assignments=total_assign,
            attendance_rate_percent=round(att_rate, 1),
            cotisation_rate_percent=round(cot_rate, 1),
            generated_at=utc_now(),
        )

    # ── Tendance de présence ──────────────────────────────────────────────

    async def get_attendance_trend(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        group_by: str = "month",  # "month" | "week"
    ) -> AttendanceTrend:
        """
        Retourne la tendance de présence groupée par mois ou par semaine.
        """
        stmt = select(Attendance)
        if start_date:
            stmt = stmt.where(col(Attendance.attendance_date) >= start_date)
        if end_date:
            stmt = stmt.where(col(Attendance.attendance_date) <= end_date)
        result = await self.session.exec(stmt)
        records = result.all()

        # Grouper par période
        buckets: dict[str, dict] = {}
        for rec in records:
            att_date = getattr(rec, "attendance_date", None)
            if not att_date:
                continue
            if group_by == "week":
                key = f"Semaine {att_date.isocalendar()[1]:02d} {att_date.year}"
            else:
                key = att_date.strftime("%Y-%m")

            if key not in buckets:
                buckets[key] = {"total": 0, "present": 0, "absent": 0}
            buckets[key]["total"] += 1
            status = getattr(rec, "status", None)
            if status in (AttendanceStatus.PRESENT, AttendanceStatus.RETARD):
                buckets[key]["present"] += 1
            else:
                buckets[key]["absent"] += 1

        points = []
        for period_key in sorted(buckets.keys()):
            b = buckets[period_key]
            rate = (b["present"] / b["total"] * 100) if b["total"] else 0.0
            points.append(
                AttendancePoint(
                    period=period_key,
                    total=b["total"],
                    present=b["present"],
                    absent=b["absent"],
                    rate_percent=round(rate, 1),
                )
            )

        avg_rate = (
            sum(p.rate_percent for p in points) / len(points) if points else 0.0
        )
        label = "Tendance mensuelle" if group_by == "month" else "Tendance hebdomadaire"
        return AttendanceTrend(
            period_label=label,
            points=points,
            average_rate_percent=round(avg_rate, 1),
        )

    # ── Statut des cotisations ────────────────────────────────────────────

    async def get_cotisation_status(self) -> Optional[CotisationStatusSchema]:
        """
        Retourne le statut des cotisations de la période la plus récente.
        """
        # Récupérer la période la plus récente
        stmt = select(CotisationPeriod).order_by(col(CotisationPeriod.start_date).desc())
        result = await self.session.exec(stmt)
        period = result.first()
        if not period:
            return CotisationStatusSchema(
                period_id=None,
                period_name="Aucune période",
                total_members=0,
                paid_count=0,
                partial_count=0,
                unpaid_count=0,
                total_expected=0.0,
                total_collected=0.0,
                rate_percent=0.0,
            )

        # Cotisations de cette période
        stmt_cot = select(MemberCotisation).where(
            MemberCotisation.period_id == period.id
        )
        result_cot = await self.session.exec(stmt_cot)
        cotisations = result_cot.all()

        paid = sum(1 for c in cotisations if c.status == CotisationPaymentStatus.PAYE)
        partial = sum(1 for c in cotisations if c.status == CotisationPaymentStatus.PAYE_PARTIELLEMENT)
        unpaid = len(cotisations) - paid - partial

        total_expected = float(period.amount_expected or 0) * len(cotisations)
        total_collected = sum(
            float(getattr(c, "amount_paid", 0) or 0) for c in cotisations
        )
        rate = (paid / len(cotisations) * 100) if cotisations else 0.0

        return CotisationStatusSchema(
            period_id=period.id,
            period_name=period.title,
            total_members=len(cotisations),
            paid_count=paid,
            partial_count=partial,
            unpaid_count=unpaid,
            total_expected=round(total_expected, 2),
            total_collected=round(total_collected, 2),
            rate_percent=round(rate, 1),
        )

    # ── Événements à venir ────────────────────────────────────────────────

    async def get_upcoming_events(self, limit: int = 5) -> List[UpcomingEvent]:
        """Retourne les N prochains événements avec leur nb d'assignments."""
        now = datetime.utcnow()
        stmt = (
            select(Event)
            .where(col(Event.start_time) >= now)
            .order_by(col(Event.start_time))
            .limit(limit)
        )
        result = await self.session.exec(stmt)
        events = result.all()

        upcoming = []
        for ev in events:
            # Compter les assignments
            stmt_a = select(Assignment).where(Assignment.event_id == ev.id)
            result_a = await self.session.exec(stmt_a)
            assignments = result_a.all()
            confirmed = sum(
                1 for a in assignments
                if getattr(a, "status", None) in (
                    AssignmentStatus.ACCEPTED,
                    AssignmentStatus.PRESENT,
                )
            )
            upcoming.append(
                UpcomingEvent(
                    id=ev.id,
                    title=ev.title,
                    event_date=ev.start_time,
                    location=getattr(ev, "location", ""),
                    total_assignments=len(assignments),
                    confirmed_assignments=confirmed,
                )
            )
        return upcoming

    # ── Top servants ──────────────────────────────────────────────────────

    async def get_top_servants(self, limit: int = 10) -> List[TopServant]:
        """
        Retourne les servants classés par taux de présence décroissant.
        """
        # Récupérer tous les servants actifs
        stmt_s = select(User).where(
            User.role == UserRole.SERVANT, User.is_active == True
        )
        result_s = await self.session.exec(stmt_s)
        servants = result_s.all()

        # Pour chaque servant, calculer les stats de présence
        servant_stats = []
        for s in servants:
            stmt_att = select(Attendance).where(Attendance.user_id == s.id)
            result_att = await self.session.exec(stmt_att)
            att_records = result_att.all()
            total = len(att_records)
            present = sum(
                1 for a in att_records
                if getattr(a, "status", None) in (
                    AttendanceStatus.PRESENT,
                    AttendanceStatus.EN_RETARD,
                )
            )
            rate = (present / total * 100) if total else 0.0
            servant_stats.append(
                {
                    "user": s,
                    "total": total,
                    "present": present,
                    "rate": rate,
                }
            )

        # Trier par taux décroissant
        servant_stats.sort(key=lambda x: x["rate"], reverse=True)

        top = []
        for rank, stat in enumerate(servant_stats[:limit], start=1):
            u = stat["user"]
            top.append(
                TopServant(
                    rank=rank,
                    user_id=u.id,
                    full_name=f"{u.first_name} {u.last_name}",
                    total_sessions=stat["total"],
                    present_count=stat["present"],
                    attendance_rate_percent=round(stat["rate"], 1),
                )
            )
        return top
