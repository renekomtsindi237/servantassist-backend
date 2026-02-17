"""
Main application entry point for ServantAssist API
Clean Architecture implementation with FastAPI
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager

from src.infrastructure.config.settings import get_settings
from src.infrastructure.database.session import sessionmanager
from src.presentation.api.v1 import (
    admin, auth, users, activities, communication,
    assignments, responsables, poste,
    discipline, cotisations, attendance, subgroups,
    attendance_sessions, contributions, financial_entries,
    material, reports, sport_culture, sunday_schedule,
    training, weekly_schedule,
)
from src.presentation.middleware.error_handler import ErrorHandlerMiddleware
from src.presentation.middleware.logging_middleware import LoggingMiddleware
from src.presentation.middleware.rate_limit import RateLimitMiddleware
from src.presentation.middleware.security_headers import SecurityHeadersMiddleware

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("Database session manager initialized")
    
    yield
    
    # Shutdown
    if sessionmanager._engine is not None:
        await sessionmanager.close()
    print("Database disconnected")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="API for managing altar servers and their activities",
    version="1.0.0",
    docs_url="/api/docs" if settings.APP_ENV == "development" else None,
    redoc_url="/api/redoc" if settings.APP_ENV == "development" else None,
    lifespan=lifespan,
)

# ── Middleware (ordre : du plus externe au plus interne) ──────────────
# 1. Rate limiting (bloque avant tout traitement)
app.add_middleware(RateLimitMiddleware)
# 2. Logging (trace toutes les requetes, y compris les bloquees)
app.add_middleware(LoggingMiddleware)
# 3. Error handler (attrape les exceptions non gerees)
app.add_middleware(ErrorHandlerMiddleware)
# 4. Security headers (ajoute HSTS, CSP, X-Frame-Options, etc.)
app.add_middleware(SecurityHeadersMiddleware)
# 5. GZip (compression des reponses)
app.add_middleware(GZipMiddleware, minimum_size=1000)
# 6. CORS (autorise les origines configurees)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "Retry-After"],
    max_age=600,  # Cache preflight pour 10 min
)

# API Routes
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["Authentication"]
)
app.include_router(
    admin.router,
    prefix="/api/v1/admin",
    tags=["Admin"]
)
app.include_router(
    users.router,
    prefix="/api/v1/users",
    tags=["Users"]
)
app.include_router(
    activities.router,
    prefix="/api/v1/events",
    tags=["Events"]
)
app.include_router(
    communication.router,
    prefix="/api/v1/communication",
    tags=["Communication"]
)
app.include_router(
    assignments.router,
    prefix="/api/v1/assignments",
    tags=["Assignments"]
)
app.include_router(
    responsables.router,
    prefix="/api/v1/responsables",
    tags=["Responsables"]
)
app.include_router(
    poste.router,
    prefix="/api/v1/poste",
    tags=["Postes (Dynamic)"]
)
app.include_router(
    discipline.router,
    prefix="/api/v1/discipline",
    tags=["Discipline"]
)
app.include_router(
    cotisations.router,
    prefix="/api/v1/cotisations",
    tags=["Cotisations"]
)
app.include_router(
    attendance.router,
    prefix="/api/v1/attendance",
    tags=["Attendance"]
)
app.include_router(
    subgroups.router,
    prefix="/api/v1/subgroups",
    tags=["Sub-Groups"]
)
app.include_router(
    attendance_sessions.router,
    prefix="/api/v1/attendance-sessions",
    tags=["Attendance Sessions"]
)
app.include_router(
    contributions.router,
    prefix="/api/v1/contributions",
    tags=["Contributions"]
)
app.include_router(
    financial_entries.router,
    prefix="/api/v1/financial-entries",
    tags=["Financial Entries"]
)
app.include_router(
    material.router,
    prefix="/api/v1/material",
    tags=["Material"]
)
app.include_router(
    reports.router,
    prefix="/api/v1/reports",
    tags=["Reports"]
)
app.include_router(
    sport_culture.router,
    prefix="/api/v1/sport-culture",
    tags=["Sport & Culture"]
)
app.include_router(
    sunday_schedule.router,
    prefix="/api/v1/sunday-schedule",
    tags=["Sunday Schedule"]
)
app.include_router(
    training.router,
    prefix="/api/v1/training",
    tags=["Training"]
)
app.include_router(
    weekly_schedule.router,
    prefix="/api/v1/weekly-schedule",
    tags=["Weekly Schedule"]
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to ServantAssist API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.APP_ENV
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # nosec B104 — bind all interfaces dans Docker
        port=8000,
        reload=settings.APP_ENV == "development",
    )
