"""
Health check endpoint.

Provides a simple health check for monitoring and load balancers.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["health"])


class HealthResponse(BaseModel):
    """Health check response."""
    ok: bool


@router.get("/health", response_model=HealthResponse)
def health_check():
    """
    Health check endpoint.
    
    Returns:
        {"ok": true} if the service is healthy
    """
    return HealthResponse(ok=True)
