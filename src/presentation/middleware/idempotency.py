"""
Middleware d'idempotency pour les requêtes POST.

Utilise le header `X-Idempotency-Key` (UUID v4 côté client) pour détecter
les doubles soumissions et retourner la réponse mise en cache.

TTL des clés : 24h (configurable).
Backend Redis avec fallback in-memory.

Fonctionnement :
1. Client envoie POST avec `X-Idempotency-Key: <uuid>`.
2. Premier appel → exécution normale, réponse mise en cache.
3. Appels suivants avec la même clé → réponse en cache retournée directement.

Endpoints protégés : tous les POST sauf auth/login, auth/register, auth/logout.
"""

import hashlib
import json
import logging
import time
from typing import Dict, Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

_TTL_SECONDS = 86400  # 24h
_MAX_BODY_SIZE = 1024 * 64  # 64 KB max pour le cache

# Endpoints exclus de l'idempotency (déjà idempotents ou non-critiques)
_EXCLUDED_PREFIXES = (
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/logout",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/api/v1/auth/refresh",
)


# ── In-memory fallback ─────────────────────────────────────────────────────


class _InMemoryStore:
    def __init__(self) -> None:
        self._store: Dict[str, Tuple[int, int, bytes, str]] = {}
        # key → (status_code, created_at, body_bytes, content_type)

    def get(self, key: str) -> Optional[Tuple[int, bytes, str]]:
        entry = self._store.get(key)
        if not entry:
            return None
        status_code, created_at, body, ct = entry
        if status_code == 0:  # in-progress sentinel — not a completed response
            return None
        if time.time() - created_at > _TTL_SECONDS:
            del self._store[key]
            return None
        return status_code, body, ct

    def set(self, key: str, status_code: int, body: bytes, content_type: str) -> None:
        self._store[key] = (status_code, int(time.time()), body, content_type)

    def mark_in_progress(self, key: str) -> None:
        self._store[key] = (0, int(time.time()), b"", "")

    def is_in_progress(self, key: str) -> bool:
        entry = self._store.get(key)
        return bool(entry and entry[0] == 0)

    def cleanup(self) -> None:
        now = time.time()
        expired = [k for k, v in self._store.items() if now - v[1] > _TTL_SECONDS]
        for k in expired:
            del self._store[k]


_memory_store = _InMemoryStore()


# ── Middleware ─────────────────────────────────────────────────────────────


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Détecte les doubles soumissions POST via X-Idempotency-Key."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Appliquer uniquement aux POST
        if request.method != "POST":
            return await call_next(request)

        # Exclure les endpoints non-critiques
        path = request.url.path
        if any(path.startswith(p) for p in _EXCLUDED_PREFIXES):
            return await call_next(request)

        idempotency_key = request.headers.get("X-Idempotency-Key", "").strip()
        if not idempotency_key:
            return await call_next(request)

        # Clé composite : endpoint + idempotency_key (évite collisions cross-endpoint)
        composite = hashlib.sha256(f"{path}:{idempotency_key}".encode()).hexdigest()

        # Vérifier le cache
        cached = _memory_store.get(composite)
        if cached:
            status_code, body, content_type = cached
            logger.debug("Idempotency cache hit: key=%s path=%s", idempotency_key, path)
            return Response(
                content=body,
                status_code=status_code,
                media_type=content_type,
                headers={"X-Idempotency-Replayed": "true"},
            )

        # Requête en cours (protection concurrence)
        if _memory_store.is_in_progress(composite):
            return JSONResponse(
                status_code=409,
                content={"detail": "Requête en cours de traitement. Réessayez dans un instant."},
            )

        _memory_store.mark_in_progress(composite)

        try:
            response = await call_next(request)
        except Exception:
            # Nettoyer en cas d'erreur pour permettre un nouvel essai
            _memory_store._store.pop(composite, None)
            raise

        # Ne mettre en cache que les réponses de succès (2xx)
        if 200 <= response.status_code < 300:
            body_chunks = []
            total = 0
            async for chunk in response.body_iterator:
                total += len(chunk)
                if total <= _MAX_BODY_SIZE:
                    body_chunks.append(chunk)
                else:
                    # Corps trop grand → ne pas mettre en cache
                    body_chunks = []
                    break

            if body_chunks:
                body = b"".join(body_chunks)
                ct = response.headers.get("content-type", "application/json")
                _memory_store.set(composite, response.status_code, body, ct)
                return Response(
                    content=body,
                    status_code=response.status_code,
                    media_type=ct,
                    headers=dict(response.headers),
                )
            else:
                _memory_store._store.pop(composite, None)
        else:
            _memory_store._store.pop(composite, None)

        return response
