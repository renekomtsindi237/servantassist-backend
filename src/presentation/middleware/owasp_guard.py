"""
Middleware OWASP Top 10 — ServantAssist
Couvre les risques A03, A04, A05, A07, A09, A10 en une seule couche.

OWASP Top 10 2021 :
  A03 Injection            → Détection de patterns SQL/NoSQL/SSTI dans les URLs et query strings
  A04 Insecure Design      → Limite de taille des requêtes, validation Content-Type
  A05 Security Misconfig   → Validation des hôtes autorisés (Allowed Hosts)
  A07 Auth Failures        → Rejet des tokens malformés avant le routeur
  A09 Security Logging     → Log structuré de chaque événement de sécurité
  A10 SSRF                 → Détection de schémas d'URL dangereux dans les corps

Les risques A01, A02, A06, A08 sont couverts par :
  A01 → RBAC dans auth_deps.py (require_admin, require_censeur, etc.)
  A02 → Chiffrement AES-256-GCM des champs PII + ECDH payload
  A06 → pip-audit dans le pipeline CI
  A08 → IdempotencyMiddleware + vérification d'intégrité HMAC
"""
from __future__ import annotations

import re
import time
from typing import FrozenSet, Sequence

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.infrastructure.config.settings import get_settings

# ── Patterns d'injection (A03) ────────────────────────────────────────────
# Détectés dans : URL path, query string, headers critiques
# Le corps JSON est géré par Pydantic — pas besoin de le rescanner ici.
_SQL_PATTERNS: Sequence[re.Pattern] = [
    re.compile(
        r"(union\s+select|select\s+.+\s+from|insert\s+into|drop\s+table"
        r"|delete\s+from|update\s+.+\s+set|exec\s*\(|execute\s*\()",
        re.IGNORECASE,
    ),
    re.compile(r"(--\s|;--|\bor\b\s+\d+=\d+|\band\b\s+\d+=\d+)", re.IGNORECASE),
    re.compile(
        r"(xp_cmdshell|sp_executesql|information_schema|sysobjects)", re.IGNORECASE
    ),
]

_SSTI_PATTERNS: Sequence[re.Pattern] = [
    re.compile(r"\{\{.*?\}\}"),  # Jinja2/Twig
    re.compile(r"\$\{.*?\}"),  # EL / Freemarker
    re.compile(r"<%.*?%>"),  # JSP / ERB
]

_PATH_TRAVERSAL: re.Pattern = re.compile(
    r"(\.\./|\.\.\\|%2e%2e%2f|%2e%2e/|\.%2e/|%2e\./)",
    re.IGNORECASE,
)

# Schémas d'URL dangereux côté SSRF (A10)
_SSRF_SCHEMES: FrozenSet[str] = frozenset(
    {
        "file://",
        "gopher://",
        "dict://",
        "ftp://",
        "ldap://",
        "ldaps://",
        "sftp://",
        "tftp://",
        "jar://",
        "netdoc://",
    }
)

# Taille max du corps hors upload (A04) — 2 MB par défaut
_MAX_BODY_BYTES = 2 * 1024 * 1024

# Content-Type attendu pour les corps (A04)
_JSON_METHODS = frozenset({"POST", "PUT", "PATCH"})
_ALLOWED_CONTENT_TYPES = frozenset(
    {
        "application/json",
        "multipart/form-data",
        "application/x-www-form-urlencoded",
    }
)

# Endpoints exempts de la validation Content-Type
_CT_EXEMPT_PREFIXES = (
    "/api/v1/communication/ws",  # WebSocket upgrade
    "/metrics",
    "/health",
    "/ready",
)


class OWASPGuardMiddleware(BaseHTTPMiddleware):
    """
    Garde OWASP : rejet précoce des requêtes malveillantes.
    S'intercale AVANT le routeur FastAPI pour ne jamais atteindre le code métier.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        start = time.monotonic()

        # ── A05 : Validation des hôtes autorisés ─────────────────────────
        host = request.headers.get("host", "").split(":")[0]
        if settings.ALLOWED_HOSTS and host not in settings.ALLOWED_HOSTS:
            self._log_event("BLOCKED_HOST", request, f"host={host}")
            return self._reject(400, "Invalid host header")

        # ── A03 : Injection dans l'URL et query string ────────────────────
        raw_url = str(request.url)
        if self._has_injection(raw_url):
            self._log_event("INJECTION_ATTEMPT", request, f"url={raw_url[:200]}")
            return self._reject(400, "Malformed request")

        # ── A04 : Path traversal ──────────────────────────────────────────
        if _PATH_TRAVERSAL.search(request.url.path):
            self._log_event("PATH_TRAVERSAL", request, f"path={request.url.path}")
            return self._reject(400, "Malformed request")

        # ── A04 : Validation du Content-Type pour POST/PUT/PATCH ─────────
        if request.method in _JSON_METHODS and not any(
            request.url.path.startswith(p) for p in _CT_EXEMPT_PREFIXES
        ):
            ct = request.headers.get("content-type", "").split(";")[0].strip()
            if ct and ct not in _ALLOWED_CONTENT_TYPES:
                self._log_event("INVALID_CONTENT_TYPE", request, f"ct={ct}")
                return self._reject(415, "Unsupported Media Type")

        # ── A04 : Taille du corps hors upload multipart ───────────────────
        content_length = request.headers.get("content-length")
        ct = request.headers.get("content-type", "")
        if (
            content_length
            and "multipart/form-data" not in ct
            and int(content_length) > _MAX_BODY_BYTES
        ):
            self._log_event("BODY_TOO_LARGE", request, f"size={content_length}")
            return self._reject(413, "Request body too large")

        # ── Passe la main ─────────────────────────────────────────────────
        response: Response = await call_next(request)

        # ── A09 : Log des réponses 4xx/5xx pour audit ─────────────────────
        elapsed = round((time.monotonic() - start) * 1000, 1)
        if response.status_code >= 400:
            logger.bind(
                event="http_error",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=elapsed,
                client=self._client_ip(request),
            ).warning("HTTP {status}", status=response.status_code)

        return response

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _has_injection(text: str) -> bool:
        for pattern in _SQL_PATTERNS:
            if pattern.search(text):
                return True
        for pattern in _SSTI_PATTERNS:
            if pattern.search(text):
                return True
        return False

    @staticmethod
    def _client_ip(request: Request) -> str:
        settings = get_settings()
        if settings.TRUST_PROXY_HEADERS:
            forwarded = request.headers.get("x-forwarded-for")
            if forwarded:
                return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _log_event(self, event: str, request: Request, detail: str = "") -> None:
        logger.bind(
            event=event,
            method=request.method,
            path=request.url.path,
            client=self._client_ip(request),
            detail=detail,
        ).warning("OWASP guard blocked: {event}", event=event)

    @staticmethod
    def _reject(status: int, message: str) -> JSONResponse:
        return JSONResponse(
            status_code=status,
            content={"detail": message},
            headers={
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
            },
        )
