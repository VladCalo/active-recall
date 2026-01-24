"""
Password validation and common password checking.

This module provides:
- Strong password policy enforcement
- Common password detection
- Password strength feedback
"""

import re
from typing import List, Tuple

from app.config import get_settings

settings = get_settings()

# Top 1000 most common passwords (abbreviated for space - in production use a full list)
COMMON_PASSWORDS = {
    "123456", "password", "12345678", "qwerty", "123456789", "12345", "1234",
    "111111", "1234567", "dragon", "123123", "baseball", "iloveyou", "trustno1",
    "sunshine", "master", "welcome", "shadow", "ashley", "football", "jesus",
    "michael", "ninja", "mustang", "password1", "password123", "123qwe",
    "qwerty123", "letmein", "admin", "login", "abc123", "monkey", "princess",
    "starwars", "passw0rd", "hello", "charlie", "donald", "qwertyuiop",
    "000000", "654321", "lovely", "7777777", "888888", "superman", "admin123",
    "password!", "p@ssword", "p@ssw0rd", "passwd", "pass123", "test123",
    "changeme", "default", "guest", "secret", "computer", "internet",
    "qazwsx", "access", "master1", "matrix", "whatever", "soccer",
    "diamond", "summer", "sunshine1", "winter", "spring", "autumn",
    # Add more as needed in production
}


def check_password_strength(password: str) -> Tuple[bool, List[str]]:
    """
    Check password strength and return validation result.
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    # Length check
    if len(password) < settings.min_password_length:
        issues.append(f"Password must be at least {settings.min_password_length} characters")
    
    if settings.require_password_complexity:
        # Uppercase check
        if not re.search(r'[A-Z]', password):
            issues.append("Password must contain at least one uppercase letter")
        
        # Lowercase check
        if not re.search(r'[a-z]', password):
            issues.append("Password must contain at least one lowercase letter")
        
        # Number check
        if not re.search(r'\d', password):
            issues.append("Password must contain at least one number")
        
        # Special character check (optional but recommended)
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            issues.append("Password must contain at least one special character")
    
    # Common password check
    if settings.check_common_passwords:
        if password.lower() in COMMON_PASSWORDS:
            issues.append("This password is too common. Please choose a stronger password")
        
        # Check for password variations
        password_lower = password.lower()
        for common in COMMON_PASSWORDS:
            if common in password_lower:
                if len(password) < len(common) + 4:  # Must add significant length
                    issues.append("Password is too similar to a common password")
                    break
    
    # Repeated characters check
    if re.search(r'(.)\1{3,}', password):
        issues.append("Password contains too many repeated characters")
    
    # Sequential characters check
    if _has_sequential_chars(password, 4):
        issues.append("Password contains sequential characters (e.g., 1234, abcd)")
    
    return len(issues) == 0, issues


def _has_sequential_chars(password: str, length: int = 4) -> bool:
    """Check for sequential characters."""
    sequences = [
        "0123456789",
        "9876543210",
        "abcdefghijklmnopqrstuvwxyz",
        "zyxwvutsrqponmlkjihgfedcba",
        "qwertyuiop",
        "asdfghjkl",
        "zxcvbnm",
    ]
    
    password_lower = password.lower()
    for seq in sequences:
        for i in range(len(seq) - length + 1):
            if seq[i:i+length] in password_lower:
                return True
    
    return False


def get_password_requirements() -> List[str]:
    """Get human-readable password requirements."""
    requirements = [
        f"At least {settings.min_password_length} characters long"
    ]
    
    if settings.require_password_complexity:
        requirements.extend([
            "At least one uppercase letter (A-Z)",
            "At least one lowercase letter (a-z)",
            "At least one number (0-9)",
            "At least one special character (!@#$%^&*)",
        ])
    
    if settings.check_common_passwords:
        requirements.append("Not a commonly used password")
    
    return requirements
