"""
Main application entry point for ServantAssist API
Clean Architecture implementation with FastAPI
"""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
import logging

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    _SENTRY_AVAILABLE = True
except ImportError:
    _SENTRY_AVAILABLE = False

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from prometheus_client import Counter, Gauge, Histogram, make_asgi_app

from src.infrastructure.config.settings import get_settings
from src.infrastructure.database.session import sessionmanager
from src.infrastructure.websocket.connection_manager import ConnectionManager

# ── Métriques Prometheus custom ───────────────────────────────────────────
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["path"],
)
active_ws_connections = Gauge(
    "active_ws_connections_total",
    "Number of active WebSocket connections",
)
from src.presentation.api.v1 import (
    activities,
    admin,
    api_keys,
    assignments,
    attendance,
    attendance_sessions,
    auth,
    classement,
    communication,
    dossier,
    contributions,
    cotisations,
    dashboard,
    discipline,
    email,
    financial_entries,
    material,
    poste,
    reports,
    responsables,
    sport_culture,
    subgroups,
    sunday_schedule,
    training,
    users,
    weekly_schedule,
)
from src.infrastructure.events.handlers import register_all_handlers
from src.presentation.middleware.error_handler import ErrorHandlerMiddleware
from src.presentation.middleware.idempotency import IdempotencyMiddleware
from src.presentation.middleware.logging_middleware import LoggingMiddleware
from src.presentation.middleware.owasp_guard import OWASPGuardMiddleware
from src.presentation.middleware.payload_encryption import PayloadEncryptionMiddleware
from src.presentation.middleware.rate_limit import RateLimitMiddleware
from src.presentation.exceptions.handlers import (
    domain_exception_handler,
    http_exception_handler,
    sqlalchemy_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from src.core.exceptions import ServantAssistException
from src.presentation.middleware.security_headers import SecurityHeadersMiddleware
from src.presentation.middleware.versioning import API_VERSION, VersioningMiddleware

settings = get_settings()
logger = logging.getLogger(__name__)

# ── Sentry initialisation (désactivé si SENTRY_DSN absent) ───────────────
if _SENTRY_AVAILABLE and settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.APP_ENV,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            RedisIntegration(),
        ],
        send_default_pii=False,
    )
    logger.info("Sentry initialized (env=%s)", settings.APP_ENV)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    register_all_handlers()
    logger.info("EventBus handlers registered")
    logger.info("Database session manager initialized")

    # ── WebSocket connection manager ─────────────────────────────────────
    app.state.ws_manager = ConnectionManager()
    await app.state.ws_manager.start_heartbeat()
    logger.info("WebSocket connection manager initialized")

    # ── Initialisation Redis (optionnel) ────────────────────────────
    redis_client = None
    if settings.APP_ENV != "testing":
        try:
            import redis.asyncio as aioredis

            redis_client = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=3,
            )
            await redis_client.ping()
            logger.info("Redis connected")

            # Configurer les backends distribues
            from src.infrastructure.security.brute_force import brute_force_guard
            from src.infrastructure.security.token_blacklist import token_blacklist
            from src.presentation.middleware.rate_limit import rate_limiter

            brute_force_guard.configure_redis(redis_client)
            rate_limiter.configure_redis(redis_client)
            token_blacklist.configure_redis(redis_client)
        except Exception as exc:
            logger.warning(
                "Redis unavailable, using in-memory fallback | error=%s",
                str(exc),
            )
            redis_client = None

    # ── Tâche de cleanup périodique (in-memory fallback) ─────────────────
    async def _cleanup_loop():
        from src.infrastructure.security.token_blacklist import token_blacklist
        from src.presentation.middleware.rate_limit import rate_limiter as _rl

        while True:
            await asyncio.sleep(300)  # Toutes les 5 min
            _rl._memory_backend.cleanup()
            token_blacklist.cleanup_memory()

    cleanup_task = asyncio.create_task(_cleanup_loop())

    yield

    # Shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

    await app.state.ws_manager.stop_heartbeat()

    if redis_client:
        await redis_client.close()
        logger.info("Redis disconnected")
    if sessionmanager._engine is not None:
        await sessionmanager.close()
    logger.info("Database disconnected")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="API for managing altar servers and their activities",
    version="1.0.0",
    docs_url="/api/docs" if settings.APP_ENV == "development" else None,
    redoc_url="/api/redoc" if settings.APP_ENV == "development" else None,
    lifespan=lifespan,
)

# ── Exception handlers (ordre : du plus spécifique au plus général) ───
from fastapi.exceptions import HTTPException, RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(ServantAssistException, domain_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# ── Middleware (ordre : du plus externe au plus interne) ──────────────
# 1. OWASP Guard — rejet précoce avant tout autre traitement
app.add_middleware(OWASPGuardMiddleware)
# 2. Rate limiting
app.add_middleware(RateLimitMiddleware)
# 2. Versioning (X-API-Version + X-Request-ID sur toutes les réponses)
app.add_middleware(VersioningMiddleware)
# 3. Logging (trace toutes les requetes, y compris les bloquees)
app.add_middleware(LoggingMiddleware)
# 4. Error handler (attrape les exceptions non gerees)
app.add_middleware(ErrorHandlerMiddleware)
# 5. Security headers (ajoute HSTS, CSP, X-Frame-Options, etc.)
app.add_middleware(SecurityHeadersMiddleware)
# 6. Idempotency (détecte les doubles soumissions POST)
app.add_middleware(IdempotencyMiddleware)
# 7. GZip (compression des reponses)
app.add_middleware(GZipMiddleware, minimum_size=1000)
# 8. CORS (autorise les origines configurees)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "X-Requested-With",
        "X-Request-ID",
        "Idempotency-Key",
        "X-Client-Pubkey",  # chiffrement ECDH éphémère (Loi 2024/017)
    ],
    expose_headers=[
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "Retry-After",
        "X-API-Version",
        "X-Request-ID",
        "X-Total-Count",
        "Link",
    ],
    max_age=600,
)

# API Routes
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(activities.router, prefix="/api/v1/events", tags=["Events"])
app.include_router(
    communication.router,
    prefix="/api/v1/communication",
     tags=["Communication"])
app.include_router(
    assignments.router,
    prefix="/api/v1/assignments",
     tags=["Assignments"])
app.include_router(
    responsables.router,
    prefix="/api/v1/responsables",
     tags=["Responsables"])
app.include_router(
    poste.router,
    prefix="/api/v1/poste",
     tags=["Postes (Dynamic)"])
app.include_router(
    discipline.router,
    prefix="/api/v1/discipline",
     tags=["Discipline"])
app.include_router(
    cotisations.router,
    prefix="/api/v1/cotisations",
     tags=["Cotisations"])
app.include_router(
    attendance.router,
    prefix="/api/v1/attendance",
     tags=["Attendance"])
app.include_router(
    subgroups.router,
    prefix="/api/v1/subgroups",
     tags=["Sub-Groups"])
app.include_router(
    attendance_sessions.router,
    prefix="/api/v1/attendance-sessions",
    tags=["Attendance Sessions"],
)
app.include_router(
    contributions.router,
    prefix="/api/v1/contributions",
     tags=["Contributions"])
app.include_router(
    financial_entries.router,
    prefix="/api/v1/financial-entries",
    tags=["Financial Entries"],
)
app.include_router(
    material.router,
    prefix="/api/v1/material",
     tags=["Material"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(classement.router, prefix="/api/v1/classements", tags=["Classements"])
app.include_router(email.router, prefix="/api/v1/email", tags=["Email"])
app.include_router(dossier.router, prefix="/api/v1/dossier", tags=["Dossier"])
app.include_router(
    sport_culture.router,
    prefix="/api/v1/sport-culture",
     tags=["Sport & Culture"])
app.include_router(
    sunday_schedule.router,
    prefix="/api/v1/sunday-schedule",
     tags=["Sunday Schedule"])
app.include_router(
    training.router,
    prefix="/api/v1/training",
     tags=["Training"])
app.include_router(
    weekly_schedule.router,
    prefix="/api/v1/weekly-schedule",
     tags=["Weekly Schedule"])
app.include_router(
    dashboard.router,
    prefix="/api/v1/dashboard",
    tags=["Dashboard"],
)
app.include_router(
    api_keys.router,
    prefix="/api/v1/api-keys",
    tags=["API Keys"],
)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "name": "ServantAssist API",
        "version": API_VERSION,
        "docs": "/api/docs",
        "health": "/health",
        "ready": "/ready",
        "api_version": "/api/v1/version",
    }


@app.get(
    "/ready",
    tags=["System"],
    summary="Readiness probe",
    description="Retourne 200 si l'application est prête à recevoir du trafic (DB accessible). "
                "Utilisé par Kubernetes / load-balancer avant de router les requêtes.",
)
async def readiness_probe():
    """Sonde de disponibilité : vérifie que la base de données est joignable."""
    from fastapi.responses import JSONResponse
    from sqlmodel import text as sqltext

    try:
        async with sessionmanager.session() as session:
            await session.exec(sqltext("SELECT 1"))
        return {"status": "ready"}
    except Exception as exc:
        logger.error("Readiness probe failed: %s", str(exc))
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "detail": "Database unreachable"},
        )


@app.get(
    "/api/v1/version",
    tags=["System"],
    summary="Version de l'API",
    description="Retourne la version courante de l'API et les informations de build.",
)
async def api_version():
    """Métadonnées de version — utilisé par l'app mobile pour vérifier la compatibilité."""
    from src.presentation.middleware.versioning import API_RELEASE_DATE

    return {
        "version": API_VERSION,
        "release_date": API_RELEASE_DATE,
        "environment": settings.APP_ENV,
        "min_client_version": "1.0.0",
        "deprecations": [],
    }


@app.get("/health")
async def health_check():
    """
    Advanced health check endpoint.

    Returns:
        200 with status "healthy" or "degraded" if non-critical services are down.
        503 with status "unhealthy" if the database is unreachable.
    """
    import time
    from datetime import timezone

    from fastapi.responses import JSONResponse

    checks: dict = {}
    overall = "healthy"

    # ── Database check ────────────────────────────────────────────────────
    try:
        t0 = time.monotonic()
        async with sessionmanager.session() as session:
            from sqlmodel import text
            await session.exec(text("SELECT 1"))
        db_latency = round((time.monotonic() - t0) * 1000, 1)
        checks["database"] = {"status": "ok", "latency_ms": db_latency}
    except Exception as exc:
        checks["database"] = {"status": "error", "error": str(exc)[:80]}
        overall = "unhealthy"

    # ── Redis check ───────────────────────────────────────────────────────
    try:
        import redis.asyncio as aioredis

        t0 = time.monotonic()
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await r.ping()
        await r.close()
        redis_latency = round((time.monotonic() - t0) * 1000, 1)
        checks["redis"] = {"status": "ok", "latency_ms": redis_latency}
    except Exception as exc:
        checks["redis"] = {"status": "error", "error": str(exc)[:80]}
        if overall == "healthy":
            overall = "degraded"  # Redis non bloquant

    # ── WebSocket connections count ───────────────────────────────────────
    ws_manager = getattr(app.state, "ws_manager", None)
    if ws_manager is not None:
        checks["websocket"] = {
            "status": "ok",
            "active_connections": ws_manager.total_connections,
            "connected_users": ws_manager.connected_users,
        }

    payload = {
        "status": overall,
        "version": "1.0.0",
        "environment": settings.APP_ENV,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    http_status = 503 if overall == "unhealthy" else 200
    return JSONResponse(content=payload, status_code=http_status)


# 9. Déchiffrement de charge utile (Loi 2024/017 — POST/PUT/PATCH chiffrés)
app.add_middleware(PayloadEncryptionMiddleware)

# ── Fichiers statiques uploadés (dev local sans R2) ──────────────────────
_uploads_dir = Path("uploads")
_uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads_dir)), name="uploads")

# ── Assets statiques (logo, images système) ───────────────────────────────
_static_dir = Path("static")
_static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

# ── Prometheus metrics endpoint ───────────────────────────────────────────
_metrics_app = make_asgi_app()
app.mount("/metrics", _metrics_app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # nosec B104 — bind all interfaces dans Docker
        port=8000,
        reload=settings.APP_ENV == "development",
    )
