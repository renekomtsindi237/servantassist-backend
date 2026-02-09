"""
Middleware de logging des requetes HTTP.

Log chaque requete avec :
- Methode, chemin, statut, duree
- IP client
- User-Agent
- Marquage special pour les endpoints sensibles (audit trail)
"""
import time

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


# Endpoints qui declenchent un log d'audit de securite
_AUDIT_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/login/phone",
    "/api/v1/auth/register",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/api/v1/auth/refresh",
}
_ADMIN_PREFIX = "/api/v1/admin/"


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log structurel de chaque requete HTTP."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")[:100]
        path = request.url.path
        method = request.method

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start) * 1000
        status_code = response.status_code

        # Log standard
        log_data = {
            "method": method,
            "path": path,
            "status": status_code,
            "duration_ms": round(duration_ms, 1),
            "client_ip": client_ip,
            "user_agent": user_agent,
        }

        if status_code >= 500:
            logger.error("HTTP {status} | {method} {path} | {duration_ms}ms | {client_ip}", **log_data)
        elif status_code >= 400:
            logger.warning("HTTP {status} | {method} {path} | {duration_ms}ms | {client_ip}", **log_data)
        else:
            logger.info("HTTP {status} | {method} {path} | {duration_ms}ms", **log_data)

        # Audit log pour les endpoints sensibles
        if path in _AUDIT_PATHS or path.startswith(_ADMIN_PREFIX):
            audit_level = "warning" if status_code >= 400 else "info"
            getattr(logger, audit_level)(
                "AUDIT | {method} {path} | status={status} | ip={client_ip} | ua={user_agent}",
                **log_data,
            )

        return response

