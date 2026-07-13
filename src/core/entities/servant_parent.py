from datetime import datetime
from uuid import UUID

from sqlmodel import Field, SQLModel

from src.core.utils import utc_now


class ServantParent(SQLModel, table=True):
    __tablename__ = "servant_parents"

    servant_id: UUID = Field(foreign_key="users.id", primary_key=True)
    parent_id: UUID = Field(foreign_key="users.id", primary_key=True)
    created_at: datetime = Field(default_factory=utc_now)
