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
            return UserRole(value)
        return value


class ServantPosition(str, Enum):
    DELEGUE = "DELEGUE"
    VICE_DELEGUE = "VICE_DELEGUE"
    CENSEUR = "CENSEUR"
    CENSEUR_ADJOINT = "CENSEUR_ADJOINT"
    SECRETAIRE_GENERAL = "SECRETAIRE_GENERAL"
    SECRETAIRE_GENERAL_ADJOINT = "SECRETAIRE_GENERAL_ADJOINT"
    ECONOME = "ECONOME"
    COMMISSAIRE_AUX_COMPTES = "COMMISSAIRE_AUX_COMPTES"
    INTENDANT = "INTENDANT"
    CHARGE_LITURGIE = "CHARGE_LITURGIE"
    CEREMONIARE = "CEREMONIARE"
    CHARGE_SPORTS_CULTURE = "CHARGE_SPORTS_CULTURE"
    CHARGE_CLASSEMENT = "CHARGE_CLASSEMENT"
    CONSEILLER = "CONSEILLER"
    SERVANT_AUTEL = "SERVANT_AUTEL"


class _ServantPositionType(types.TypeDecorator):
    """VARCHAR(64) column that transparently converts to/from ServantPosition enum.

    Same pattern as _UserRoleType: asyncpg cannot implicitly cast text OID to the
    PostgreSQL servantposition enum OID, causing DatatypeMismatchError on INSERT.
    Storing as VARCHAR avoids the mismatch while this decorator surfaces ServantPosition.
    """

    impl = SAString(64)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if isinstance(value, ServantPosition):
            return value.value
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            try:
                return ServantPosition(value)
            except ValueError:
                return value
        return value


class UserBase(SQLModel):
    email: str = Field(unique=True, index=True)
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
    position: Optional[ServantPosition] = Field(
        default=None,
        sa_column=Column(_ServantPositionType(), nullable=True),
    )  # Poste organisationnel (servants uniquement)


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
