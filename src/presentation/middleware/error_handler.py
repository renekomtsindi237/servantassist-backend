"""
Middleware de gestion globale des erreurs.

- En PRODUCTION : ne fuit JAMAIS de stack trace ni de details internes.
- En DEVELOPMENT : retourne le message d'erreur complet pour le debug.
- Log toutes les erreurs 500 avec le contexte de la requete.
"""
import traceback
import uuid

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.infrastructure.config.settings import get_settings


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Attrape les exceptions non gerees et retourne une reponse securisee."""

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            settings = get_settings()
            error_id = uuid.uuid4().hex[:12]

            # Log complet pour le monitoring
            logger.error(
                "Unhandled exception | error_id={error_id} | method={method} | "
                "path={path} | client={client} | error={error}",
                error_id=error_id,
                method=request.method,
                path=request.url.path,
                client=request.client.host if request.client else "unknown",
                error=str(exc),
            )
            if settings.APP_DEBUG:
                logger.error(traceback.format_exc())

            # Reponse securisee
            if settings.APP_ENV == "production":
                return JSONResponse(
                    status_code=500,
                    content={
                        "detail": "An internal error occurred.",
                        "error_id": error_id,
                    },
                )
            else:
                return JSONResponse(
                    status_code=500,
                    content={
                        "detail": str(exc),
                        "error_id": error_id,
                        "type": type(exc).__name__,
                    },
                )

