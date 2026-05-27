"""
Middleware de rate limiting avec support Redis et fallback in-memory.

Protege les endpoints sensibles contre le brute-force :
- /api/v1/auth/login      : 5 req/min par IP
- /api/v1/auth/login/phone : 5 req/min par IP
- /api/v1/auth/register   : 3 req/min par IP
- /api/v1/auth/forgot-password : 3 req/min par IP
- Tous les autres         : 60 req/min par IP

Backends :
- **Redis** : utilise en production pour le rate limiting distribue
- **In-memory** : fallback si Redis n'est pas disponible (dev/test)
"""
import logging
import time
from collections import defaultdict
from typing import Dict, Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.infrastructure.config.settings import get_settings
logger = logging.getLogger(__name__)


# Configuration : (max_requests, window_seconds)
_RATE_LIMIT_PREFIXES = (
    "/api/v1/auth/login",
    "/api/v1/auth/login/phone",
    "/api/v1/auth/register",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
)
_WINDOW_SECONDS = 60


def _get_client_ip(request: Request) -> str:
    settings = get_settings()
    if settings.TRUST_PROXY_HEADERS:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",", 1)[0].strip()
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        cf_ip = request.headers.get("cf-connecting-ip")
        if cf_ip:
            return cf_ip.strip()

    return request.client.host if request.client else "unknown"


# ═══════════════════════════════════════════════════════════════════════════
#  Backend In-Memory
# ═══════════════════════════════════════════════════════════════════════════


class _InMemoryTokenBucket:
    """Compteur par IP avec fenetre glissante (fallback in-memory)."""

    __slots__ = ("_store",)

    def __init__(self):
        self._store: Dict[str, list] = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int,
                   window: int) -> Tuple[bool, int]:
        """Retourne (autorise, requetes_restantes)."""
        now = time.monotonic()
        timestamps = self._store[key]

        # Purger les entrees hors fenetre
        self._store[key] = [t for t in timestamps if now - t < window]
        timestamps = self._store[key]

        remaining = max(0, max_requests - len(timestamps))
        if len(timestamps) >= max_requests:
            return False, 0

        timestamps.append(now)
        return True, remaining - 1

    def cleanup(self, max_age: int = 300):
        now = time.monotonic()
        keys_to_delete = [k for k, v in self._store.items()
                                                          if not v or now - v[-1] > max_age]
        for k in keys_to_delete:
            del self._store[k]


# ═══════════════════════════════════════════════════════════════════════════
#  Backend Redis
# ═══════════════════════════════════════════════════════════════════════════


class _RedisTokenBucket:
    """Rate limiter avec Redis comme backend (fenetre glissante avec sorted sets)."""

    _PREFIX = "rl:"

    def __init__(self, redis_client):
        self._redis = redis_client

    async def is_allowed(self, key: str, max_requests: int,
                         window: int) -> Tuple[bool, int]:
        """Verifie si la requete est autorisee via Redis sorted set."""
        import time as _time

        now = _time.time()
        redis_key = f"{self._PREFIX}{key}"

        pipe = self._redis.pipeline()
        # Supprimer les entrees expirees
        pipe.zremrangebyscore(redis_key, 0, now - window)
        # Compter les entrees restantes
        pipe.zcard(redis_key)
        # Ajouter l'entree actuelle
        pipe.zadd(redis_key, {str(now): now})
        # Definir l'expiration de la cle
        pipe.expire(redis_key, window)
        results = await pipe.execute()

        current_count = results[1]
        remaining = max(0, max_requests - current_count - 1)

        if current_count >= max_requests:
            return False, 0

        return True, remaining


# ═══════════════════════════════════════════════════════════════════════════
#  Facade
# ═══════════════════════════════════════════════════════════════════════════


class RateLimiter:
    """
    Rate limiter qui utilise Redis si disponible, sinon fallback in-memory.
    """

    def __init__(self):
        self._redis_backend: Optional[_RedisTokenBucket] = None
        self._memory_backend = _InMemoryTokenBucket()
        self._use_redis = False

    def configure_redis(self, redis_client) -> None:
        """Configure le backend Redis."""
        if redis_client:
            self._redis_backend = _RedisTokenBucket(redis_client)
            self._use_redis = True
            logger.info("Rate limiter: backend Redis active")
        else:
            logger.warning(
                "Rate limiter: Redis non disponible, fallback in-memory")

    async def is_allowed(self, key: str, max_requests: int,
                         window: int) -> Tuple[bool, int]:
        if self._use_redis and self._redis_backend:
            try:
                return await self._redis_backend.is_allowed(key, max_requests, window)
            except Exception:
                # Redis indisponible — bascule silencieusement sur in-memory
                self._use_redis = False
                logger.warning("Rate limiter: Redis inaccessible, bascule sur in-memory")
        return self._memory_backend.is_allowed(key, max_requests, window)


# Singleton global
rate_limiter = RateLimiter()


# ═══════════════════════════════════════════════════════════════════════════
#  Middleware
# ═══════════════════════════════════════════════════════════════════════════


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Applique le rate limiting par IP sur les endpoints sensibles."""

    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        # Identifier le client par IP
        client_ip = _get_client_ip(request)
        path = request.url.path

        # Determiner la limite applicable
        max_requests, window = settings.RATE_LIMIT_GLOBAL, _WINDOW_SECONDS
        matched_path = None
        for prefix in _RATE_LIMIT_PREFIXES:
            if path.startswith(prefix):
                max_requests, window = settings.RATE_LIMIT_AUTH, _WINDOW_SECONDS
                matched_path = prefix
                break

        bucket_key = f"{client_ip}:{matched_path or 'global'}"
        allowed, remaining = await rate_limiter.is_allowed(bucket_key, max_requests, window)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after_seconds": window,
                },
                headers={
                    "Retry-After": str(window),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)

        # Ajouter les headers de rate limit informatifs
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response
