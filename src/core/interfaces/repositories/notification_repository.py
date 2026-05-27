from typing import Dict, List, Optional, Protocol, runtime_checkable
from uuid import UUID

from src.core.entities.notification import (
    Notification,
    NotificationChannel,
    NotificationPreference,
    NotificationStatus,
    NotificationType,
)


@runtime_checkable
class INotificationRepository(Protocol):
    async def create(self, notification: Notification) -> Notification: ...

    async def create_many(self, notifications: List[Notification]) -> List[Notification]: ...

    async def get_by_id(self, notification_id: UUID) -> Optional[Notification]: ...

    async def get_by_user(
        self,
        user_id: UUID,
        *,
        notification_type: Optional[NotificationType] = None,
        status: Optional[NotificationStatus] = None,
        channel: Optional[NotificationChannel] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Notification]: ...

    async def count_by_user(self, user_id: UUID, **kwargs) -> int: ...

    async def count_unread_by_user(self, user_id: UUID) -> int: ...

    async def mark_sent(self, notification_id: UUID) -> Optional[Notification]: ...

    async def mark_read(self, notification_id: UUID) -> Optional[Notification]: ...

    async def get_stats_by_user(self, user_id: UUID) -> Dict: ...


@runtime_checkable
class INotificationPreferenceRepository(Protocol):
    async def get_by_user(self, user_id: UUID) -> List[NotificationPreference]: ...

    async def get_by_user_and_type(
        self, user_id: UUID, notification_type: NotificationType
    ) -> Optional[NotificationPreference]: ...

    async def upsert(self, preference: NotificationPreference) -> NotificationPreference: ...
