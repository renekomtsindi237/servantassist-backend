from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from src.core.utils import utc_now


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    SERVANT = "SERVANT"
    PARENT = "PARENT"
    AUMÔNIER = "AUMÔNIER"


class UserBase(SQLModel):
    email: str = Field(unique=True, index=True)
    first_name: str
    last_name: str
    role: UserRole = Field(default=UserRole.SERVANT)
    is_active: bool = Field(default=True)
    phone_number: Optional[str] = Field(
        default=None, index=True
    )  # Indexed for PARENT/SERVANT login
    profile_photo_url: Optional[str] = Field(default=None)  # URL de la photo de profil
    birth_date: Optional[datetime] = Field(
        default=None
    )  # Pour les règles d'âge (Art 19, 26)
    baptism_date: Optional[datetime] = Field(
        default=None
    )  # Art 19 : être chrétien baptisé


class User(UserBase, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    created_by: Optional[UUID] = Field(
        default=None, foreign_key="users.id"
    )  # Admin who created this user
    invited_by: Optional[UUID] = Field(
        default=None, foreign_key="users.id"
    )  # For PARENT: who sent invitation
