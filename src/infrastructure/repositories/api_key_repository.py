"""Repository pour les API Keys."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.core.entities.api_key import ApiKey
from src.core.utils import utc_now


class ApiKeyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, api_key: ApiKey) -> ApiKey:
        self.session.add(api_key)
        await self.session.commit()
        await self.session.refresh(api_key)
        return api_key

    async def get_by_id(self, key_id: UUID) -> Optional[ApiKey]:
        result = await self.session.exec(select(ApiKey).where(ApiKey.id == key_id))
        return result.first()

    async def get_by_user(self, user_id: UUID) -> List[ApiKey]:
        result = await self.session.exec(
            select(ApiKey).where(ApiKey.user_id == user_id).order_by(ApiKey.created_at.desc())
        )
        return list(result.all())

    async def list_all(self, limit: int = 50, offset: int = 0) -> List[ApiKey]:
        result = await self.session.exec(select(ApiKey).order_by(ApiKey.created_at.desc()).offset(offset).limit(limit))
        return list(result.all())

    async def revoke(self, key_id: UUID) -> Optional[ApiKey]:
        key = await self.get_by_id(key_id)
        if not key:
            return None
        key.is_active = False
        self.session.add(key)
        await self.session.commit()
        await self.session.refresh(key)
        return key

    async def delete(self, key_id: UUID) -> bool:
        key = await self.get_by_id(key_id)
        if not key:
            return False
        await self.session.delete(key)
        await self.session.commit()
        return True

    async def touch(self, key_id: UUID) -> None:
        """Met à jour last_used_at."""
        key = await self.get_by_id(key_id)
        if key:
            key.last_used_at = utc_now()
            self.session.add(key)
            await self.session.commit()
