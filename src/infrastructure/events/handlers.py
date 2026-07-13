"""
Handlers d'événements de domaine.

Chaque handler réagit à un ou plusieurs DomainEvent sans modifier
les services émetteurs (principe Open/Closed).

Ce module est importé une seule fois au démarrage de l'application
(dans main.py lifespan) pour enregistrer tous les handlers.
"""

import logging

from src.core.events.domain_events import (
    AttendanceRecorded,
    DisciplineCaseOpened,
    DisciplineSanctionIssued,
    PasswordReset,
    UserActivated,
    UserDeactivated,
    UserDeleted,
    UserInvited,
    UserRegistered,
)
from src.infrastructure.events.bus import event_bus
from src.infrastructure.services.email_service import EmailService

logger = logging.getLogger(__name__)


# ── Handlers Audit ────────────────────────────────────────────────────────────


@event_bus.handler(UserRegistered)
async def audit_user_registered(event: UserRegistered) -> None:
    logger.info(
        "AUDIT | UserRegistered | user_id=%s role=%s by_admin=%s",
        event.user_id,
        event.role,
        event.created_by_admin,
    )


@event_bus.handler(UserRegistered)
async def notify_user_registered(event: UserRegistered) -> None:
    """Envoie l'email de bienvenue — ADMIN et AUMÔNIER uniquement (PARENT/SERVANT n'utilisent pas l'email)."""
    if not event.email or event.created_by_admin:
        return
    if event.role not in ("ADMIN", "AUMÔNIER"):
        return
    try:
        await EmailService().send_welcome_email(
            to_email=event.email,
            user_first_name=event.first_name or event.email.split("@")[0].capitalize(),
            role=event.role,
        )
    except Exception as exc:
        logger.error("Erreur envoi email bienvenue | error=%s", exc)


@event_bus.handler(UserInvited)
async def audit_user_invited(event: UserInvited) -> None:
    logger.info(
        "AUDIT | UserInvited | invitation=%s by=%s role=%s",
        event.invitation_id,
        event.created_by_id,
        event.role,
    )


@event_bus.handler(PasswordReset)
async def audit_password_reset(event: PasswordReset) -> None:
    logger.info(
        "AUDIT | PasswordReset | user_id=%s by_admin=%s",
        event.user_id,
        event.reset_by_admin_id,
    )


@event_bus.handler(UserDeactivated)
async def audit_user_deactivated(event: UserDeactivated) -> None:
    logger.info(
        "AUDIT | UserDeactivated | user_id=%s by=%s",
        event.user_id,
        event.deactivated_by_id,
    )


@event_bus.handler(UserActivated)
async def audit_user_activated(event: UserActivated) -> None:
    logger.info("AUDIT | UserActivated | user_id=%s", event.user_id)


@event_bus.handler(UserDeleted)
async def audit_user_deleted(event: UserDeleted) -> None:
    logger.info(
        "AUDIT | UserDeleted | user_id=%s by=%s",
        event.user_id,
        event.deleted_by_id,
    )


@event_bus.handler(DisciplineCaseOpened)
async def audit_discipline_case_opened(event: DisciplineCaseOpened) -> None:
    logger.info(
        "AUDIT | DisciplineCaseOpened | case=%s accused=%s category=%s by=%s",
        event.case_id,
        event.accused_user_id,
        event.offense_category,
        event.opened_by_id,
    )


@event_bus.handler(DisciplineSanctionIssued)
async def audit_discipline_sanction(event: DisciplineSanctionIssued) -> None:
    logger.info(
        "AUDIT | DisciplineSanctionIssued | case=%s accused=%s sanction=%s by=%s",
        event.case_id,
        event.accused_user_id,
        event.sanction_type,
        event.issued_by_id,
    )


@event_bus.handler(AttendanceRecorded)
async def audit_attendance_recorded(event: AttendanceRecorded) -> None:
    logger.debug(
        "AUDIT | AttendanceRecorded | id=%s user=%s type=%s status=%s",
        event.attendance_id,
        event.user_id,
        event.attendance_type,
        event.status,
    )


# ── Handlers Notification (hooks futurs) ──────────────────────────────────────
# Ces handlers peuvent envoyer des emails/WhatsApp quand l'infrastructure
# de notification est configurée. Actuellement ils loguent uniquement.


@event_bus.handler(UserInvited)
async def notify_user_invited(event: UserInvited) -> None:
    """Envoie le code d'invitation par email si disponible."""
    if not event.email:
        return
    try:
        from src.infrastructure.services.email_service import EmailService

        await EmailService().send_general_notification(
            to_email=event.email,
            user_first_name=event.email.split("@")[0].capitalize(),
            title="Votre code d'invitation ServantAssist",
            body=(
                "Votre code d'invitation est prêt. "
                "Rendez-vous sur la plateforme ServantAssist pour l'utiliser lors de votre inscription."
            ),
        )
    except Exception as exc:
        logger.error("Erreur envoi email invitation | error=%s", exc)


@event_bus.handler(DisciplineCaseOpened)
async def notify_discipline_accused(event: DisciplineCaseOpened) -> None:
    """
    Notifie l'accusé de l'ouverture d'un dossier disciplinaire.

    - Log d'audit enrichi avec les données de l'accusé.
    - Envoi d'email si l'adresse est disponible dans l'event.
    - La notification in-app est créée via une tâche Celery pour ne pas
      bloquer le handler (absence de session DB ici).
    """
    logger.info(
        "NOTIFY | DisciplineCaseOpened | case=%s accused_id=%s accused_email=%s category=%s",
        event.case_id,
        event.accused_user_id,
        event.accused_email or "N/A",
        event.offense_category,
    )

    if not event.accused_email:
        return

    try:
        first_name = event.accused_first_name or event.accused_email.split("@")[0].capitalize()
        await EmailService().send_general_notification(
            to_email=event.accused_email,
            user_first_name=first_name,
            title="Ouverture d'un dossier disciplinaire vous concernant",
            body=(
                f"Un dossier disciplinaire (catégorie : {event.offense_category}) "
                "a été ouvert vous concernant. "
                "Vous serez contacté prochainement par l'aumônier ou le délégué "
                "pour la suite de la procédure."
            ),
        )
    except Exception as exc:
        logger.error(
            "Erreur envoi email dossier disciplinaire | accused=%s error=%s",
            event.accused_user_id,
            exc,
        )


@event_bus.handler(PasswordReset)
async def notify_password_reset(event: PasswordReset) -> None:
    """
    Envoie une confirmation par email après réinitialisation du mot de passe.

    Bonne pratique de sécurité : l'utilisateur est informé que son mot de
    passe a été modifié, lui permettant de réagir s'il ne l'a pas demandé.
    """
    logger.info(
        "NOTIFY | PasswordReset | user_id=%s by_admin=%s has_email=%s",
        event.user_id,
        bool(event.reset_by_admin_id),
        bool(event.email),
    )

    if not event.email:
        return

    try:
        first_name = event.first_name or event.email.split("@")[0].capitalize()
        await EmailService().send_password_changed_email(
            to_email=event.email,
            user_first_name=first_name,
        )
    except Exception as exc:
        logger.error(
            "Erreur envoi email confirmation réinitialisation | user=%s error=%s",
            event.user_id,
            exc,
        )


def register_all_handlers() -> None:
    """
    Appelé au démarrage de l'application pour s'assurer que tous les handlers
    sont enregistrés. Les décorateurs @event_bus.handler() s'exécutent à
    l'import du module, donc il suffit d'importer ce fichier.
    Cette fonction existe pour rendre l'intention explicite dans main.py.
    """
    logger.info("EventBus: %d event types have registered handlers", len(event_bus._handlers))
