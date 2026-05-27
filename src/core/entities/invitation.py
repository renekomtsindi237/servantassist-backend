"""
Invitation codes for controlled user creation
Prevents unauthorized role assignment (especially for PARENT and AUMÔNIER)
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from src.core.utils import utc_now


class InvitationStatus(str, Enum):
    """Status of invitation"""

    PENDING = "PENDING"  # Not yet used
    ACCEPTED = "ACCEPTED"  # Used to register
    REVOKED = "REVOKED"  # Cancelled by admin


class InvitationCode(SQLModel, table=True):
    """
    Invitation codes for PARENT and AUMÔNIER role creation
    - PARENT: Admin generates code, Parent uses code to register
    - AUMÔNIER: Admin creates directly (no code needed)
    """

    __tablename__ = "invitation_codes"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    # Unique invitation code (e.g., "INV-ABC123XYZ")
    code: str = Field(unique=True, index=True)
    # Role that this invitation allows (PARENT, AUMÔNIER)
    role: str = Field(default="PARENT")

    # Who can use this code
    email: Optional[str] = Field(default=None)  # Email if pre-assigned (chiffré)
    phone_number: Optional[str] = Field(default=None)  # WhatsApp (chiffré)

    # Index HMAC pour lookups sans déchiffrement (Loi 2024/017 Art. 22)
    email_hmac: Optional[str] = Field(default=None, index=True)
    phone_hmac: Optional[str] = Field(default=None, index=True)

    # Status tracking
    status: InvitationStatus = Field(default=InvitationStatus.PENDING)

    # Audit trail
    # Admin who created this invitation
    created_by: UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now)
    # No automatic expiration - admin controls lifespan via revocation

    # Usage tracking
    used_by: Optional[UUID] = Field(
    default=None,
     foreign_key="users.id")  # Who accepted this invitation
    used_at: Optional[datetime] = Field(default=None)

    # Metadata
    parent_name: Optional[str] = Field(default=None)  # Nom du parent destinataire
    # "Invitation for parents group 5A"
    notes: Optional[str] = Field(default=None)
    # Whether code was sent via WhatsApp
    whatsapp_sent: bool = Field(default=False)
    # Whether invitation code email was sent
    email_sent: bool = Field(default=False)

    class Config:
        from_attributes = True
