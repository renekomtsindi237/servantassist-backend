"""
Main application entry point for ServantAssist API
Clean Architecture implementation with FastAPI
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager

from src.infrastructure.config.settings import get_settings
from src.infrastructure.database.connection import database
from src.presentation.api.v1 import auth, users, activities, communication
from src.presentation.middleware.error_handler import ErrorHandlerMiddleware
from src.presentation.middleware.logging_middleware import LoggingMiddleware
from src.presentation.middleware.rate_limit import RateLimitMiddleware

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    await database.connect()
    print("✅ Database connected")
    
    yield
    
    # Shutdown
    await database.disconnect()
    print("❌ Database disconnected")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="API for managing altar servers and their activities",
    version="1.0.0",
    docs_url="/api/docs" if settings.APP_ENV == "development" else None,
    redoc_url="/api/redoc" if settings.APP_ENV == "development" else None,
    lifespan=lifespan,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# API Routes
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["Authentication"]
)
app.include_router(
    users.router,
    prefix="/api/v1/users",
    tags=["Users"]
)
app.include_router(
    activities.router,
    prefix="/api/v1/activities",
    tags=["Activities"]
)
app.include_router(
    communication.router,
    prefix="/api/v1/communication",
    tags=["Communication"]
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
        "database": "connected" if database.is_connected else "disconnected",
        "environment": settings.APP_ENV
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.APP_ENV == "development"
    )
