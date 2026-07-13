"""
Tâches Celery de rappel planifiées.

Schedule (configurer dans celery_app.py beat_schedule) :
- send_cotisation_reminders : chaque lundi à 9h00
- send_event_reminders_24h  : chaque matin à 7h30 (complément de scheduled.py)

Ces tâches sont conçues pour être idempotentes et ne jamais lever d'exception
non rattrapée afin de ne pas bloquer la queue Beat.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from src.infrastructure.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── Rappels cotisations ────────────────────────────────────────────────────────


@celery_app.task(
    name="src.infrastructure.tasks.reminder_tasks.send_cotisation_reminders",
    bind=True,
    max_retries=2,
)
def send_cotisation_reminders(self) -> dict:
    """
    Chaque lundi à 9h : envoie un rappel aux servants avec des cotisations en retard.

    Cible : MemberCotisation avec status EN_RETARD ou PENDING dont la période
    est passée (mois < mois en cours).

    Returns:
        dict avec nb_reminders_sent et nb_errors.
    """
    try:
        return _run_async(_send_cotisation_reminders_async())
    except Exception as exc:
        logger.error("send_cotisation_reminders: failed error=%s", exc, exc_info=True)
        raise self.retry(exc=exc, countdown=600)


async def _send_cotisation_reminders_async() -> dict:
    from sqlmodel import col, select

    from src.core.entities.contribution import MemberCotisation
    from src.core.entities.user import User
    from src.infrastructure.database.session import sessionmanager
    from src.infrastructure.services.email_service import EmailService

    now = datetime.now(timezone.utc)
    current_month = now.month
    current_year = now.year

    sent = 0
    errors = 0

    async with sessionmanager.session() as session:
        stmt = select(MemberCotisation).where(
            col(MemberCotisation.year) <= current_year,
        )
        result = await session.exec(stmt)
        cotisations = result.all()

        overdue = [
            c for c in cotisations
            if str(getattr(c.status, "value", c.status)) in ("PENDING", "EN_RETARD")
            and (
                c.year < current_year
                or (c.year == current_year and (int(c.month) if c.month else 0) < current_month)
            )
        ]

        if not overdue:
            logger.info("send_cotisation_reminders: no overdue cotisations found")
            return {"nb_reminders_sent": 0, "nb_errors": 0}

        email_svc = EmailService()
        for cotisation in overdue:
            user = await session.get(User, cotisation.user_id)
            if not user or not user.is_active or not user.email:
                continue
            try:
                period_str = f"{cotisation.month}/{cotisation.year}" if cotisation.month else str(cotisation.year)
                await email_svc.send_general_notification(
                    to_email=user.email,
                    user_first_name=user.first_name,
                    title="Rappel — Cotisation en retard",
                    body=(
                        f"Votre cotisation pour la période {period_str} est en attente de règlement.\n\n"
                        f"Montant dû : {cotisation.amount:,.0f} XAF\n\n"
                        "Merci de régulariser votre situation au plus tôt.\n"
                        "Connectez-vous à ServantAssist pour effectuer votre paiement."
                    ),
                )
                sent += 1
            except Exception as e:
                logger.error(
                    "send_cotisation_reminders: error sending to user=%s error=%s",
                    cotisation.user_id,
                    e,
                )
                errors += 1

    logger.info(
        "send_cotisation_reminders: sent=%d errors=%d overdue=%d",
        sent,
        errors,
        len(overdue),
    )
    return {"nb_reminders_sent": sent, "nb_errors": errors}


# ── Rappels événements (complément) ───────────────────────────────────────────


@celery_app.task(
    name="src.infrastructure.tasks.reminder_tasks.send_event_day_reminders",
    bind=True,
    max_retries=2,
)
def send_event_day_reminders(self) -> dict:
    """
    Rappels le jour J à 7h30 pour les servants affectés à des événements du jour.

    Complète send_event_reminders de scheduled.py qui couvre J+1.
    """
    try:
        return _run_async(_send_event_day_reminders_async())
    except Exception as exc:
        logger.error("send_event_day_reminders: failed error=%s", exc, exc_info=True)
        raise self.retry(exc=exc, countdown=300)


async def _send_event_day_reminders_async() -> dict:
    from sqlmodel import col, select

    from src.core.entities.assignment import Assignment, AssignmentStatus
    from src.core.entities.event import Event, EventStatus
    from src.core.entities.user import User
    from src.infrastructure.database.session import sessionmanager
    from src.infrastructure.services.email_service import EmailService

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    sent = 0
    errors = 0

    async with sessionmanager.session() as session:
        stmt = select(Event).where(
            Event.status == EventStatus.PUBLIE,
            col(Event.start_time) >= today_start,
            col(Event.start_time) < today_end,
        )
        result = await session.exec(stmt)
        events = result.all()

        if not events:
            logger.info("send_event_day_reminders: no events today")
            return {"nb_reminders_sent": 0, "nb_errors": 0}

        email_svc = EmailService()
        for event in events:
            stmt_a = select(Assignment).where(
                Assignment.event_id == event.id,
                Assignment.status == AssignmentStatus.ACCEPTED,
            )
            result_a = await session.exec(stmt_a)
            for assignment in result_a.all():
                user = await session.get(User, assignment.user_id)
                if not user or not user.is_active or not user.email:
                    continue
                try:
                    role = assignment.liturgical_role.value if assignment.liturgical_role else "servant"
                    start_time = event.start_time.strftime("%H:%M") if event.start_time else ""
                    await email_svc.send_general_notification(
                        to_email=user.email,
                        user_first_name=user.first_name,
                        title=f"Rappel — {event.title} aujourd'hui",
                        body=(
                            f"Vous êtes affecté à l'événement « {event.title} » aujourd'hui.\n"
                            f"Heure : {start_time}\n"
                            f"Lieu : {event.location or 'Non précisé'}\n"
                            f"Rôle : {role}\n\n"
                            "Bonne célébration !"
                        ),
                    )
                    sent += 1
                except Exception as e:
                    logger.error(
                        "send_event_day_reminders: error user=%s event=%s error=%s",
                        assignment.user_id,
                        event.id,
                        e,
                    )
                    errors += 1

    logger.info("send_event_day_reminders: sent=%d errors=%d", sent, errors)
    return {"nb_reminders_sent": sent, "nb_errors": errors}
