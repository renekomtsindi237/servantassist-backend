"""
Unit tests for EmailService.
All tests patch SMTP and template functions to avoid real network calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_service(app_env="testing", smtp_user="", smtp_password="", debug=False):
    """Create an EmailService with mocked settings."""
    with patch("src.infrastructure.services.email_service.get_settings") as mock_gs:
        settings = MagicMock()
        settings.APP_ENV = app_env
        settings.SMTP_USER = smtp_user
        settings.SMTP_PASSWORD = smtp_password
        settings.SMTP_HOST = "smtp.example.com"
        settings.SMTP_PORT = 587
        settings.SMTP_FROM = "noreply@example.com"
        settings.SMTP_FROM_NAME = "TestApp"
        settings.SMTP_REPLY_TO = ""
        settings.SMTP_USE_TLS = True
        settings.FRONTEND_URL = "https://example.com"
        settings.APP_DEBUG = debug
        mock_gs.return_value = settings
        from src.infrastructure.services.email_service import EmailService

        svc = EmailService()
        svc._settings = settings
    return svc


# ─────────────────────────────────────────────────────────────────────────────
#  Properties
# ─────────────────────────────────────────────────────────────────────────────


def test_is_smtp_configured_true():
    svc = _make_service(smtp_user="user@example.com", smtp_password="pass")
    assert svc._is_smtp_configured is True


def test_is_smtp_configured_false():
    svc = _make_service(smtp_user="", smtp_password="")
    assert svc._is_smtp_configured is False


def test_is_testing_true():
    svc = _make_service(app_env="testing")
    assert svc._is_testing is True


def test_is_testing_false():
    svc = _make_service(app_env="production")
    assert svc._is_testing is False


# ─────────────────────────────────────────────────────────────────────────────
#  send_email — testing mode
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_email_testing_mode_logs_and_returns_true():
    svc = _make_service(app_env="testing")
    result = await svc.send_email("to@example.com", "Subject", "<p>body</p>")
    assert result is True


@pytest.mark.asyncio
async def test_send_email_testing_mode_with_debug():
    svc = _make_service(app_env="testing", debug=True)
    result = await svc.send_email("to@example.com", "Subj", "<p>body</p>")
    assert result is True


# ─────────────────────────────────────────────────────────────────────────────
#  send_email — SMTP not configured
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_email_no_smtp_returns_false():
    svc = _make_service(app_env="production", smtp_user="", smtp_password="")
    result = await svc.send_email("to@example.com", "Subject", "<p>body</p>")
    assert result is False


# ─────────────────────────────────────────────────────────────────────────────
#  send_email — SMTP configured, success
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_email_smtp_success():
    svc = _make_service(app_env="production", smtp_user="user", smtp_password="pass")
    with patch.object(svc, "_send_smtp", new_callable=AsyncMock) as mock_smtp:
        result = await svc.send_email("to@example.com", "Subject", "<p>body</p>")
    assert result is True
    mock_smtp.assert_called_once()


@pytest.mark.asyncio
async def test_send_email_smtp_exception_returns_false():
    svc = _make_service(app_env="production", smtp_user="user", smtp_password="pass")
    with patch.object(svc, "_send_smtp", side_effect=Exception("SMTP error")):
        result = await svc.send_email("to@example.com", "Subject", "<p>body</p>")
    assert result is False


# ─────────────────────────────────────────────────────────────────────────────
#  _send_smtp
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_smtp_success():
    svc = _make_service(app_env="production", smtp_user="user", smtp_password="pass")
    svc._settings.SMTP_PORT = 587

    with patch("src.infrastructure.services.email_service.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
        await svc._send_smtp("to@example.com", "Subject", "<p>test</p>")
    mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_send_smtp_ssl_port():
    svc = _make_service(app_env="production", smtp_user="user", smtp_password="pass")
    svc._settings.SMTP_PORT = 465

    with patch("src.infrastructure.services.email_service.aiosmtplib.send", new_callable=AsyncMock):
        await svc._send_smtp("to@example.com", "Subject", "<p>ssl</p>")


@pytest.mark.asyncio
async def test_send_smtp_auth_error():
    import aiosmtplib

    svc = _make_service(app_env="production", smtp_user="user", smtp_password="pass")

    with patch(
        "src.infrastructure.services.email_service.aiosmtplib.send",
        side_effect=aiosmtplib.SMTPAuthenticationError(535, "Auth failed"),
    ):
        with pytest.raises(aiosmtplib.SMTPAuthenticationError):
            await svc._send_smtp("to@example.com", "Subject", "<p>test</p>")


@pytest.mark.asyncio
async def test_send_smtp_os_error():
    svc = _make_service(app_env="production", smtp_user="user", smtp_password="pass")

    with patch("src.infrastructure.services.email_service.aiosmtplib.send", side_effect=OSError("connection refused")):
        with pytest.raises(OSError):
            await svc._send_smtp("to@example.com", "Subject", "<p>test</p>")


# ─────────────────────────────────────────────────────────────────────────────
#  Business email methods (all in testing mode)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_reset_password_email():
    svc = _make_service()
    result = await svc.send_reset_password_email("user@example.com", "token123", "Jean")
    assert result is True


@pytest.mark.asyncio
async def test_send_reset_code_email():
    svc = _make_service()
    result = await svc.send_reset_code_email("user@example.com", "123456", "Jean")
    assert result is True


@pytest.mark.asyncio
async def test_send_password_changed_email():
    svc = _make_service()
    result = await svc.send_password_changed_email("user@example.com", "Jean")
    assert result is True


@pytest.mark.asyncio
async def test_send_assignment_notification():
    svc = _make_service()
    result = await svc.send_assignment_notification(
        "user@example.com", "Jean", "Messe du dimanche", "2026-06-21", "SERVANT_AUTEL", "Cathédrale"
    )
    assert result is True


@pytest.mark.asyncio
async def test_send_event_reminder():
    svc = _make_service()
    result = await svc.send_event_reminder(
        "user@example.com", "Jean", "Messe du dimanche", "2026-06-21", "Cathédrale", "SERVANT"
    )
    assert result is True


@pytest.mark.asyncio
async def test_send_absence_parent_notification():
    svc = _make_service()
    result = await svc.send_absence_parent_notification(
        "parent@example.com", "Marie", "Jean", "Dupont", "Messe", "2026-06-21"
    )
    assert result is True


@pytest.mark.asyncio
async def test_send_general_notification():
    svc = _make_service()
    result = await svc.send_general_notification("user@example.com", "Jean", "Titre de la notif", "Corps du message")
    assert result is True


@pytest.mark.asyncio
async def test_send_invitation_code_email():
    svc = _make_service()
    result = await svc.send_invitation_code_email("parent@example.com", "Marie Dupont", "ABC123", "PARENT")
    assert result is True


@pytest.mark.asyncio
async def test_send_absence_warning_email():
    svc = _make_service()
    result = await svc.send_absence_warning_email("servant@example.com", "Jean", "Dupont", 3, "2026-06-21")
    assert result is True


@pytest.mark.asyncio
async def test_send_parent_convocation_email():
    svc = _make_service()
    result = await svc.send_parent_convocation_email("parent@example.com", "Marie", "Jean", "Dupont", 5)
    assert result is True


@pytest.mark.asyncio
async def test_send_welcome_email():
    svc = _make_service()
    result = await svc.send_welcome_email("user@example.com", "Jean", "SERVANT")
    assert result is True


@pytest.mark.asyncio
async def test_send_welcome_email_defaults():
    svc = _make_service()
    result = await svc.send_welcome_email("user@example.com")
    assert result is True


def test_logo_url_points_to_an_existing_static_file():
    """Régression : `_logo_url()` a longtemps pointé vers
    `logo_servant_mail.png`, un fichier qui n'a jamais existé sur disque —
    chaque email envoyé affichait une icône d'image cassée. Verrouille que
    le fichier référencé existe réellement sous `static/`."""
    from pathlib import Path

    from src.infrastructure.services.email_templates import _logo_url

    with patch("src.infrastructure.services.email_templates.get_settings") as mock_gs:
        settings = MagicMock()
        settings.APP_URL = "http://localhost:8000"
        mock_gs.return_value = settings
        url = _logo_url()

    relative_path = url.split("/static/", 1)[1]
    static_file = Path(__file__).resolve().parents[2] / "static" / relative_path
    assert static_file.is_file(), f"Logo référencé dans les emails introuvable sur disque : {static_file}"
