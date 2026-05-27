"""
Protection contre les attaques par force brute.

Mecanisme :
- Apres N tentatives echouees sur un identifiant (email ou telephone),
  le compte est verrouille temporairement.
- Le verrouillage est progressif :
  * 5 echecs  -> verrouillage 1 min
  * 10 echecs -> verrouillage 5 min
  * 15 echecs -> verrouillage 15 min
  * 20+ echecs -> verrouillage 30 min
- Apres une connexion reussie, le compteur est reinitialise.

Backends :
- **Redis** : utilise en production pour un stockage distribue
- **In-memory** : fallback si Redis n'est pas disponible (dev/test)
"""
import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


# Seuils progressifs : (nombre_echecs, duree_verrouillage_secondes)
_LOCKOUT_TIERS: list[Tuple[int, int]] = [
    (5, 60),  # 5 echecs  -> 1 min
    (10, 300),  # 10 echecs -> 5 min
    (15, 900),  # 15 echecs -> 15 min
    (20, 1800),  # 20 echecs -> 30 min
]


def _get_lockout_duration(count: int) -> int:
    """Retourne la duree de verrouillage en secondes selon le nombre d'echecs."""
    duration = 0
    for threshold, lock_seconds in _LOCKOUT_TIERS:
        if count >= threshold:
            duration = lock_seconds
    return duration


def _get_remaining_attempts(count: int) -> int:
    """Retourne le nombre de tentatives restantes avant verrouillage."""
    for threshold, _ in _LOCKOUT_TIERS:
        if count < threshold:
            return threshold - count
    return 0


# ═══════════════════════════════════════════════════════════════════════════
#  Backend Redis
# ═══════════════════════════════════════════════════════════════════════════


class RedisBruteForceProtection:
    """Protection brute-force avec Redis comme backend."""

    # Prefix des cles Redis
    _PREFIX = "bf:"

    def __init__(self, redis_client):
        self._redis = redis_client

    def _key_count(self, identifier: str) -> str:
        return f"{self._PREFIX}{identifier}:count"

    def _key_locked(self, identifier: str) -> str:
        return f"{self._PREFIX}{identifier}:locked"

    async def check_locked(
        self, identifier: str) -> Tuple[bool, Optional[int]]:
        ttl = await self._redis.ttl(self._key_locked(identifier))
        if ttl and ttl > 0:
            return True, ttl
        return False, None

    async def record_failure(
        self, identifier: str) -> Tuple[bool, int, Optional[int]]:
        key = self._key_count(identifier)
        count = await self._redis.incr(key)
        # Expirer le compteur apres 1h d'inactivite
        await self._redis.expire(key, 3600)

        lockout_duration = _get_lockout_duration(count)
        if lockout_duration > 0:
            await self._redis.setex(
                self._key_locked(identifier),
                lockout_duration,
                "1",
            )
            return True, count, lockout_duration

        return False, count, None

    async def record_success(self, identifier: str) -> None:
        await self._redis.delete(
            self._key_count(identifier),
            self._key_locked(identifier),
        )

    async def get_remaining_attempts(self, identifier: str) -> int:
        key = self._key_count(identifier)
        count = await self._redis.get(key)
        count = int(count) if count else 0
        return _get_remaining_attempts(count)


# ═══════════════════════════════════════════════════════════════════════════
#  Backend In-Memory (fallback)
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class _LoginAttempt:
    """Suivi des tentatives de connexion pour un identifiant."""

    count: int = 0
    first_attempt: float = 0.0
    last_attempt: float = 0.0
    locked_until: float = 0.0


class InMemoryBruteForceProtection:
    """Gestionnaire de protection brute-force en memoire (fallback)."""

    def __init__(self):
        self._attempts: Dict[str, _LoginAttempt] = {}

    def check_locked(self, identifier: str) -> Tuple[bool, Optional[int]]:
        attempt = self._attempts.get(identifier)
        if not attempt:
            return False, None

        now = time.monotonic()
        if attempt.locked_until > now:
            remaining = int(attempt.locked_until - now) + 1
            return True, remaining

        return False, None

    def record_failure(
        self, identifier: str) -> Tuple[bool, int, Optional[int]]:
        now = time.monotonic()
        attempt = self._attempts.get(identifier)

        if not attempt:
            attempt = _LoginAttempt(
                count=1,
                first_attempt=now,
                last_attempt=now,
            )
            self._attempts[identifier] = attempt
        else:
            attempt.count += 1
            attempt.last_attempt = now

        lockout_duration = _get_lockout_duration(attempt.count)
        if lockout_duration > 0:
            attempt.locked_until = now + lockout_duration
            return True, attempt.count, lockout_duration

        return False, attempt.count, None

    def record_success(self, identifier: str) -> None:
        self._attempts.pop(identifier, None)

    def get_remaining_attempts(self, identifier: str) -> int:
        attempt = self._attempts.get(identifier)
        if not attempt:
            return _LOCKOUT_TIERS[0][0]
        return _get_remaining_attempts(attempt.count)

    def cleanup(self, max_age: int = 3600) -> None:
        now = time.monotonic()
        to_delete = [k for k, v in self._attempts.items() if now -
     v.last_attempt > max_age and v.locked_until < now]
        for k in to_delete:
            del self._attempts[k]


# ═══════════════════════════════════════════════════════════════════════════
#  Facade unifiee
# ═══════════════════════════════════════════════════════════════════════════


class BruteForceProtection:
    """
    Facade qui utilise Redis si disponible, sinon fallback in-memory.

    L'interface est async pour supporter les deux backends.
    """

    def __init__(self):
        self._redis_backend: Optional[RedisBruteForceProtection] = None
        self._memory_backend = InMemoryBruteForceProtection()
        self._use_redis = False

    def configure_redis(self, redis_client) -> None:
        """Configure le backend Redis. Appeler au demarrage de l'app si Redis est disponible."""
        if redis_client:
            self._redis_backend = RedisBruteForceProtection(redis_client)
            self._use_redis = True
            logger.info("Brute-force protection: backend Redis active")
        else:
            logger.warning(
                "Brute-force protection: Redis non disponible, fallback in-memory")

    async def check_locked(
        self, identifier: str) -> Tuple[bool, Optional[int]]:
        if self._use_redis and self._redis_backend:
            return await self._redis_backend.check_locked(identifier)
        return self._memory_backend.check_locked(identifier)

    async def record_failure(
        self, identifier: str) -> Tuple[bool, int, Optional[int]]:
        if self._use_redis and self._redis_backend:
            return await self._redis_backend.record_failure(identifier)
        return self._memory_backend.record_failure(identifier)

    async def record_success(self, identifier: str) -> None:
        if self._use_redis and self._redis_backend:
            await self._redis_backend.record_success(identifier)
        else:
            self._memory_backend.record_success(identifier)

    async def get_remaining_attempts(self, identifier: str) -> int:
        if self._use_redis and self._redis_backend:
            return await self._redis_backend.get_remaining_attempts(identifier)
        return self._memory_backend.get_remaining_attempts(identifier)


# Singleton global
brute_force_guard = BruteForceProtection()
