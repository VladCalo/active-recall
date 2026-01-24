"""
Active Recall Monitor - FastAPI Application Entry Point

This is the main entry point for the backend application.
It configures FastAPI, CORS, security headers, rate limiting, and includes all API routes.

Architecture Overview:
- /app/api/       - FastAPI route handlers
- /app/models/    - SQLAlchemy ORM models
- /app/schemas/   - Pydantic validation schemas
- /app/services/  - Business logic services
- /app/core/      - Security, auth, dependencies
- /app/config.py  - Configuration management
- /app/database.py - Database setup and session management

Security Features:
- JWT authentication with access/refresh tokens
- Argon2 password hashing
- Rate limiting on auth endpoints
- CORS with configurable origins
- Security headers
- httpOnly cookies for refresh tokens
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.database import engine, Base
from app.api import subjects_router, reviews_router, health_router, auth_router

settings = get_settings()

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    
    On startup: Creates database tables if they don't exist.
    This is a simple approach for SQLite; for production Postgres,
    you'd use Alembic migrations exclusively.
    """
    # Startup: Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: Nothing needed for SQLite


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Track study subjects and generate daily review schedules using active recall / spaced repetition.",
    version="1.0.0",
    lifespan=lifespan,
    # Disable docs in production if desired
    docs_url="/docs" if settings.debug else "/docs",
    redoc_url="/redoc" if settings.debug else "/redoc",
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,  # Required for cookies
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# =============================================================================
# Security Headers Middleware
# =============================================================================

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # In production, add Strict-Transport-Security
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response


# =============================================================================
# Error Handlers
# =============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle validation errors with clean JSON response.
    
    Avoids exposing internal details in error messages.
    """
    # In debug mode, show detailed errors
    if settings.debug:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()},
        )
    
    # In production, show generic error
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error. Please check your input."},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Handle unexpected errors.
    
    In debug mode: show full error
    In production: show generic message (don't leak internals)
    """
    if settings.debug:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc)},
        )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred."},
    )


# =============================================================================
# Include API Routers
# =============================================================================

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(subjects_router)
app.include_router(reviews_router)


@app.get("/")
def root():
    """
    Root endpoint - API information.
    
    Useful for quick checks and discovery.
    """
    return {
        "app": settings.app_name,
        "docs": "/docs",
        "health": "/api/health",
    }
