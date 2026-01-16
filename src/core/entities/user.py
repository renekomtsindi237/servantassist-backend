"""
User Entity - Core Domain Model
Clean Architecture: Domain Layer
"""
from datetime import datetime
from typing import Optional, List
from enum import Enum


class UserRole(str, Enum):
    """User roles enumeration"""
    SUPER_ADMIN = "SUPER_ADMIN"
    AUMONIER = "AUMONIER"
    RESPONSABLE_DELEGUE = "RESPONSABLE_DELEGUE"
    DELEGUE_ADJOINT = "DELEGUE_ADJOINT"
    SECRETAIRE_GENERAL = "SECRETAIRE_GENERAL"
    SECRETAIRE_ADJOINT = "SECRETAIRE_ADJOINT"
    CENSEUR = "CENSEUR"
    CENSEUR_ADJOINT = "CENSEUR_ADJOINT"
    ECONOME = "ECONOME"
    COMMISSAIRE_AUX_COMPTES = "COMMISSAIRE_AUX_COMPTES"
    RESPONSABLE_LITURGIE_SPIRITUALITE = "RESPONSABLE_LITURGIE_SPIRITUALITE"
    INTENDANT = "INTENDANT"
    RESPONSABLE_SPORTS = "RESPONSABLE_SPORTS"
    CEREMONIARE = "CEREMONIARE"
    PARENT = "PARENT"
    SERVANT = "SERVANT"


class Gender(str, Enum):
    """Gender enumeration"""
    MALE = "MALE"
    FEMALE = "FEMALE"


class User:
    """
    User Entity - Core domain model
    Represents a user in the system (Servant, Parent, Admin, etc.)
    """
    
    def __init__(
        self,
        id: str,
        email: str,
        phone_number1: str,
        first_name: str,
        last_name: str,
        role: UserRole,
        hashed_password: str,
        phone_number2: Optional[str] = None,
        date_of_birth: Optional[datetime] = None,
        gender: Optional[Gender] = None,
        address: Optional[str] = None,
        profile_picture: Optional[str] = None,
        is_active: bool = False,
        is_email_verified: bool = False,
        is_phone_verified: bool = False,
        parent_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        last_login_at: Optional[datetime] = None,
    ):
        self.id = id
        self.email = email
        self.phone_number1 = phone_number1
        self.phone_number2 = phone_number2
        self.first_name = first_name
        self.last_name = last_name
        self.date_of_birth = date_of_birth
        self.gender = gender
        self.address = address
        self.profile_picture = profile_picture
        self.role = role
        self.hashed_password = hashed_password
        self.is_active = is_active
        self.is_email_verified = is_email_verified
        self.is_phone_verified = is_phone_verified
        self.parent_id = parent_id
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.last_login_at = last_login_at
    
    @property
    def full_name(self) -> str:
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin privileges"""
        admin_roles = [
            UserRole.SUPER_ADMIN,
            UserRole.AUMONIER,
            UserRole.RESPONSABLE_DELEGUE,
            UserRole.SECRETAIRE_GENERAL,
        ]
        return self.role in admin_roles
    
    @property
    def is_servant(self) -> bool:
        """Check if user is a servant"""
        return self.role == UserRole.SERVANT
    
    @property
    def is_parent(self) -> bool:
        """Check if user is a parent"""
        return self.role == UserRole.PARENT
    
    def can_manage_users(self) -> bool:
        """Check if user can manage other users"""
        return self.role in [
            UserRole.SUPER_ADMIN,
            UserRole.AUMONIER,
            UserRole.SECRETAIRE_GENERAL,
        ]
    
    def can_manage_activities(self) -> bool:
        """Check if user can manage activities"""
        return self.role in [
            UserRole.SUPER_ADMIN,
            UserRole.AUMONIER,
            UserRole.RESPONSABLE_DELEGUE,
            UserRole.DELEGUE_ADJOINT,
        ]
    
    def can_manage_finances(self) -> bool:
        """Check if user can manage finances"""
        return self.role in [
            UserRole.SUPER_ADMIN,
            UserRole.ECONOME,
            UserRole.COMMISSAIRE_AUX_COMPTES,
        ]
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login_at = datetime.utcnow()
    
    def activate(self):
        """Activate user account"""
        self.is_active = True
        self.updated_at = datetime.utcnow()
    
    def deactivate(self):
        """Deactivate user account"""
        self.is_active = False
        self.updated_at = datetime.utcnow()
    
    def verify_email(self):
        """Mark email as verified"""
        self.is_email_verified = True
        self.updated_at = datetime.utcnow()
    
    def verify_phone(self):
        """Mark phone as verified"""
        self.is_phone_verified = True
        self.updated_at = datetime.utcnow()
    
    def update_profile_picture(self, url: str):
        """Update profile picture URL"""
        self.profile_picture = url
        self.updated_at = datetime.utcnow()
    
    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"
