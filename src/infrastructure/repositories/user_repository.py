"""
Repository pour l'entite User.
Fournit les operations CRUD + recherche + pagination + filtrage par role.
"""
import math
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, or_
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.entities.user import User, UserRole
from src.core.interfaces.repository import IRepository


class UserRepository(IRepository[User]):
    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Lecture ────────────────────────────────────────────────────────
    async def get(self, id: UUID) -> Optional[User]:
        statement = select(User).where(User.id == id)
        result = await self.session.exec(statement)
        return result.first()

    async def get_by_email(self, email: str) -> Optional[User]:
        statement = select(User).where(User.email == email)
        result = await self.session.exec(statement)
        return result.first()

    async def get_by_phone(self, phone_number: str) -> Optional[User]:
        """Recherche par numero de telephone (pour login PARENT/SERVANT)."""
        statement = select(User).where(User.phone_number == phone_number)
        result = await self.session.exec(statement)
        return result.first()

    # ── Listing avec pagination et filtres ────────────────────────────
    async def list(self) -> List[User]:
        statement = select(User)
        result = await self.session.exec(statement)
        return result.all()

    async def list_paginated(
        self,
        *,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[User], int]:
        """
        Liste paginee avec filtres optionnels.

        Retourne (users, total_count).
        """
        statement = select(User)

        # Filtrage par role
        if role is not None:
            statement = statement.where(User.role == role)

        # Filtrage par statut actif
        if is_active is not None:
            statement = statement.where(User.is_active == is_active)

        # Recherche textuelle (nom, prenom, email)
        if search:
            search_term = f"%{search.lower()}%"
            statement = statement.where(
                or_(
                    func.lower(User.first_name).like(search_term),
                    func.lower(User.last_name).like(search_term),
                    func.lower(User.email).like(search_term),
                )
            )

        # Compter le total avant pagination
        count_stmt = select(func.count()).select_from(statement.subquery())
        count_result = await self.session.exec(count_stmt)
        total = count_result.one()

        # Pagination
        offset = (page - 1) * page_size
        statement = statement.offset(offset).limit(page_size).order_by(User.created_at.desc())

        result = await self.session.exec(statement)
        users = result.all()

        return users, total

    async def count_by_role(self, role: UserRole) -> int:
        """Compte le nombre d'utilisateurs ayant un role donne."""
        statement = select(func.count()).where(User.role == role)
        result = await self.session.exec(statement)
        return result.one()

    # ── Ecriture ──────────────────────────────────────────────────────
    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update(self, id: UUID, entity: User) -> User:
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def delete(self, id: UUID) -> bool:
        statement = select(User).where(User.id == id)
        result = await self.session.exec(statement)
        user = result.first()
        if user:
            await self.session.delete(user)
            await self.session.commit()
            return True
        return False

    async def email_exists(self, email: str, exclude_id: Optional[UUID] = None) -> bool:
        """Verifie si un email est deja utilise (en excluant un utilisateur donne)."""
        statement = select(User).where(User.email == email)
        if exclude_id:
            statement = statement.where(User.id != exclude_id)
        result = await self.session.exec(statement)
        return result.first() is not None

    async def phone_exists(self, phone_number: str, exclude_id: Optional[UUID] = None) -> bool:
        """Verifie si un numero de telephone est deja utilise."""
        statement = select(User).where(User.phone_number == phone_number)
        if exclude_id:
            statement = statement.where(User.id != exclude_id)
        result = await self.session.exec(statement)
        return result.first() is not None
