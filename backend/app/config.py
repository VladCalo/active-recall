"""
Application configuration settings.

This module handles all configuration via environment variables with sensible defaults.
Uses pydantic-settings for type-safe configuration management.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "Active Recall Monitor"
    debug: bool = False
    
    # Database
    database_url: str = "sqlite:///./app.db"
    
    # CORS - allowed origins for frontend
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    
    # Default timezone for the application
    default_timezone: str = "Europe/Bucharest"
    
    # Default recall intervals in days
    default_intervals: list[int] = [1, 3, 7, 14, 30, 60, 120, 180]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Using lru_cache ensures settings are only loaded once from environment.
    """
    return Settings()
