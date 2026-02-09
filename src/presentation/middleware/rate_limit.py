"""
Middleware de rate limiting en memoire (token bucket simplifie).

Protege les endpoints sensibles contre le brute-force :
- /api/v1/auth/login      : 5 req/min par IP
- /api/v1/auth/login/phone : 5 req/min par IP
- /api/v1/auth/register   : 3 req/min par IP
- /api/v1/auth/forgot-password : 3 req/min par IP
- Tous les autres         : 60 req/min par IP

En production, utiliser Redis pour le rate limiting distribue.
"""
import time
from collections import defaultdict
from typing import Dict, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


# Configuration : (max_requests, window_seconds)
_RATE_LIMITS: Dict[str, Tuple[int, int]] = {
    "/api/v1/auth/login": (5, 60),
    "/api/v1/auth/login/phone": (5, 60),
    "/api/v1/auth/register": (3, 60),
    "/api/v1/auth/forgot-password": (3, 60),
    "/api/v1/auth/reset-password": (3, 60),
}
_DEFAULT_LIMIT: Tuple[int, int] = (60, 60)  # 60 req/min


class _TokenBucket:
    """Compteur par IP avec fenetre glissante."""

    __slots__ = ("_store",)

    def __init__(self):
        # key = (ip, path_prefix) -> list of timestamps
        self._store: Dict[str, list] = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int, window: int) -> Tuple[bool, int]:
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
        """Nettoie les entrees obsoletes (appel periodique optionnel)."""
        now = time.monotonic()
        keys_to_delete = [
            k for k, v in self._store.items()
            if not v or now - v[-1] > max_age
        ]
        for k in keys_to_delete:
            del self._store[k]


_bucket = _TokenBucket()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Applique le rate limiting par IP sur les endpoints sensibles."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Identifier le client par IP
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        # Determiner la limite applicable
        max_requests, window = _DEFAULT_LIMIT
        matched_path = None
        for prefix, limits in _RATE_LIMITS.items():
            if path.startswith(prefix):
                max_requests, window = limits
                matched_path = prefix
                break

        bucket_key = f"{client_ip}:{matched_path or 'global'}"
        allowed, remaining = _bucket.is_allowed(bucket_key, max_requests, window)

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

