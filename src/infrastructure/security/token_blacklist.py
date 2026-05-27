"""
Blacklist de tokens JWT par JTI.

Permet de révoquer un token avant son expiration naturelle (logout, rotation).
Backend Redis avec fallback in-memory.
"""
import logging
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# ── In-memory fallback ─────────────────────────────────────────────────────


class _InMemoryBlacklist:
    """Blacklist en mémoire : jti → expiry timestamp."""

    def __init__(self) -> None:
        self._store: Dict[str, float] = {}

    def add(self, jti: str, expires_at: float) -> None:
        self._store[jti] = expires_at

    def is_blacklisted(self, jti: str) -> bool:
        exp = self._store.get(jti)
        if exp is None:
            return False
        if time.time() >= exp:
            del self._store[jti]
            return False
        return True

    def cleanup(self) -> None:
        now = time.time()
        expired = [k for k, v in self._store.items() if v <= now]
        for k in expired:
            del self._store[k]


# ── Redis backend ──────────────────────────────────────────────────────────


class _RedisBlacklist:
    _PREFIX = "jti_bl:"

    def __init__(self, redis_client) -> None:
        self._redis = redis_client

    async def add(self, jti: str, expires_at: float) -> None:
        ttl = max(1, int(expires_at - time.time()))
        await self._redis.setex(f"{self._PREFIX}{jti}", ttl, "1")

    async def is_blacklisted(self, jti: str) -> bool:
        val = await self._redis.get(f"{self._PREFIX}{jti}")
        return val is not None


# ── Façade ──────────────────────────────────────────────────────────────────


class TokenBlacklist:
    """
    Révocation de tokens JWT par JTI.
    Utilise Redis si disponible, sinon fallback in-memory.
    """

    def __init__(self) -> None:
        self._redis_backend: Optional[_RedisBlacklist] = None
        self._memory_backend = _InMemoryBlacklist()
        self._use_redis = False

    def configure_redis(self, redis_client) -> None:
        if redis_client:
            self._redis_backend = _RedisBlacklist(redis_client)
            self._use_redis = True
            logger.info("Token blacklist: backend Redis actif")
        else:
            logger.warning("Token blacklist: Redis non disponible, fallback in-memory")

    async def revoke(self, jti: str, expires_at: float) -> None:
        """Révoque un token en ajoutant son JTI à la blacklist."""
        if self._use_redis and self._redis_backend:
            await self._redis_backend.add(jti, expires_at)
        else:
            self._memory_backend.add(jti, expires_at)

    async def is_revoked(self, jti: str) -> bool:
        """Retourne True si le token est révoqué."""
        if self._use_redis and self._redis_backend:
            return await self._redis_backend.is_blacklisted(jti)
        return self._memory_backend.is_blacklisted(jti)

    def cleanup_memory(self) -> None:
        """Purge les entrées expirées du fallback in-memory."""
        self._memory_backend.cleanup()


# Singleton global
token_blacklist = TokenBlacklist()
