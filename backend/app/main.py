"""
Active Recall Monitor - FastAPI Application Entry Point

This is the main entry point for the backend application.
It configures FastAPI, CORS, and includes all API routes.

Architecture Overview:
- /app/api/       - FastAPI route handlers
- /app/models/    - SQLAlchemy ORM models
- /app/schemas/   - Pydantic validation schemas
- /app/services/  - Business logic services
- /app/config.py  - Configuration management
- /app/database.py - Database setup and session management
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import engine, Base
from app.api import subjects_router, reviews_router, health_router

settings = get_settings()


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
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health_router)
app.include_router(subjects_router)
app.include_router(reviews_router)


@app.get("/")
def root():
    """
    Root endpoint - redirects to API documentation.
    
    Useful for quick checks and discovery.
    """
    return {
        "app": settings.app_name,
        "docs": "/docs",
        "health": "/api/health",
    }
