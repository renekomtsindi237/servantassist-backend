"""
Middleware de headers de securite HTTP.

Ajoute les headers recommandes par OWASP sur chaque reponse :
- Strict-Transport-Security (HSTS)
- X-Content-Type-Options
- X-Frame-Options
- X-XSS-Protection
- Content-Security-Policy
- Referrer-Policy
- Permissions-Policy
- Cache-Control sur endpoints sensibles
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.infrastructure.config.settings import get_settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injecte les headers de securite sur toutes les reponses."""

    # Chemins sensibles qui ne doivent JAMAIS etre mis en cache
    _NO_CACHE_PATHS = ("/api/v1/auth/", "/api/v1/admin/")

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)
        settings = get_settings()

        # -- HSTS : force HTTPS (1 an, incluant sous-domaines) --------
        if settings.APP_ENV == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # -- Empeche le sniffing MIME ---------------------------------
        response.headers["X-Content-Type-Options"] = "nosniff"

        # -- Empeche l'embarquement dans un iframe --------------------
        response.headers["X-Frame-Options"] = "DENY"

        # -- Protection XSS legacy (navigateurs anciens) --------------
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # -- Content Security Policy ----------------------------------
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        # -- Politique de referrer ------------------------------------
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # -- Permissions Policy (desactive camera, micro, etc.) -------
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )

        # -- Cache-Control sur les endpoints sensibles ----------------
        path = request.url.path
        if any(path.startswith(p) for p in self._NO_CACHE_PATHS):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"

        # -- Masquer le serveur (ne pas reveler la techno) ------------
        response.headers.pop("server", None)
        response.headers["X-Powered-By"] = "ServantAssist"

        return response

