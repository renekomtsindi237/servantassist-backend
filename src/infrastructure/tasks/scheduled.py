"""
Tâches Celery planifiées (Beat).

Toutes les tâches sont async-safe : elles ouvrent leur propre session
de base de données et se ferment proprement à la fin.

Pour lancer en développement :
    celery -A src.infrastructure.tasks.celery_app worker --loglevel=info
    celery -A src.infrastructure.tasks.celery_app beat --loglevel=info
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from src.infrastructure.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Exécute une coroutine dans un event loop depuis une tâche Celery synchrone."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── Tâche 1 : Rappels 24h avant un événement ─────────────────────────────


@celery_app.task(
    name="src.infrastructure.tasks.scheduled.send_event_reminders",
    bind=True,
    max_retries=3,
)
def send_event_reminders(self):
    """
    Chaque matin à 8h : envoie un rappel aux servants affectés
    à un événement prévu dans les prochaines 24h.
    """
    try:
        _run_async(_send_event_reminders_async())
    except Exception as exc:
        logger.error("send_event_reminders failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc, countdown=300)  # retry dans 5 min


async def _send_event_reminders_async():
    """Logique async : récupère les événements demain et envoie les rappels."""
    from sqlmodel import col, select

    from src.core.entities.assignment import Assignment, AssignmentStatus
    from src.core.entities.event import Event, EventStatus
    from src.core.entities.notification import (
        NotificationChannel,
        NotificationPriority,
        NotificationType,
    )
    from src.core.entities.user import User
    from src.infrastructure.database.session import sessionmanager
    from src.infrastructure.services.email_service import EmailService

    now = datetime.now(timezone.utc)
    tomorrow_start = now + timedelta(hours=20)
    tomorrow_end = now + timedelta(hours=28)

    async with sessionmanager.session() as session:
        # Événements publiés demain
        stmt = select(Event).where(
            Event.status == EventStatus.PUBLIE,
            col(Event.start_time) >= tomorrow_start,
            col(Event.start_time) <= tomorrow_end,
        )
        result = await session.exec(stmt)
        events = result.all()

        if not events:
            logger.info("send_event_reminders: no events tomorrow")
            return

        email_svc = EmailService()
        sent = 0

        for event in events:
            # Récupérer les assignments ACCEPTED
            stmt_a = select(Assignment).where(
                Assignment.event_id == event.id,
                Assignment.status == AssignmentStatus.ACCEPTED,
            )
            result_a = await session.exec(stmt_a)
            assignments = result_a.all()

            for assignment in assignments:
                # Récupérer le servant
                user = await session.get(User, assignment.user_id)
                if not user or not user.is_active or not user.email:
                    continue

                role = (
                    assignment.liturgical_role.value
                    if assignment.liturgical_role
                    else "servant"
                )
                ok = await email_svc.send_event_reminder(
                    to_email=user.email,
                    user_first_name=user.first_name,
                    event_title=event.title,
                    event_date=event.start_time,
                    event_location=event.location,
                    liturgical_role=role,
                )
                if ok:
                    sent += 1

        logger.info(
            "send_event_reminders: sent %d reminders for %d events",
            sent,
            len(events),
        )


# ── Tâche 2 : Rapport hebdomadaire ───────────────────────────────────────


@celery_app.task(
    name="src.infrastructure.tasks.scheduled.send_weekly_report",
    bind=True,
    max_retries=3,
)
def send_weekly_report(self):
    """
    Chaque lundi à 7h : envoie un rapport hebdomadaire de statistiques
    à tous les admins actifs.
    """
    try:
        _run_async(_send_weekly_report_async())
    except Exception as exc:
        logger.error("send_weekly_report failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc, countdown=600)


async def _send_weekly_report_async():
    """Logique async : calcule les stats de la semaine et envoie l'email."""
    from sqlmodel import col, select

    from src.core.entities.attendance import Attendance, AttendanceStatus
    from src.core.entities.event import Event, EventStatus
    from src.core.entities.user import User, UserRole
    from src.infrastructure.database.session import sessionmanager
    from src.infrastructure.services.email_service import EmailService

    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=7)

    async with sessionmanager.session() as session:
        # Récupérer les admins
        stmt_admins = select(User).where(
            User.role == UserRole.ADMIN, User.is_active == True
        )
        result_a = await session.exec(stmt_admins)
        admins = result_a.all()

        if not admins:
            logger.info("send_weekly_report: no admins found")
            return

        # Stats semaine
        stmt_events = select(Event).where(
            Event.status == EventStatus.PUBLIE,
            col(Event.start_time) >= week_start,
            col(Event.start_time) <= now,
        )
        result_e = await session.exec(stmt_events)
        events_week = result_e.all()

        stmt_att = select(Attendance).where(col(Attendance.created_at) >= week_start)
        result_att = await session.exec(stmt_att)
        attendance_week = result_att.all()

        present = sum(
            1
            for a in attendance_week
            if getattr(a, "status", None)
            in (AttendanceStatus.PRESENT, AttendanceStatus.RETARD)
        )
        total_att = len(attendance_week)
        att_rate = f"{present / total_att * 100:.1f}%" if total_att else "N/A"

        body = (
            f"Semaine du {week_start.strftime('%d/%m/%Y')} au {now.strftime('%d/%m/%Y')}\n\n"
            f"📅 Événements de la semaine : {len(events_week)}\n"
            f"✅ Appels enregistrés : {total_att}\n"
            f"📊 Taux de présence : {att_rate}\n\n"
            "Connectez-vous à ServantAssist pour voir le détail."
        )

        email_svc = EmailService()
        for admin in admins:
            if admin.email:
                await email_svc.send_general_notification(
                    to_email=admin.email,
                    user_first_name=admin.first_name,
                    title="Rapport hebdomadaire ServantAssist",
                    body=body,
                )

        logger.info(
            "send_weekly_report: report sent to %d admins | events=%d att_rate=%s",
            len(admins),
            len(events_week),
            att_rate,
        )


# ── Tâche 3 : Nettoyage des vieilles notifications ────────────────────────


@celery_app.task(
    name="src.infrastructure.tasks.scheduled.cleanup_notifications",
    bind=True,
    max_retries=2,
)
def cleanup_notifications(self):
    """
    Chaque nuit à 2h : supprime les notifications IN_APP lues depuis +30 jours.
    """
    try:
        deleted = _run_async(_cleanup_notifications_async())
        logger.info("cleanup_notifications: deleted %d old notifications", deleted)
    except Exception as exc:
        logger.error("cleanup_notifications failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc, countdown=1800)


async def _cleanup_notifications_async() -> int:
    """Logique async : supprime les notifications lues de plus de 30 jours."""
    from sqlmodel import col, delete

    from src.core.entities.notification import Notification, NotificationStatus
    from src.infrastructure.database.session import sessionmanager

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    async with sessionmanager.session() as session:
        stmt = delete(Notification).where(
            Notification.status == NotificationStatus.READ,
            col(Notification.updated_at) <= cutoff,
        )
        result = await session.exec(stmt)
        await session.commit()
        return result.rowcount or 0
