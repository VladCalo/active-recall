"""
Admin service - handles admin-only operations.

Provides functionality for:
- User management (list, update, disable, delete)
- System statistics
- Admin seeding

Security: All operations require admin authorization at the API layer.
"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.user import User
from app.models.subject import Subject
from app.services.review_service import ReviewService
from app.core.security import hash_password
from app.config import get_settings


class AdminService:
    """Service class for admin operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
    
    def get_stats(self) -> dict:
        """
        Get system-wide statistics.
        
        Returns:
            Dictionary with various stats
        """
        now = datetime.utcnow()
        seven_days_ago = now - timedelta(days=7)
        
        # Total counts
        total_users = self.db.query(func.count(User.id)).scalar() or 0
        total_subjects = self.db.query(func.count(Subject.id)).scalar() or 0
        
        # Admin count
        admin_count = self.db.query(func.count(User.id)).filter(
            User.is_admin == True
        ).scalar() or 0
        
        # Active users (logged in last 7 days)
        active_users_7d = self.db.query(func.count(User.id)).filter(
            User.last_login_at >= seven_days_ago
        ).scalar() or 0
        
        # Subjects created last 7 days
        subjects_created_7d = self.db.query(func.count(Subject.id)).filter(
            Subject.created_at >= seven_days_ago
        ).scalar() or 0
        
        # Disabled users
        disabled_users = self.db.query(func.count(User.id)).filter(
            User.is_disabled == True
        ).scalar() or 0

        # Users awaiting admin approval
        pending_approval_users = self.db.query(func.count(User.id)).filter(
            User.is_approved == False
        ).scalar() or 0
        
        # Calculate reviews due today and next 7 days (across all users)
        reviews_due_today = 0
        reviews_due_7d = 0
        
        all_users = self.db.query(User).filter(User.is_disabled == False).all()
        for user in all_users:
            review_service = ReviewService(self.db, user)
            today = review_service.get_today()
            end_7d = today + timedelta(days=6)
            
            # Today's reviews (includes overdue)
            reviews_due_today += len(review_service.get_due_today())

            # Next 7 days (upcoming next_due_date + completions already logged in range)
            range_items = review_service.get_calendar_range(today, end_7d)
            for items in range_items.values():
                reviews_due_7d += len(items)
        
        return {
            "total_users": total_users,
            "total_subjects": total_subjects,
            "admin_count": admin_count,
            "disabled_users": disabled_users,
            "pending_approval_users": pending_approval_users,
            "active_users_last_7_days": active_users_7d,
            "subjects_created_last_7_days": subjects_created_7d,
            "reviews_due_today_total": reviews_due_today,
            "reviews_due_next_7_days_total": reviews_due_7d,
        }
    
    def list_users(
        self,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        """
        List users with pagination and optional search.
        
        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            search: Optional email search query
            
        Returns:
            Tuple of (user list, total count)
        """
        query = self.db.query(User)
        
        if search:
            query = query.filter(User.email.ilike(f"%{search}%"))
        
        total = query.count()
        
        users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
        
        result = []
        for user in users:
            subject_count = self.db.query(func.count(Subject.id)).filter(
                Subject.user_id == user.id
            ).scalar() or 0
            
            result.append({
                "id": user.id,
                "email": user.email,
                "is_admin": user.is_admin,
                "is_disabled": user.is_disabled,
                "is_approved": user.is_approved,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
                "subject_count": subject_count,
            })
        
        return result, total
    
    def get_user_details(self, user_id: str) -> Optional[dict]:
        """
        Get detailed information about a specific user.
        
        Args:
            user_id: User UUID
            
        Returns:
            User details dict or None if not found
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        # Get subjects with summary
        subjects = self.db.query(Subject).filter(Subject.user_id == user_id).all()
        subjects_summary = []
        
        for subject in subjects:
            subjects_summary.append({
                "id": str(subject.id),
                "name": subject.name,
                "start_date": subject.start_date.isoformat(),
                "category": subject.category.value,
            })
        
        return {
            "id": user.id,
            "email": user.email,
            "is_admin": user.is_admin,
            "is_disabled": user.is_disabled,
            "is_approved": user.is_approved,
            "failed_login_attempts": user.failed_login_attempts,
            "locked_until": user.locked_until.isoformat() if user.locked_until else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "subject_count": len(subjects),
            "subjects": subjects_summary,
        }
    
    def update_user(
        self,
        user_id: str,
        current_admin_id: str,
        is_admin: Optional[bool] = None,
        is_disabled: Optional[bool] = None,
        is_approved: Optional[bool] = None,
    ) -> tuple[Optional[dict], Optional[str]]:
        """
        Update user admin/disabled/approval status.

        Args:
            user_id: User to update
            current_admin_id: ID of admin performing the action
            is_admin: New admin status (optional)
            is_disabled: New disabled status (optional)
            is_approved: New approval status (optional)

        Returns:
            Tuple of (updated user dict, error message)
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None, "User not found"

        # Prevent removing last admin
        if is_admin is False and user.is_admin:
            admin_count = self.db.query(func.count(User.id)).filter(
                User.is_admin == True
            ).scalar() or 0
            if admin_count <= 1:
                return None, "Cannot remove the last admin"

        # Prevent self-demotion (can still disable self, but not remove admin)
        if user_id == current_admin_id and is_admin is False:
            return None, "Cannot remove your own admin privileges"

        # Apply updates
        if is_admin is not None:
            user.is_admin = is_admin
        if is_disabled is not None:
            user.is_disabled = is_disabled
            # If enabling, reset lockout
            if not is_disabled:
                user.failed_login_attempts = 0
                user.locked_until = None
        if is_approved is not None:
            user.is_approved = is_approved

        self.db.commit()
        self.db.refresh(user)

        return self.get_user_details(user_id), None
    
    def delete_user(
        self,
        user_id: str,
        current_admin_id: str,
    ) -> tuple[bool, Optional[str]]:
        """
        Delete a user account.
        
        Args:
            user_id: User to delete
            current_admin_id: ID of admin performing the action
            
        Returns:
            Tuple of (success, error message)
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False, "User not found"
        
        # Prevent self-deletion
        if user_id == current_admin_id:
            return False, "Cannot delete your own account"
        
        # Prevent deleting last admin
        if user.is_admin:
            admin_count = self.db.query(func.count(User.id)).filter(
                User.is_admin == True
            ).scalar() or 0
            if admin_count <= 1:
                return False, "Cannot delete the last admin"
        
        self.db.delete(user)
        self.db.commit()
        
        return True, None


def seed_admin_user(db: Session) -> tuple[bool, str]:
    """
    Seed the initial admin user if none exists.
    
    Uses environment variables for credentials.
    Idempotent - does nothing if an admin already exists.
    
    Args:
        db: Database session
        
    Returns:
        Tuple of (created, message)
    """
    import os
    
    # Skip seeding in test environment
    if os.environ.get("TESTING") == "1":
        return False, "Skipped in test environment"
    
    settings = get_settings()
    
    # Check if any admin exists
    try:
        existing_admin = db.query(User).filter(User.is_admin == True).first()
    except Exception:
        # Column might not exist yet (e.g., before migration)
        return False, "Admin seeding skipped - migration may be needed"
    if existing_admin:
        return False, f"Admin already exists: {existing_admin.email}"
    
    # Check production safety
    default_email = "adminvladcalo"
    default_password = "Adminvladcalo123!"
    
    is_default_email = settings.admin_email == default_email
    is_default_password = settings.admin_password == default_password
    
    if settings.environment == "production":
        if is_default_email or is_default_password:
            if not settings.admin_allow_default:
                raise RuntimeError(
                    "\n" + "=" * 60 + "\n"
                    "SECURITY ERROR: Default admin credentials detected in production!\n"
                    "=" * 60 + "\n"
                    "You MUST change ADMIN_EMAIL and ADMIN_PASSWORD in your .env file.\n"
                    "\n"
                    "To proceed with defaults (NOT RECOMMENDED), set:\n"
                    "  ADMIN_ALLOW_DEFAULT=true\n"
                    "\n"
                    "Current settings:\n"
                    f"  ADMIN_EMAIL: {settings.admin_email}\n"
                    f"  ADMIN_PASSWORD: {'[DEFAULT - CHANGE ME!]' if is_default_password else '[Custom]'}\n"
                    "=" * 60
                )
            else:
                import warnings
                warnings.warn(
                    "Using default admin credentials in production! "
                    "This is a security risk. Change ADMIN_EMAIL and ADMIN_PASSWORD immediately.",
                    UserWarning
                )
    
    # Create admin user
    admin_user = User(
        email=settings.admin_email.lower(),
        password_hash=hash_password(settings.admin_password),
        is_admin=True,
        is_disabled=False,
        is_approved=True,
    )
    
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    
    return True, f"Admin user created: {admin_user.email}"
