"""
Tâches Celery asynchrones pour l'envoi d'emails.

Usage :
    # Envoi asynchrone depuis n'importe quel endpoint FastAPI :
    send_email_async.delay(to="user@example.com", subject="...", html_body="...")
    send_welcome_email_async.delay(to="user@example.com", user_first_name="Jean", role="SERVANT")
"""

import asyncio
import logging

from src.infrastructure.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Exécute une coroutine dans un event loop dédié (tâche Celery synchrone)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── Tâche générique ───────────────────────────────────────────────────────────


@celery_app.task(
    name="src.infrastructure.tasks.email_tasks.send_email_async",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_email_async(self, to: str, subject: str, html_body: str) -> bool:
    """
    Envoie un email HTML en arrière-plan.

    Retry automatique 3 fois avec backoff 60s si l'envoi échoue.
    Retourne True si l'email a été envoyé/loggé avec succès.
    """
    try:
        from src.infrastructure.services.email_service import EmailService

        result = _run_async(EmailService().send_email(to, subject, html_body))
        logger.info("send_email_async: sent to=%s subject=%s result=%s", to, subject, result)
        return result
    except Exception as exc:
        logger.error("send_email_async: failed to=%s error=%s", to, exc)
        raise self.retry(exc=exc)


# ── Emails métier ─────────────────────────────────────────────────────────────


@celery_app.task(
    name="src.infrastructure.tasks.email_tasks.send_welcome_email_async",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def send_welcome_email_async(
    self, to: str, user_first_name: str, role: str = "SERVANT"
) -> bool:
    """Envoie l'email de bienvenue après inscription. Délègue l'event handler UserRegistered."""
    try:
        from src.infrastructure.services.email_service import EmailService

        result = _run_async(
            EmailService().send_welcome_email(
                to_email=to, user_first_name=user_first_name, role=role
            )
        )
        logger.info("send_welcome_email_async: to=%s role=%s result=%s", to, role, result)
        return result
    except Exception as exc:
        logger.error("send_welcome_email_async: failed to=%s error=%s", to, exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="src.infrastructure.tasks.email_tasks.send_assignment_email_async",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def send_assignment_email_async(
    self,
    to: str,
    user_first_name: str,
    event_title: str,
    event_date: str,
    liturgical_role: str,
    event_location: str = "",
) -> bool:
    """Notifie un servant de son affectation à un événement."""
    try:
        from src.infrastructure.services.email_service import EmailService

        result = _run_async(
            EmailService().send_assignment_notification(
                to_email=to,
                user_first_name=user_first_name,
                event_title=event_title,
                event_date=event_date,
                liturgical_role=liturgical_role,
                event_location=event_location,
            )
        )
        logger.info(
            "send_assignment_email_async: to=%s event=%s result=%s", to, event_title, result
        )
        return result
    except Exception as exc:
        logger.error("send_assignment_email_async: failed to=%s error=%s", to, exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="src.infrastructure.tasks.email_tasks.send_reset_code_email_async",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def send_reset_code_email_async(
    self, to: str, code: str, user_first_name: str = "Utilisateur"
) -> bool:
    """Envoie le code OTP 6 chiffres pour réinitialisation de mot de passe mobile."""
    try:
        from src.infrastructure.services.email_service import EmailService

        result = _run_async(
            EmailService().send_reset_code_email(
                to_email=to, code=code, user_first_name=user_first_name
            )
        )
        logger.info("send_reset_code_email_async: to=%s result=%s", to, result)
        return result
    except Exception as exc:
        logger.error("send_reset_code_email_async: failed to=%s error=%s", to, exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="src.infrastructure.tasks.email_tasks.send_absence_notification_async",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
)
def send_absence_notification_async(
    self,
    parent_email: str,
    parent_first_name: str,
    child_first_name: str,
    child_last_name: str,
    event_title: str,
    event_date: str,
) -> bool:
    """Notifie un parent de l'absence de son enfant à un événement."""
    try:
        from src.infrastructure.services.email_service import EmailService

        result = _run_async(
            EmailService().send_absence_parent_notification(
                to_email=parent_email,
                parent_first_name=parent_first_name,
                child_first_name=child_first_name,
                child_last_name=child_last_name,
                event_title=event_title,
                event_date=event_date,
            )
        )
        logger.info(
            "send_absence_notification_async: parent=%s child=%s %s result=%s",
            parent_email,
            child_first_name,
            child_last_name,
            result,
        )
        return result
    except Exception as exc:
        logger.error("send_absence_notification_async: failed parent=%s error=%s", parent_email, exc)
        raise self.retry(exc=exc)
