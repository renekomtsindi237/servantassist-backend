"""
Utilitaires de securite : hachage de mots de passe et creation de JWT.

Chaque token contient un JTI (JWT Token ID) unique pour permettre
la revocation future via blacklist Redis.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Union

import jwt
import nh3
from passlib.context import CryptContext

from src.infrastructure.config.settings import get_settings

settings = get_settings()

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,  # Augmenter le cout de hachage (defaut: 12)
)


class SecurityUtils:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(
        subject: Union[str, Any],
        role: str,
        expires_delta: timedelta = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode: dict = {
            "exp": expire,
            "iat": now,
            "sub": str(subject),
            "role": role,
            "jti": uuid.uuid4().hex,  # ID unique pour revocation future
            "iss": settings.APP_NAME,
        }
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt

    @staticmethod
    def create_refresh_token(
        subject: Union[str, Any],
        role: str,
        expires_delta: timedelta = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

        to_encode: dict = {
            "exp": expire,
            "iat": now,
            "sub": str(subject),
            "type": "refresh",
            "role": role,
            "jti": uuid.uuid4().hex,
            "iss": settings.APP_NAME,
        }
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt

    @staticmethod
    def create_reset_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
        now = datetime.now(timezone.utc)
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=15)  # Short lived

        to_encode = {
            "exp": expire,
            "iat": now,
            "sub": str(subject),
            "type": "reset",
            "jti": uuid.uuid4().hex,
            "iss": settings.APP_NAME,
        }
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt

    @staticmethod
    def sanitize_html(content: str) -> str:
        """Nettoie le contenu HTML pour éviter les failles XSS."""
        if not content:
            return content
        # Strip all tags as per security test requirements
        return nh3.clean(content, tags=set())
