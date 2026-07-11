"""
Admin API endpoints.

Provides admin-only functionality:
- System statistics
- User management
- Traffic metrics

Security: All endpoints require authentication AND admin privileges.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.core.deps import get_current_admin_user
from app.models.user import User
from app.services.admin_service import AdminService
from app.core.metrics import get_traffic_stats

router = APIRouter(prefix="/api/admin", tags=["admin"])


# =============================================================================
# Schemas
# =============================================================================

class AdminHealthResponse(BaseModel):
    """Admin health check response."""
    status: str
    admin_user: str
    message: str


class StatsResponse(BaseModel):
    """System statistics response."""
    total_users: int
    total_subjects: int
    admin_count: int
    disabled_users: int
    pending_approval_users: int
    active_users_last_7_days: int
    subjects_created_last_7_days: int
    reviews_due_today_total: int
    reviews_due_next_7_days_total: int


class UserListItem(BaseModel):
    """User item in list response."""
    id: str
    email: str
    is_admin: bool
    is_disabled: bool
    is_approved: bool
    created_at: Optional[str]
    last_login_at: Optional[str]
    subject_count: int


class UserListResponse(BaseModel):
    """Paginated user list response."""
    users: list[UserListItem]
    total: int
    skip: int
    limit: int


class SubjectSummary(BaseModel):
    """Subject summary for user details."""
    id: str
    name: str
    start_date: str
    category: str


class UserDetailResponse(BaseModel):
    """Detailed user information."""
    id: str
    email: str
    is_admin: bool
    is_disabled: bool
    is_approved: bool
    failed_login_attempts: int
    locked_until: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    last_login_at: Optional[str]
    subject_count: int
    subjects: list[SubjectSummary]


class UserUpdateRequest(BaseModel):
    """Request to update user."""
    is_admin: Optional[bool] = None
    is_disabled: Optional[bool] = None
    is_approved: Optional[bool] = None


class TrafficStatsResponse(BaseModel):
    """Traffic statistics response."""
    period_hours: int
    request_count_total: int
    requests_by_route: dict[str, int]
    status_code_counts: dict[str, int]
    avg_latency_ms: float
    p95_latency_ms: float
    requests_per_minute: float


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/health", response_model=AdminHealthResponse)
def admin_health(
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Admin health check endpoint.
    
    Verifies admin authentication is working.
    """
    return AdminHealthResponse(
        status="ok",
        admin_user=current_admin.email,
        message="Admin access verified"
    )


@router.get("/stats", response_model=StatsResponse)
def get_stats(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Get system-wide statistics.
    
    Returns counts and metrics about users, subjects, and reviews.
    """
    admin_service = AdminService(db)
    stats = admin_service.get_stats()
    return StatsResponse(**stats)


@router.get("/users", response_model=UserListResponse)
def list_users(
    skip: int = Query(default=0, ge=0, description="Records to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Max records to return"),
    search: Optional[str] = Query(default=None, description="Search by email"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    List all users with pagination.
    
    Supports searching by email.
    """
    admin_service = AdminService(db)
    users, total = admin_service.list_users(skip=skip, limit=limit, search=search)
    
    return UserListResponse(
        users=[UserListItem(**u) for u in users],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/users/{user_id}", response_model=UserDetailResponse)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Get detailed information about a specific user.
    """
    admin_service = AdminService(db)
    user = admin_service.get_user_details(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserDetailResponse(**user)


@router.patch("/users/{user_id}", response_model=UserDetailResponse)
def update_user(
    user_id: str,
    update: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Update user admin/disabled status.
    
    Cannot remove the last admin or demote yourself.
    """
    admin_service = AdminService(db)
    
    user, error = admin_service.update_user(
        user_id=user_id,
        current_admin_id=current_admin.id,
        is_admin=update.is_admin,
        is_disabled=update.is_disabled,
        is_approved=update.is_approved,
    )
    
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserDetailResponse(**user)


@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    x_admin_confirm: str = Header(
        ...,
        alias="X-Admin-Confirm",
        description="Must be 'DELETE' to confirm deletion"
    ),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Delete a user account.
    
    DANGEROUS: This permanently deletes the user and all their data.
    
    Requires confirmation header: X-Admin-Confirm: DELETE
    Cannot delete yourself or the last admin.
    """
    if x_admin_confirm != "DELETE":
        raise HTTPException(
            status_code=400,
            detail="Deletion not confirmed. Set header 'X-Admin-Confirm: DELETE'"
        )
    
    admin_service = AdminService(db)
    success, error = admin_service.delete_user(
        user_id=user_id,
        current_admin_id=current_admin.id,
    )
    
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    return {"message": "User deleted successfully", "user_id": user_id}


@router.get("/traffic", response_model=TrafficStatsResponse)
def get_traffic(
    hours: int = Query(default=24, ge=1, le=168, description="Hours to aggregate (max 7 days)"),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Get request traffic statistics.
    
    Returns aggregated metrics for the specified time period.
    """
    stats = get_traffic_stats(hours)
    return TrafficStatsResponse(**stats)
