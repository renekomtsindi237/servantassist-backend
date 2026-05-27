"""
Endpoints d'administration des emails.

- POST /api/v1/email/test  → envoie un email de test (ADMIN uniquement)
- POST /api/v1/email/notify → envoie une notification générale à un ou plusieurs destinataires
"""
import logging
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from src.core.entities.user import User
from src.infrastructure.services.email_service import EmailService
from src.presentation.dependencies.auth_deps import get_current_admin_user

router = APIRouter()
logger = logging.getLogger(__name__)


class TestEmailRequest(BaseModel):
    to_email: str
    subject: str = "Test ServantAssist — SMTP OK"
    message: str = "Ceci est un email de test envoyé depuis ServantAssist pour vérifier que le service SMTP fonctionne correctement."


class NotifyRequest(BaseModel):
    to_emails: List[str]
    title: str
    body: str
    recipient_name: str = "Membre ServantAssist"


class EmailResult(BaseModel):
    success: bool
    to: str
    detail: str


@router.post(
    "/test",
    response_model=EmailResult,
    summary="Envoyer un email de test (Admin)",
    description="Envoie un email de test pour vérifier la configuration SMTP. Réservé aux administrateurs.",
)
async def send_test_email(
    request: TestEmailRequest,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
) -> EmailResult:
    """Envoie un email de test via SMTP pour valider la configuration."""
    email_service = EmailService()
    ok = await email_service.send_general_notification(
        to_email=request.to_email,
        user_first_name="Administrateur",
        title=request.subject,
        body=request.message,
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Échec de l'envoi de l'email. Vérifiez la configuration SMTP dans le fichier .env.",
        )
    logger.info("Email de test envoyé | to=%s | by=%s", request.to_email, current_admin.id)
    return EmailResult(
        success=True,
        to=request.to_email,
        detail="Email envoyé avec succès.",
    )


@router.post(
    "/notify",
    response_model=List[EmailResult],
    summary="Envoyer une notification générale (Admin)",
    description="Envoie une notification générale à un ou plusieurs destinataires. Réservé aux administrateurs.",
)
async def send_notification(
    request: NotifyRequest,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
) -> List[EmailResult]:
    """Envoie une notification générale à plusieurs destinataires."""
    email_service = EmailService()
    results = []
    for email in request.to_emails:
        ok = await email_service.send_general_notification(
            to_email=email,
            user_first_name=request.recipient_name,
            title=request.title,
            body=request.body,
        )
        results.append(EmailResult(
            success=ok,
            to=email,
            detail="Envoyé." if ok else "Échec d'envoi.",
        ))
    logger.info(
        "Notifications envoyées | count=%d | by=%s",
        len(request.to_emails),
        current_admin.id,
    )
    return results
