import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from src.core.entities.user import UserRole


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class TokenData(BaseModel):
    email: str
    role: UserRole


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserPhoneLogin(BaseModel):
    """Login for PARENT and SERVANT using phone number"""

    phone_number: str = Field(...,
     description="Phone number with country code (e.g., +237xxxxxxxxx)")
    password: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(
        ...,
        min_length=8,
        description="Minimum 8 characters, with uppercase, lowercase, and digit",
    )
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    role: UserRole = UserRole.SERVANT

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets minimum security requirements"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError(
                "Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError(
                "Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("phone_number")
    @classmethod
    def validate_phone_for_role(cls, v: str, info) -> Optional[str]:
        """Validate phone number is provided for PARENT and SERVANT roles"""
        role = info.data.get("role")
        if role in [UserRole.PARENT, UserRole.SERVANT]:
            if not v:
                raise ValueError(f"{role} users must provide a phone number")
            # Basic phone validation: should be in format like +237xxxxxxxxx
            if not re.match(r"^\+\d{1,3}\d{6,14}$", v):
                raise ValueError(
                    "Phone number must be in format: +237xxxxxxxxx")
        return v


class UserCreateWithInvite(BaseModel):
    """Extended schema for registration with invitation code support"""

    email: EmailStr
    password: str = Field(
        ...,
        min_length=8,
        description="Minimum 8 characters, with uppercase, lowercase, and digit",
    )
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    role: UserRole = UserRole.SERVANT
    invitation_code: Optional[str] = Field(
    default=None, description="Required for PARENT role")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets minimum security requirements"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError(
                "Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError(
                "Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("phone_number")
    @classmethod
    def validate_phone_for_role(cls, v: str, info) -> Optional[str]:
        """Validate phone number is provided for PARENT and SERVANT roles"""
        role = info.data.get("role")
        if role in [UserRole.PARENT, UserRole.SERVANT]:
            if not v:
                raise ValueError(f"{role} users must provide a phone number")
            if not re.match(r"^\+\d{1,3}\d{6,14}$", v):
                raise ValueError(
                    "Phone number must be in format: +237xxxxxxxxx")
        return v


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole
    is_active: bool
    phone_number: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class RequestResetCodeRequest(BaseModel):
    """Demande d'envoi d'un code OTP par email (flow mobile)."""
    email: EmailStr


class VerifyResetCodeRequest(BaseModel):
    """Vérification du code OTP reçu par email."""
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class VerifyResetCodeResponse(BaseModel):
    """Token JWT à utiliser pour POST /auth/reset-password."""
    reset_token: str
