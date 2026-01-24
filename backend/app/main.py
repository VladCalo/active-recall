"""
Active Recall Monitor - FastAPI Application Entry Point

This is the main entry point for the backend application.
It configures FastAPI, security headers, rate limiting, and includes all API routes.

Security Features:
- JWT authentication with refresh token rotation
- Argon2 password hashing
- Rate limiting (Redis-backed or in-memory)
- CORS with configurable origins
- Comprehensive security headers
- Request size limits
- Structured logging
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.database import engine, Base
from app.api import subjects_router, reviews_router, health_router, auth_router
from app.core.rate_limiter import limiter, rate_limit_exceeded_handler
from app.core.logging import setup_logging, get_logger

settings = get_settings()

# Setup structured logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    
    On startup: Creates database tables, logs startup.
    On shutdown: Logs shutdown.
    """
    logger.info(
        "application_startup",
        environment=settings.environment,
        debug=settings.debug
    )
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    
    logger.info("application_shutdown")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Track study subjects and generate daily review schedules using active recall / spaced repetition.",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug or settings.environment != "production" else None,
    redoc_url="/redoc" if settings.debug or settings.environment != "production" else None,
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


# =============================================================================
# Security Headers Middleware
# =============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add comprehensive security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Core security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"  # Deprecated, use CSP instead
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy (restrict browser features)
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), "
            "gyroscope=(), magnetometer=(), microphone=(), "
            "payment=(), usb=()"
        )
        
        # Production-only headers
        if settings.environment == "production":
            # HSTS - force HTTPS
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
            
            # CSP - Content Security Policy
            # Note: Adjust based on your frontend requirements
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            )
        
        return response


app.add_middleware(SecurityHeadersMiddleware)


# =============================================================================
# Request Size Limit Middleware
# =============================================================================

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limit request body size to prevent DoS."""
    
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            if int(content_length) > settings.max_request_body_size:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={"detail": "Request body too large"}
                )
        return await call_next(request)


app.add_middleware(RequestSizeLimitMiddleware)


# =============================================================================
# CORS Configuration
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,  # Required for cookies
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
    expose_headers=["X-RateLimit-Remaining", "X-RateLimit-Limit", "Retry-After"],
    max_age=600,  # Cache preflight for 10 minutes
)


# =============================================================================
# Error Handlers
# =============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with clean JSON response."""
    if settings.debug:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()},
        )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error. Please check your input."},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors without leaking internals."""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc) if settings.debug else "Internal error"
    )
    
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
    """Root endpoint - API information."""
    return {
        "app": settings.app_name,
        "version": "2.0.0",
        "docs": "/docs" if settings.debug else None,
        "health": "/api/health",
    }
