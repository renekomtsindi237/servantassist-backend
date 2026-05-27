"""
Middleware de gestion globale des erreurs — filet de sécurité.

Rôle : attraper les exceptions qui auraient échappé aux handlers FastAPI
(ex: erreurs dans d'autres middlewares, erreurs de transport).

Les exceptions applicatives sont gérées en priorité par les handlers
enregistrés dans main.py via app.add_exception_handler().
Ce middleware est le dernier recours.

Comportement :
- Production  → jamais de stack trace ni de détail interne
- Dev/Staging → message d'erreur complet pour le debug
- Toujours loggé avec un error_id traçable
"""
from __future__ import annotations

import traceback
import uuid

from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.core.exceptions import ServantAssistException
from src.infrastructure.config.settings import get_settings


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Filet de sécurité final pour les exceptions non catchées par FastAPI."""

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            return await call_next(request)

        except ServantAssistException as exc:
            # Exception métier non catchée par les handlers FastAPI
            error_id = uuid.uuid4().hex[:12]
            logger.bind(
                event="middleware_domain_exception",
                exception_type=type(exc).__name__,
                path=request.url.path,
                error_id=error_id,
            ).error("Domain exception in middleware: {msg}", msg=exc.message)

            return JSONResponse(
                status_code=exc.http_status,
                content={"detail": exc.message, "error_id": error_id},
            )

        except SQLAlchemyError as exc:
            # Erreur DB hors contexte FastAPI (ex: middleware en amont)
            error_id = uuid.uuid4().hex[:12]
            logger.bind(
                event="middleware_db_error",
                exception_type=type(exc).__name__,
                path=request.url.path,
                error_id=error_id,
            ).error("SQLAlchemy error in middleware: {exc}", exc=str(exc)[:200])

            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Base de données temporairement indisponible.",
                    "error_id": error_id,
                },
            )

        except Exception as exc:
            settings = get_settings()
            error_id = uuid.uuid4().hex[:12]

            logger.bind(
                event="middleware_unhandled",
                exception_type=type(exc).__name__,
                path=request.url.path,
                method=request.method,
                client=request.client.host if request.client else "unknown",
                error_id=error_id,
            ).error(
                "Unhandled exception: {exc}\n{tb}",
                exc=str(exc),
                tb=traceback.format_exc() if settings.APP_DEBUG else "",
            )

            if settings.APP_ENV == "production":
                return JSONResponse(
                    status_code=500,
                    content={
                        "detail": "Une erreur interne est survenue.",
                        "error_id": error_id,
                    },
                )

            return JSONResponse(
                status_code=500,
                content={
                    "detail": str(exc),
                    "type": type(exc).__name__,
                    "error_id": error_id,
                },
            )
