"""
Repository pour l'entité User.
Fournit les opérations CRUD + recherche + pagination + filtrage par rôle.

Chiffrement PII (Loi 2024/017 Cameroun) :
  Les champs nominatifs sont chiffrés en AES-256-GCM avant tout stockage et
  déchiffrés après lecture via EncryptedModelMixin. Les lookups email/téléphone
  utilisent les colonnes HMAC (opaque pour l'hébergeur étranger).
"""

import math
from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value
from sqlmodel import select

from src.core.entities.servant_parent import ServantParent
from src.core.entities.user import User, UserRole
from src.core.interfaces.repository import IRepository
from src.infrastructure.config.settings import get_settings
from src.infrastructure.security.encrypted_model_mixin import EncryptedModelMixin
from src.infrastructure.security.field_encryption import get_encryptor

_PII_FIELDS = ("first_name", "last_name", "email", "phone_number", "oauth_subject")
_PII_DATE_FIELDS = ("birth_date", "baptism_date")


def default_profile_photo_url() -> str:
    """Photo de profil par défaut (`static/images/profil.jpeg`, identique à
    `servantassist-web/public/profil.jpeg`) — appliquée à tout utilisateur
    n'ayant pas encore uploadé sa propre photo (`POST /users/me/photo` écrase
    cette valeur dès l'upload)."""
    return f"{get_settings().APP_URL.rstrip('/')}/static/images/profil.jpeg"


class UserRepository(EncryptedModelMixin, IRepository[User]):
    ENCRYPTED_FIELDS = _PII_FIELDS
    HMAC_INDEX_MAP = {
        "email": "email_hmac",
        "phone_number": "phone_hmac",
        "oauth_subject": "oauth_subject_hmac",
    }

    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Override : les dates ISO nécessitent un traitement spécial ────

    def _encrypt_model(self, model: User) -> None:
        from datetime import datetime as dt

        enc = get_encryptor()

        # HMAC d'abord (sur le plaintext)
        for plain_field, hmac_col in self.HMAC_INDEX_MAP.items():
            val = getattr(model, plain_field, None)
            setattr(model, hmac_col, enc.hmac_index(val))

        # Chiffrement des champs texte
        for field in self.ENCRYPTED_FIELDS:
            val = getattr(model, field, None)
            if val is not None:
                setattr(model, field, enc.encrypt(str(val)))

        # Chiffrement des dates (stockées comme ISO-8601 string)
        for field in _PII_DATE_FIELDS:
            val = getattr(model, field, None)
            if val is not None and not isinstance(val, str):
                setattr(model, field, enc.encrypt(val.isoformat()))

    def _decrypt_model(self, model: User) -> None:
        from datetime import datetime as dt

        enc = get_encryptor()

        for field in self.ENCRYPTED_FIELDS:
            val = getattr(model, field, None)
            if val:
                try:
                    set_committed_value(model, field, enc.decrypt(val))
                except (ValueError, Exception):
                    pass

        for field in _PII_DATE_FIELDS:
            val = getattr(model, field, None)
            if val and isinstance(val, str):
                try:
                    set_committed_value(model, field, dt.fromisoformat(enc.decrypt(val)))
                except (ValueError, Exception):
                    # Repli : la valeur est peut-être une date ISO en clair
                    # (donnée antérieure au chiffrement PII, cf. commentaire
                    # équivalent dans EncryptedModelMixin). Si même ça échoue,
                    # c'est un blob chiffré indéchiffrable (clé tournée,
                    # donnée orpheline) — on ne le laisse JAMAIS remonter tel
                    # quel : Pydantic validerait ce champ comme une date et
                    # ferait planter toute la réponse (y compris une liste
                    # paginée entière à cause d'un seul enregistrement).
                    try:
                        set_committed_value(model, field, dt.fromisoformat(val))
                    except (ValueError, Exception):
                        set_committed_value(model, field, None)

    # ── Lecture ────────────────────────────────────────────────────────

    async def _load_parent_ids(self, user: User) -> None:
        """Populate transient parent_ids on a SERVANT user from the junction table."""
        result = await self.session.exec(select(ServantParent.parent_id).where(ServantParent.servant_id == user.id))
        object.__setattr__(user, "parent_ids", list(result.all()))

    async def get(self, id: UUID) -> Optional[User]:
        result = await self.session.exec(select(User).where(User.id == id))
        user = result.first()
        if user:
            self._decrypt_model(user)
            if user.role == UserRole.SERVANT:
                await self._load_parent_ids(user)
        return user

    async def get_by_email(self, email: Optional[str]) -> Optional[User]:
        # Défense en profondeur : email est optionnel pour SERVANT/PARENT.
        # hmac_index(None) retourne None, et `Column == None` se compile en
        # `IS NULL` côté SQL — sans cette garde, un email vide/None
        # retournerait un utilisateur ARBITRAIRE parmi tous les comptes sans
        # email, pas "aucun utilisateur trouvé".
        if not email:
            return None
        email_hmac = get_encryptor().hmac_index(email)
        result = await self.session.exec(select(User).where(User.email_hmac == email_hmac))
        user = result.first()
        if user:
            self._decrypt_model(user)
        return user

    async def get_by_phone(self, phone_number: str) -> Optional[User]:
        phone_hmac = get_encryptor().hmac_index(phone_number)
        result = await self.session.exec(select(User).where(User.phone_hmac == phone_hmac))
        user = result.first()
        if user:
            self._decrypt_model(user)
        return user

    async def get_by_oauth_subject(self, provider: str, subject: str) -> Optional[User]:
        subject_hmac = get_encryptor().hmac_index(subject)
        result = await self.session.exec(
            select(User).where(
                User.oauth_provider == provider,
                User.oauth_subject_hmac == subject_hmac,
            )
        )
        user = result.first()
        if user:
            self._decrypt_model(user)
        return user

    async def list(self) -> List[User]:
        result = await self.session.exec(select(User))
        users = list(result.all())
        self._decrypt_list(users)
        return users

    async def list_paginated(
        self,
        *,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        exclude_role: Optional[UserRole] = None,
    ) -> Tuple[List[User], int]:
        """
        Liste paginée avec filtres. La recherche textuelle est effectuée
        en mémoire après déchiffrement (correct pour un groupe paroissial).
        """
        stmt = select(User)
        if role is not None:
            stmt = stmt.where(User.role == role)
        if exclude_role is not None:
            stmt = stmt.where(User.role != exclude_role)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)

        result = await self.session.exec(stmt)
        all_users = list(result.all())
        self._decrypt_list(all_users)

        if search:
            term = search.lower()
            all_users = [
                u
                for u in all_users
                if term in (u.first_name or "").lower()
                or term in (u.last_name or "").lower()
                or term in (u.email or "").lower()
            ]

        total = len(all_users)
        all_users.sort(key=lambda u: u.created_at, reverse=True)
        offset = (page - 1) * page_size
        return all_users[offset : offset + page_size], total

    async def count_by_role(self, role: UserRole) -> int:
        result = await self.session.exec(select(func.count()).where(User.role == role))
        return result.one()

    # ── Écriture ──────────────────────────────────────────────────────

    async def create(self, user: User) -> User:
        if not user.profile_photo_url:
            user.profile_photo_url = default_profile_photo_url()
        self._encrypt_model(user)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        self._decrypt_model(user)
        self.session.expunge(user)
        if user.role == UserRole.SERVANT:
            await self._load_parent_ids(user)
        return user

    async def update(self, id: UUID, entity: User) -> User:
        self._encrypt_model(entity)
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        self._decrypt_model(entity)
        self.session.expunge(entity)
        if entity.role == UserRole.SERVANT:
            await self._load_parent_ids(entity)
        return entity

    async def delete(self, id: UUID) -> bool:
        result = await self.session.exec(select(User).where(User.id == id))
        user = result.first()
        if user:
            await self.session.delete(user)
            await self.session.commit()
            return True
        return False

    async def email_exists(self, email: Optional[str], exclude_id: Optional[UUID] = None) -> bool:
        # Même garde que get_by_email() : email est optionnel désormais.
        if not email:
            return False
        email_hmac = get_encryptor().hmac_index(email)
        stmt = select(User).where(User.email_hmac == email_hmac)
        if exclude_id:
            stmt = stmt.where(User.id != exclude_id)
        result = await self.session.exec(stmt)
        return result.first() is not None

    async def phone_exists(self, phone_number: str, exclude_id: Optional[UUID] = None) -> bool:
        phone_hmac = get_encryptor().hmac_index(phone_number)
        stmt = select(User).where(User.phone_hmac == phone_hmac)
        if exclude_id:
            stmt = stmt.where(User.id != exclude_id)
        result = await self.session.exec(stmt)
        return result.first() is not None

    async def get_parents_of(self, servant_id: UUID) -> List[User]:
        """Retourne tous les parents liés à ce servant (via junction table)."""
        result = await self.session.exec(
            select(User)
            .join(ServantParent, User.id == ServantParent.parent_id)
            .where(ServantParent.servant_id == servant_id)
        )
        parents = list(result.all())
        self._decrypt_list(parents)
        return parents

    async def get_children_of(self, parent_id: UUID) -> List[User]:
        """Retourne tous les servants liés à ce parent (via junction table)."""
        result = await self.session.exec(
            select(User)
            .join(ServantParent, User.id == ServantParent.servant_id)
            .where(ServantParent.parent_id == parent_id)
        )
        users = list(result.all())
        self._decrypt_list(users)
        return users

    async def add_parent_link(self, servant_id: UUID, parent_id: UUID) -> None:
        """Lie un servant à un parent. Max 3 parents par servant."""
        existing = await self.get_parents_of(servant_id)
        if len(existing) >= 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un servant ne peut avoir plus de 3 parents liés.",
            )
        if any(p.id == parent_id for p in existing):
            return  # idempotent
        self.session.add(ServantParent(servant_id=servant_id, parent_id=parent_id))
        await self.session.commit()

    async def remove_parent_link(self, servant_id: UUID, parent_id: UUID) -> None:
        """Supprime le lien entre un servant et un parent."""
        result = await self.session.exec(
            select(ServantParent).where(
                ServantParent.servant_id == servant_id,
                ServantParent.parent_id == parent_id,
            )
        )
        link = result.first()
        if link:
            await self.session.delete(link)
            await self.session.commit()
