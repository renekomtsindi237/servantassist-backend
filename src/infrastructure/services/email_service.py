"""
Service d'envoi d'emails transactionnels via SMTP.

Modes de fonctionnement :
- **production**  : envoi reel via SMTP (Gmail, SendGrid, etc.)
- **development** : envoi reel si SMTP_USER est configure, sinon log + fichier
- **testing**     : pas d'envoi, log uniquement

Configuration requise pour l'envoi reel (.env) :
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USER=ton.email@gmail.com
  SMTP_PASSWORD=ton-app-password       # Mot de passe d'application Google
  SMTP_FROM=noreply@servantassist.com
  SMTP_FROM_NAME=ServantAssist
  FRONTEND_URL=https://ton-domaine.com
"""
import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import aiosmtplib
from loguru import logger

from src.infrastructure.config.settings import get_settings
from src.infrastructure.services.email_templates import (
    render_absence_parent_notification,
    render_absence_warning,
    render_assignment_notification,
    render_event_reminder,
    render_forgot_password,
    render_general_notification,
    render_invitation_code,
    render_parent_convocation,
    render_password_changed,
    render_reset_code_email,
    render_welcome_email,
)


class EmailService:
    """Service d'envoi d'emails avec SMTP async."""

    def __init__(self) -> None:
        self._settings = get_settings()

    # ── Proprietes utiles ────────────────────────────────────────────────

    @property
    def _is_smtp_configured(self) -> bool:
        """Verifie que les credentials SMTP sont renseignes."""
        return bool(self._settings.SMTP_USER and self._settings.SMTP_PASSWORD)

    @property
    def _is_testing(self) -> bool:
        return self._settings.APP_ENV == "testing"

    # ── Envoi bas niveau ─────────────────────────────────────────────────

    async def _send_smtp(
        self,
        to_email: str,
        subject: str,
        html_body: str,
    ) -> None:
        """
        Envoie un email via SMTP avec aiosmtplib.

        Supporte STARTTLS (port 587) et SSL direct (port 465).
        """
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{
    self._settings.SMTP_FROM_NAME} <{
        self._settings.SMTP_FROM}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg["X-Mailer"] = "ServantAssist/1.0"
        msg["X-Priority"] = "3"  # Normal

        # Version texte brut (fallback)
        plain_text = (
            f"ServantAssist\n\n"
            f"Sujet : {subject}\n\n"
            f"Cet email est au format HTML. Si vous ne pouvez pas le lire, "
            f"veuillez utiliser un client email compatible.\n"
        )
        msg.attach(MIMEText(plain_text, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        # Determiner si on utilise SSL direct ou STARTTLS
        use_tls = self._settings.SMTP_PORT == 465
        start_tls = self._settings.SMTP_USE_TLS and not use_tls

        try:
            await aiosmtplib.send(
                msg,
                hostname=self._settings.SMTP_HOST,
                port=self._settings.SMTP_PORT,
                username=self._settings.SMTP_USER,
                password=self._settings.SMTP_PASSWORD,
                use_tls=use_tls,
                start_tls=start_tls,
                timeout=30,
            )
            logger.info(
                "Email envoye avec succes | to={to} | subject={subject}",
                to=to_email,
                subject=subject,
            )
        except aiosmtplib.SMTPAuthenticationError as exc:
            logger.error(
                "Echec authentification SMTP | host={host} | user={user} | error={error}",
                host=self._settings.SMTP_HOST,
                user=self._settings.SMTP_USER,
                error=str(exc),
            )
            raise
        except (aiosmtplib.SMTPException, OSError) as exc:
            logger.error(
                "Echec envoi email | to={to} | subject={subject} | error={error}",
                to=to_email,
                subject=subject,
                error=str(exc),
            )
            raise

    def _log_email(self, to_email: str, subject: str, html_body: str) -> None:
        """Log l'email au lieu de l'envoyer (dev/testing)."""
        logger.info(
            "EMAIL [mode dev/test] | to={to} | subject={subject}",
            to=to_email,
            subject=subject,
        )
        # En mode debug, on ajoute des details de diagnostic
        if self._settings.APP_DEBUG:
            logger.debug(
                "EMAIL DEBUG | env={env} | to={to} | subject={subject} | smtp_configured={smtp}",
                env=self._settings.APP_ENV,
                to=to_email,
                subject=subject,
                smtp=self._is_smtp_configured,
            )

    # ── Methode d'envoi principale ───────────────────────────────────────

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
    ) -> bool:
        """
        Point d'entree principal pour envoyer un email.

        En testing : log uniquement, retourne True.
        En dev/prod avec SMTP configure : envoi reel.
        En dev sans SMTP : log uniquement avec avertissement.

        Retourne True si l'email a ete envoye (ou logue) avec succes.
        """
        # Mode test : jamais d'envoi reel
        if self._is_testing:
            self._log_email(to_email, subject, html_body)
            return True

        # SMTP non configure : fallback log
        if not self._is_smtp_configured:
            logger.warning(
                "SMTP non configure — email non envoye | to={to} | " "Configurez SMTP_USER et SMTP_PASSWORD dans .env",
                to=to_email,
            )
            self._log_email(to_email, subject, html_body)
            return False

        # Envoi reel via SMTP
        try:
            await self._send_smtp(to_email, subject, html_body)
            return True
        except Exception as exc:
            logger.error(
                "Impossible d'envoyer l'email | to={to} | error={error} | type={type}",
                to=to_email,
                error=str(exc),
                type=type(exc).__name__,
            )
            # On ne propage PAS l'exception pour ne pas bloquer le flux utilisateur
            # (forgot-password doit toujours retourner 200)
            return False

    # ── Emails metier ────────────────────────────────────────────────────

    async def send_reset_password_email(
        self,
        to_email: str,
        token: str,
        user_first_name: str = "Utilisateur",
    ) -> bool:
        """
        Envoie l'email de reinitialisation de mot de passe.

        Genere un lien vers le frontend avec le token en parametre.
        """
        frontend_url = self._settings.FRONTEND_URL.rstrip("/")
        reset_link = f"{frontend_url}/auth/reset-password?token={token}"

        subject, html_body = render_forgot_password(
            user_first_name=user_first_name,
            reset_link=reset_link,
            expiry_minutes=15,
        )

        logger.info(
            "Envoi email reset password | to={to} | link={link}",
            to=to_email,
            link=reset_link,
        )
        return await self.send_email(to_email, subject, html_body)

    async def send_reset_code_email(
        self,
        to_email: str,
        code: str,
        user_first_name: str = "Utilisateur",
    ) -> bool:
        """Envoie le code OTP 6 chiffres pour réinitialisation mobile."""
        subject, html_body = render_reset_code_email(
            user_first_name=user_first_name,
            code=code,
        )
        logger.info(
            "Envoi code OTP reset | to={to}",
            to=to_email,
        )
        return await self.send_email(to_email, subject, html_body)

    async def send_password_changed_email(
        self,
        to_email: str,
        user_first_name: str = "Utilisateur",
    ) -> bool:
        """
        Envoie un email de confirmation apres changement de mot de passe.

        Bonne pratique de securite : informer l'utilisateur.
        """
        frontend_url = self._settings.FRONTEND_URL.rstrip("/")
        login_link = f"{frontend_url}/auth/login"

        subject, html_body = render_password_changed(
            user_first_name=user_first_name,
            login_link=login_link,
        )

        logger.info(
            "Envoi email confirmation changement MDP | to={to}",
            to=to_email,
        )
        return await self.send_email(to_email, subject, html_body)

    async def send_assignment_notification(
        self,
        to_email: str,
        user_first_name: str,
        event_title: str,
        event_date: str,
        liturgical_role: str,
        event_location: str = "",
    ) -> bool:
        """Notifie un servant de sa nouvelle affectation a un evenement."""
        subject, html_body = render_assignment_notification(
            user_first_name=user_first_name,
            event_title=event_title,
            event_date=event_date,
            liturgical_role=liturgical_role,
            event_location=event_location,
        )
        logger.info(
            "Envoi email affectation | to={to} | event={event}",
            to=to_email,
            event=event_title,
        )
        return await self.send_email(to_email, subject, html_body)

    async def send_event_reminder(
        self,
        to_email: str,
        user_first_name: str,
        event_title: str,
        event_date: str,
        event_location: str = "",
        liturgical_role: str = "",
    ) -> bool:
        """Envoie un rappel 24h avant un evenement."""
        subject, html_body = render_event_reminder(
            user_first_name=user_first_name,
            event_title=event_title,
            event_date=event_date,
            event_location=event_location,
            liturgical_role=liturgical_role,
        )
        logger.info(
            "Envoi email rappel evenement | to={to} | event={event}",
            to=to_email,
            event=event_title,
        )
        return await self.send_email(to_email, subject, html_body)

    async def send_absence_parent_notification(
        self,
        to_email: str,
        parent_first_name: str,
        child_first_name: str,
        child_last_name: str,
        event_title: str,
        event_date: str,
    ) -> bool:
        """Notifie un parent de l'absence de son enfant a un evenement."""
        subject, html_body = render_absence_parent_notification(
            parent_first_name=parent_first_name,
            child_first_name=child_first_name,
            child_last_name=child_last_name,
            event_title=event_title,
            event_date=event_date,
        )
        logger.info(
            "Envoi email absence parent | to={to} | child={child}",
            to=to_email,
            child=f"{child_first_name} {child_last_name}",
        )
        return await self.send_email(to_email, subject, html_body)

    async def send_general_notification(
        self,
        to_email: str,
        user_first_name: str,
        title: str,
        body: str,
    ) -> bool:
        """Envoie une notification generale."""
        subject, html_body = render_general_notification(
            user_first_name=user_first_name,
            title=title,
            body=body,
        )
        logger.info(
            "Envoi email notification generale | to={to} | title={title}",
            to=to_email,
            title=title,
        )
        return await self.send_email(to_email, subject, html_body)

    async def send_invitation_code_email(
        self,
        to_email: str,
        parent_name: str,
        code: str,
        role: str = "PARENT",
    ) -> bool:
        """Envoie le code d'invitation à un parent par email."""
        subject, html_body = render_invitation_code(
            parent_name=parent_name,
            code=code,
            role=role,
        )
        logger.info(
            "Envoi email code invitation | to={to} | code={code}",
            to=to_email,
            code=code,
        )
        return await self.send_email(to_email, subject, html_body)

    async def send_absence_warning_email(
        self,
        to_email: str,
        servant_first_name: str,
        servant_last_name: str,
        absent_count: int,
        session_date: str,
    ) -> bool:
        """Envoie un avertissement au servant après 3 absences."""
        subject, html_body = render_absence_warning(
            servant_first_name=servant_first_name,
            servant_last_name=servant_last_name,
            absent_count=absent_count,
            session_date=session_date,
        )
        logger.info(
            "Envoi email avertissement absence | to={to} | absences={n}",
            to=to_email,
            n=absent_count,
        )
        return await self.send_email(to_email, subject, html_body)

    async def send_parent_convocation_email(
        self,
        to_email: str,
        parent_first_name: str,
        servant_first_name: str,
        servant_last_name: str,
        absent_count: int,
    ) -> bool:
        """Envoie une convocation au parent après 5 absences du servant."""
        subject, html_body = render_parent_convocation(
            parent_first_name=parent_first_name,
            servant_first_name=servant_first_name,
            servant_last_name=servant_last_name,
            absent_count=absent_count,
        )
        logger.info(
            "Envoi email convocation parent | to={to} | servant={servant} | absences={n}",
            to=to_email,
            servant=f"{servant_first_name} {servant_last_name}",
            n=absent_count,
        )
        return await self.send_email(to_email, subject, html_body)

    async def send_welcome_email(
        self,
        to_email: str,
        user_first_name: str = "Utilisateur",
        role: str = "SERVANT",
    ) -> bool:
        """
        Envoie l'email de bienvenue après inscription.

        Appelé automatiquement via l'event handler UserRegistered.
        """
        frontend_url = self._settings.FRONTEND_URL.rstrip("/")
        login_link = f"{frontend_url}/login"

        subject, html_body = render_welcome_email(
            user_first_name=user_first_name,
            role=role,
            login_link=login_link,
        )

        logger.info(
            "Envoi email bienvenue | to={to} | role={role}",
            to=to_email,
            role=role,
        )
        return await self.send_email(to_email, subject, html_body)
