from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from src.core.utils import utc_now


class ConnectionLog(SQLModel, table=True):
    __tablename__ = "connection_logs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: Optional[UUID] = Field(default=None, foreign_key="users.id")
    ip_address: str = Field(max_length=45)
    country: Optional[str] = Field(default=None, max_length=100)
    country_code: Optional[str] = Field(default=None, max_length=2)
    city: Optional[str] = Field(default=None, max_length=100)
    lat: Optional[float] = None
    lng: Optional[float] = None
    logged_at: datetime = Field(default_factory=utc_now)
