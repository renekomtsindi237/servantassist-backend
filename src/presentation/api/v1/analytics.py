"""
Endpoints Analytics — métriques GA4 (via service account backend) + connexions geo.
Réservés aux admins. Résultats mis en cache Redis.
"""

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.entities.user import User
from src.infrastructure.config.settings import get_settings
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.connection_log_repository import ConnectionLogRepository
from src.infrastructure.services.google_analytics_service import get_realtime, get_today_summary
from src.presentation.dependencies.auth_deps import get_current_admin_user

logger = logging.getLogger(__name__)
router = APIRouter()

_REDIS_KEY_RT = "analytics:ga4:realtime"
_REDIS_KEY_SUM = "analytics:ga4:summary"
_TTL_RT = 60   # 1 minute
_TTL_SUM = 300  # 5 minutes


async def _redis():
    """Tente de récupérer le client Redis applicatif (optionnel)."""
    try:
        from src.infrastructure.security.brute_force import brute_force_guard
        return brute_force_guard._redis  # même instance Redis
    except Exception:
        return None


@router.get("/realtime")
async def analytics_realtime(
    _: Annotated[User, Depends(get_current_admin_user)],
) -> dict:
    """Métriques GA4 temps réel : utilisateurs actifs (30 min), events, pages vues."""
    settings = get_settings()
    redis = await _redis()

    if redis:
        cached = await redis.get(_REDIS_KEY_RT)
        if cached:
            return json.loads(cached)

    data = await get_realtime(settings.GOOGLE_SA_JSON, settings.GA4_PROPERTY_ID)

    if redis:
        await redis.setex(_REDIS_KEY_RT, _TTL_RT, json.dumps(data))

    return data


@router.get("/summary")
async def analytics_summary(
    _: Annotated[User, Depends(get_current_admin_user)],
) -> dict:
    """Résumé du jour : sessions, utilisateurs, pages vues, taux de rebond, top pages."""
    settings = get_settings()
    redis = await _redis()

    if redis:
        cached = await redis.get(_REDIS_KEY_SUM)
        if cached:
            return json.loads(cached)

    data = await get_today_summary(settings.GOOGLE_SA_JSON, settings.GA4_PROPERTY_ID)

    if redis:
        await redis.setex(_REDIS_KEY_SUM, _TTL_SUM, json.dumps(data))

    return data


@router.get("/connections")
async def analytics_connections(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[User, Depends(get_current_admin_user)],
    days: int = Query(30, ge=1, le=90),
) -> list:
    """Points de connexion géolocalisés — même données que le globe."""
    return await ConnectionLogRepository(session).get_geo_points(days=days)
