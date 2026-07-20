from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy import String as SAString
from sqlalchemy import types
from sqlmodel import Field, SQLModel

from src.core.utils import utc_now


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    SERVANT = "SERVANT"
    PARENT = "PARENT"
    AUMÔNIER = "AUMÔNIER"

    @classmethod
    def _missing_(cls, value: object) -> "UserRole | None":
        """Accept ASCII variant 'AUMONIER' (without accent) as an alias."""
        if isinstance(value, str):
            normalized = value.upper().replace("Ô", "O").replace("ô", "o")
            if normalized == "AUMONIER":
                return cls.AUMÔNIER
        return None


class _UserRoleType(types.TypeDecorator):
    """VARCHAR(20) column that transparently converts to/from UserRole enum.

    Needed because asyncpg binary protocol cannot implicitly cast text OID to
    the PostgreSQL userrole enum OID. Storing as VARCHAR avoids the mismatch
    while this decorator ensures SQLAlchemy always surfaces a UserRole value.
    """

    impl = SAString(20)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if isinstance(value, UserRole):
            return value.value
        return value  # already a plain string or None

    def process_result_value(self, value, dialect):
        if value is not None:
            try:
                return UserRole(value)
            except ValueError:
                return UserRole._missing_(value)
        return value


class UserBase(SQLModel):
    # Optionnel pour SERVANT/PARENT (identifiant de connexion = téléphone) —
    # jamais généré artificiellement : NULL si non fourni. L'identité du JWT
    # repose sur User.id, pas sur l'email (voir AuthService.create_tokens).
    email: Optional[str] = Field(default=None, unique=True, index=True)
    first_name: str
    last_name: str
    role: UserRole = Field(
        default=UserRole.SERVANT,
        sa_column=Column(_UserRoleType(), nullable=False, server_default="SERVANT"),
    )
    is_active: bool = Field(default=True)
    phone_number: Optional[str] = Field(default=None, index=True)  # Indexed for PARENT/SERVANT login
    profile_photo_url: Optional[str] = Field(default=None)  # URL de la photo de profil
    birth_date: Optional[datetime] = Field(
        default=None,
        sa_column=Column(SAString, nullable=True),
    )  # Stored as encrypted string; decrypted back to datetime by UserRepository
    baptism_date: Optional[datetime] = Field(
        default=None,
        sa_column=Column(SAString, nullable=True),
    )  # Stored as encrypted string; decrypted back to datetime by UserRepository


class User(UserBase, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    created_by: Optional[UUID] = Field(default=None, foreign_key="users.id")  # Admin who created this user
    invited_by: Optional[UUID] = Field(default=None, foreign_key="users.id")  # For PARENT: who sent invitation

    # Index HMAC pour les lookups sans déchiffrement (Loi 2024/017 Art. 22)
    # Valeur = HMAC-SHA256(normalize(plaintext)) — opaque pour l'hébergeur.
    email_hmac: Optional[str] = Field(default=None, index=True)
    phone_hmac: Optional[str] = Field(default=None, index=True)

    # Acceptation des Conditions Générales d'Utilisation (tracé pour conformité)
    terms_accepted_at: Optional[datetime] = Field(default=None)

    # Consentement explicite au traitement des données personnelles (Loi 2024/017 Art. 9)
    data_consent_at: Optional[datetime] = Field(default=None)

    # Connexion via fournisseur OAuth (Google) — connexion uniquement,
    # ne remplace pas hashed_password. oauth_subject est chiffré comme les
    # autres champs PII (voir UserRepository.ENCRYPTED_FIELDS) ; oauth_subject_hmac
    # sert de clé de recherche (Loi 2024/017 Art. 22).
    oauth_provider: Optional[str] = Field(default=None, sa_column=Column(SAString(16), nullable=True))
    oauth_subject: Optional[str] = Field(default=None)
    oauth_subject_hmac: Optional[str] = Field(default=None, index=True)
