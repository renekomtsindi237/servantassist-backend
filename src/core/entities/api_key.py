from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlmodel import JSON, Field, SQLModel

from src.core.utils import utc_now


class ApiKey(SQLModel, table=True):
    __tablename__ = "api_keys"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(max_length=100)
    key_hash: str = Field(max_length=128)
    user_id: UUID = Field(foreign_key="users.id")
    scopes: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    is_active: bool = Field(default=True)
    last_used_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
