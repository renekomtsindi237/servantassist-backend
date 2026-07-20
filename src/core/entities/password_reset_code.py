from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from src.core.utils import utc_now


class PasswordResetCode(SQLModel, table=True):
    """Code OTP 6 chiffres pour réinitialisation de mot de passe via mobile.

    Clé sur user_id (pas email) : l'email est optionnel pour SERVANT/PARENT."""

    __tablename__ = "password_reset_codes"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(index=True)
    code: str  # 6 chiffres en clair (expire rapidement)
    expires_at: datetime
    used: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utc_now)

    class Config:
        from_attributes = True
