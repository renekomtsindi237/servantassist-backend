"""
Schemas for invitation code management
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.core.entities.invitation import InvitationStatus


class InvitationCodeCreate(BaseModel):
    """Request to create invitation code"""

    role: str = Field(default="PARENT", description="PARENT or AUMÔNIER")
    parent_name: Optional[str] = Field(default=None, description="Nom du parent destinataire")
    email: Optional[str] = Field(default=None, description="Optional: specific email allowed to use")
    phone_number: Optional[str] = Field(default=None, description="Optional: phone number for WhatsApp delivery")
    notes: Optional[str] = None


class InvitationCodeResponse(BaseModel):
    """Response for invitation code"""

    id: UUID
    code: str
    role: str
    parent_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    status: InvitationStatus
    created_at: datetime
    used_at: Optional[datetime] = None
    notes: Optional[str] = None
    whatsapp_sent: bool = False
    email_sent: bool = False

    class Config:
        from_attributes = True


class InvitationCodeListResponse(BaseModel):
    """List of invitation codes with usage stats"""

    id: UUID
    code: str
    role: str
    parent_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    status: InvitationStatus
    created_at: datetime
    used_by: Optional[UUID] = None
    used_at: Optional[datetime] = None
    notes: Optional[str] = None
    whatsapp_sent: bool = False
    email_sent: bool = False

    class Config:
        from_attributes = True


class SendInvitationEmailRequest(BaseModel):
    """Request to send invitation code via email"""

    email: str = Field(description="Email address to send the code to")
