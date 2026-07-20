from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from src.core.utils import utc_now


class PhoneVerificationCode(SQLModel, table=True):
    """Code OTP 6 chiffres pour vérifier un numéro de téléphone à l'inscription
    (aucun compte n'existe encore à ce stade — pas de FK vers users)."""

    __tablename__ = "phone_verification_codes"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    phone_hmac: str = Field(index=True)  # pas le numéro en clair — cf. UserRepository.HMAC_INDEX_MAP
    code: str  # 6 chiffres en clair (expire rapidement)
    expires_at: datetime
    used: bool = Field(default=False)
    verified_at: Optional[datetime] = Field(default=None)
    verification_token: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=utc_now)

    class Config:
        from_attributes = True
