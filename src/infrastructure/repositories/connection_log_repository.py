from datetime import timedelta
from typing import List
from uuid import UUID

from sqlalchemy import func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.core.entities.connection_log import ConnectionLog
from src.core.utils import utc_now


class ConnectionLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, log: ConnectionLog) -> ConnectionLog:
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log

    async def get_geo_points(self, days: int = 30) -> List[dict]:
        """Retourne les points géolocalisés agrégés par ville pour les N derniers jours."""
        since = utc_now() - timedelta(days=days)
        stmt = (
            select(
                ConnectionLog.country,
                ConnectionLog.country_code,
                ConnectionLog.city,
                ConnectionLog.lat,
                ConnectionLog.lng,
                func.count(ConnectionLog.id).label("count"),
                func.max(ConnectionLog.logged_at).label("last_seen"),
            )
            .where(
                ConnectionLog.logged_at >= since,
                ConnectionLog.lat.is_not(None),
                ConnectionLog.lng.is_not(None),
            )
            .group_by(
                ConnectionLog.country,
                ConnectionLog.country_code,
                ConnectionLog.city,
                ConnectionLog.lat,
                ConnectionLog.lng,
            )
            .order_by(text("count DESC"))
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "country": r.country,
                "country_code": r.country_code,
                "city": r.city,
                "lat": r.lat,
                "lng": r.lng,
                "count": r.count,
                "last_seen": r.last_seen.isoformat() if r.last_seen else None,
            }
            for r in rows
        ]
