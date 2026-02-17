"""
User Repository Interface - Clean Architecture
Defines the contract for user data access
"""
from abc import ABC, abstractmethod
from typing import List, Optional

from src.core.entities.user import User, UserRole


class IUserRepository(ABC):
    """
    User Repository Interface
    Defines methods for user data access without implementation details
    """

    @abstractmethod
    async def create(self, user: User) -> User:
        """Create a new user"""
        pass

    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        pass

    @abstractmethod
    async def get_by_phone(self, phone_number: str) -> Optional[User]:
        """Get user by phone number"""
        pass

    @abstractmethod
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
    ) -> List[User]:
        """Get all users with optional filters"""
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        """Update user"""
        pass

    @abstractmethod
    async def delete(self, user_id: str) -> bool:
        """Delete user (soft delete)"""
        pass

    @abstractmethod
    async def exists_by_email(self, email: str) -> bool:
        """Check if user exists by email"""
        pass

    @abstractmethod
    async def exists_by_phone(self, phone_number: str) -> bool:
        """Check if user exists by phone number"""
        pass

    @abstractmethod
    async def count(self, role: Optional[UserRole] = None) -> int:
        """Count users with optional role filter"""
        pass

    @abstractmethod
    async def get_children(self, parent_id: str) -> List[User]:
        """Get all children of a parent"""
        pass
