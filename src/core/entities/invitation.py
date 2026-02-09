"""
Invitation codes for controlled user creation
Prevents unauthorized role assignment (especially for PARENT and AUMÔNIER)
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class InvitationStatus(str, Enum):
    """Status of invitation"""
    PENDING = "PENDING"           # Not yet used
    ACCEPTED = "ACCEPTED"         # Used to register
    REVOKED = "REVOKED"           # Cancelled by admin


class InvitationCode(SQLModel, table=True):
    """
    Invitation codes for PARENT and AUMÔNIER role creation
    - PARENT: Admin generates code, Parent uses code to register
    - AUMÔNIER: Admin creates directly (no code needed)
    """
    __tablename__ = "invitation_codes"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    code: str = Field(unique=True, index=True)  # Unique invitation code (e.g., "INV-ABC123XYZ")
    role: str = Field(default="PARENT")  # Role that this invitation allows (PARENT, AUMÔNIER)
    
    # Who can use this code
    email: Optional[str] = Field(default=None)  # Email if pre-assigned
    phone_number: Optional[str] = Field(default=None)  # Phone number for WhatsApp delivery
    
    # Status tracking
    status: InvitationStatus = Field(default=InvitationStatus.PENDING)
    
    # Audit trail
    created_by: UUID = Field(foreign_key="users.id")  # Admin who created this invitation
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # No automatic expiration - admin controls lifespan via revocation
    
    # Usage tracking
    used_by: Optional[UUID] = Field(default=None, foreign_key="users.id")  # Who accepted this invitation
    used_at: Optional[datetime] = Field(default=None)
    
    # Metadata
    notes: Optional[str] = Field(default=None)  # "Invitation for parents group 5A"
    whatsapp_sent: bool = Field(default=False)  # Whether code was sent via WhatsApp

    class Config:
        from_attributes = True
