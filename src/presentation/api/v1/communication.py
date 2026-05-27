"""
Endpoints du module Communication / Notifications.

Endpoints :
- POST   /notify           : envoyer une notification individuelle (admin/aumonier)
- POST   /broadcast        : envoyer a un groupe (admin/aumonier)
- GET    /me               : mes notifications IN_APP
- GET    /me/stats         : mes statistiques
- GET    /me/{id}          : detail d'une notification
- POST   /me/read          : marquer comme lues
- GET    /me/preferences   : mes preferences de canal
- PUT    /me/preferences   : mettre a jour une preference
- GET    /history          : historique admin de toutes les notifications
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

import logging

from src.application.services.notification_service import NotificationService
from src.core.entities.notification import (
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)
from src.core.entities.user import User
from src.infrastructure.database.session import get_db_session
from src.presentation.dependencies.auth_deps import (
    get_current_active_user,
    get_current_admin_or_aumonier,
)

logger = logging.getLogger(__name__)
from src.presentation.schemas.notification import (
    BroadcastResponse,
    NotificationBroadcast,
    NotificationMarkRead,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    NotificationResponse,
    NotificationSend,
    NotificationStatsResponse,
)

router = APIRouter()


def _get_service(session: AsyncSession, request: Request = None) -> NotificationService:
    ws_manager = getattr(request.app.state, "ws_manager", None) if request else None
    return NotificationService(session, ws_manager=ws_manager)


# ══════════════════════════════════════════════════════════════════════════
#  Admin / Aumonier : envoi
# ══════════════════════════════════════════════════════════════════════════


@router.post(
    "/notify",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Envoyer une notification individuelle",
)
async def send_notification(
    data: NotificationSend,
    request: Request,
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Envoie une notification a un utilisateur specifique."""
    service = _get_service(session, request)
    notification = await service.send_notification(
        recipient_id=data.recipient_id,
        notification_type=data.notification_type,
        channel=data.channel,
        priority=data.priority,
        title=data.title,
        body=data.body,
        sent_by=current_user.id,
        related_entity_type=data.related_entity_type,
        related_entity_id=data.related_entity_id,
    )
    enriched = await service.repo.enrich(notification)
    return enriched


@router.post(
    "/broadcast",
    response_model=BroadcastResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Envoyer une notification a un groupe",
)
async def broadcast_notification(
    data: NotificationBroadcast,
    request: Request,
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Envoie une notification a un groupe de destinataires.

    Targets :
    - ``all`` : tous les utilisateurs actifs
    - ``servants`` : tous les servants
    - ``parents`` : tous les parents
    - ``responsables`` : servants avec nomination active
    - ``subgroup:<uuid>`` : membres d'un sous-groupe
    """
    service = _get_service(session, request)
    result = await service.broadcast(
        target=data.target,
        notification_type=data.notification_type,
        channel=data.channel,
        priority=data.priority,
        title=data.title,
        body=data.body,
        sent_by=current_user.id,
        related_entity_type=data.related_entity_type,
        related_entity_id=data.related_entity_id,
    )
    return result


# ══════════════════════════════════════════════════════════════════════════
#  Self-service : notifications de l'utilisateur connecte
# ══════════════════════════════════════════════════════════════════════════


@router.get(
    "/me",
    response_model=list[NotificationResponse],
    summary="Mes notifications",
)
async def get_my_notifications(
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    notification_type: Optional[NotificationType] = Query(default=None),
    status_filter: Optional[NotificationStatus] = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Recupere mes notifications IN_APP (avec pagination)."""
    service = _get_service(session)
    return await service.get_user_notifications(
        current_user.id,
        notification_type=notification_type,
        status=status_filter,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/me/stats",
    response_model=NotificationStatsResponse,
    summary="Mes statistiques de notifications",
)
async def get_my_notification_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Retourne les statistiques de notifications de l'utilisateur connecte."""
    service = _get_service(session)
    return await service.get_user_stats(current_user.id)


@router.post(
    "/me/read",
    summary="Marquer des notifications comme lues",
)
async def mark_notifications_read(
    data: NotificationMarkRead,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Marque une ou plusieurs notifications comme lues."""
    service = _get_service(session)
    count = await service.mark_as_read(data.notification_ids, current_user.id)
    return {"marked_read": count}


# ══════════════════════════════════════════════════════════════════════════
#  Preferences de notification
# ══════════════════════════════════════════════════════════════════════════


@router.get(
    "/me/preferences",
    response_model=list[NotificationPreferenceResponse],
    summary="Mes preferences de notification",
)
async def get_my_preferences(
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Recupere les preferences de notification de l'utilisateur connecte."""
    service = _get_service(session)
    return await service.get_preferences(current_user.id)


@router.put(
    "/me/preferences",
    response_model=NotificationPreferenceResponse,
    summary="Mettre a jour une preference",
)
async def update_my_preference(
    data: NotificationPreferenceUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Met a jour une preference de canal de notification."""
    service = _get_service(session)
    return await service.update_preference(
        current_user.id,
        data.notification_type,
        email_enabled=data.email_enabled,
        whatsapp_enabled=data.whatsapp_enabled,
        in_app_enabled=data.in_app_enabled,
    )


# ══════════════════════════════════════════════════════════════════════════
#  Detail d'une notification (APRES les routes statiques /me/*)
# ══════════════════════════════════════════════════════════════════════════


@router.get(
    "/me/{notification_id}",
    response_model=NotificationResponse,
    summary="Detail d'une notification",
)
async def get_my_notification(
    notification_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Recupere le detail d'une notification specifique."""
    service = _get_service(session)
    data = await service.get_notification(notification_id, current_user.id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification non trouvee.",
        )
    return data


# ══════════════════════════════════════════════════════════════════════════
#  Historique admin
# ══════════════════════════════════════════════════════════════════════════


@router.get(
    "/history",
    summary="Historique des notifications (admin)",
)
async def get_notification_history(
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    notification_type: Optional[NotificationType] = Query(default=None),
    channel: Optional[NotificationChannel] = Query(default=None),
    status_filter: Optional[NotificationStatus] = Query(default=None, alias="status"),
    broadcast_id: Optional[UUID] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Listing admin de toutes les notifications avec filtres."""
    service = _get_service(session)
    return await service.get_all_notifications(
        notification_type=notification_type,
        channel=channel,
        status=status_filter,
        broadcast_id=broadcast_id,
        limit=limit,
        offset=offset,
    )


# ══════════════════════════════════════════════════════════════════════════
#  WebSocket — Notifications temps réel
# ══════════════════════════════════════════════════════════════════════════


@router.websocket("/ws")
async def websocket_notifications(
    websocket: WebSocket,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    token: str = Query(..., description="JWT access token"),
):
    """
    Connexion WebSocket pour les notifications temps réel.

    Le client envoie son JWT via le query parameter `token`.
    Il reçoit en push les notifications IN_APP qui lui sont destinées.

    Exemple de connexion :
        ws://localhost:8000/api/v1/communication/ws?token=<access_token>

    Format des messages reçus :
        {
          "id": "uuid",
          "type": "GENERAL|AFFECTATION|...",
          "title": "...",
          "body": "...",
          "created_at": "iso8601"
        }
    """
    from src.presentation.dependencies.auth_deps import validate_ws_token

    # Valider le JWT avant d'accepter la connexion
    try:
        user = await validate_ws_token(token, session)
    except Exception:
        await websocket.close(code=4001, reason="Token invalide ou expiré.")
        return

    ws_manager = getattr(websocket.app.state, "ws_manager", None)
    if ws_manager is None:
        await websocket.close(code=4000, reason="WebSocket non disponible.")
        return

    user_id = str(user.id)
    await ws_manager.connect(websocket, user_id)
    try:
        # Garder la connexion ouverte — ping/pong natif géré par uvicorn
        while True:
            # Attendre un message texte (heartbeat ou commande client)
            data = await websocket.receive_text()
            # Répondre au ping client si besoin
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(websocket, user_id)
        logger.info("WebSocket closed for user_id=%s", user_id)
