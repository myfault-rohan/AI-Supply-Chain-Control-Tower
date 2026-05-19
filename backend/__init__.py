"""
Backend package for AI Supply Chain Platform.
Exports core modules for database, models, auth, and schemas.
"""

from backend.database import engine, SessionLocal, Base, get_db, init_db
from backend.models import User, Product, Supplier, Forecast, Alert, ReorderRecommendation
from backend.auth import authenticate_user, create_access_token, verify_token, create_user
from backend.schemas import (
    TokenRequest, TokenResponse, UserCreate, UserResponse,
    HealthCheck, SystemHealth, UploadResponse, DataQualityReport
)

__all__ = [
    # Database
    "engine",
    "SessionLocal", 
    "Base",
    "get_db",
    "init_db",
    # Models
    "User",
    "Product",
    "Supplier",
    "Forecast",
    "Alert",
    "ReorderRecommendation",
    # Auth
    "authenticate_user",
    "create_access_token",
    "verify_token",
    "create_user",
    # Schemas
    "TokenRequest",
    "TokenResponse",
    "UserCreate",
    "UserResponse",
    "HealthCheck",
    "SystemHealth",
    "UploadResponse",
    "DataQualityReport",
]
