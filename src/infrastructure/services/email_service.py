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
from src.infrastructure.services.email_templates import render_forgot_password, render_password_changed


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
        msg["From"] = f"{self._settings.SMTP_FROM_NAME} <{self._settings.SMTP_FROM}>"
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
        # En mode debug, on affiche aussi dans stdout
        if self._settings.APP_DEBUG:
            print(f"\n{'='*70}")
            print(f"  EMAIL (non envoye — mode {self._settings.APP_ENV})")
            print(f"  To      : {to_email}")
            print(f"  Subject : {subject}")
            print(
                f"  SMTP    : {'configure' if self._is_smtp_configured else 'NON configure'}"
            )
            print(f"{'='*70}\n")

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
                "SMTP non configure — email non envoye | to={to} | "
                "Configurez SMTP_USER et SMTP_PASSWORD dans .env",
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
                "Impossible d'envoyer l'email | to={to} | error={error}",
                to=to_email,
                error=str(exc),
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
