"""
Unit Tests for AI Supply Chain Analytics Platform API (Phase 1).

Tests cover:
- System health and information endpoints
- Authentication (registration, login, JWT tokens)
- Protected endpoints and authorization
- Request/response schema validation
- Error handling
"""

import pytest
import sys
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.api_server_phase1 import app
from backend.database import Base, get_db
from backend.models import User
from backend.auth import hash_password

# ============================================================================
# Test Database Setup
# ============================================================================
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    """Override database dependency for tests."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


# ============================================================================
# Fixtures
# ============================================================================
@pytest.fixture
def db():
    """Create fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(db):
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=hash_password("TestPass123456"),
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user):
    """Get authentication token for test user."""
    response = client.post(
        "/api/v1/token",
        json={"username": "testuser", "password": "TestPass123456"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


# ============================================================================
# System Endpoint Tests
# ============================================================================
class TestSystemEndpoints:
    """Test system health and information endpoints."""
    
    def test_root_endpoint_returns_info(self):
        """Test root endpoint returns API information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data
    
    def test_health_check_endpoint(self):
        """Test health check endpoint returns status."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "timestamp" in data


# ============================================================================
# Authentication Tests
# ============================================================================
class TestAuthenticationEndpoints:
    """Test authentication and JWT token generation."""
    
    def test_register_new_user(self, db):
        """Test successful user registration."""
        response = client.post(
            "/api/v1/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "NewPass123456"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"
        assert data["is_active"] is True
    
    def test_register_duplicate_username_fails(self, test_user):
        """Test registration fails for duplicate username."""
        response = client.post(
            "/api/v1/register",
            json={
                "username": "testuser",  # Already exists
                "email": "another@example.com",
                "password": "Pass123456"
            }
        )
        assert response.status_code == 409
    
    def test_login_with_valid_credentials(self, test_user):
        """Test successful login returns JWT token."""
        response = client.post(
            "/api/v1/token",
            json={"username": "testuser", "password": "TestPass123456"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 28800
    
    def test_login_with_invalid_password(self, test_user):
        """Test login fails with incorrect password."""
        response = client.post(
            "/api/v1/token",
            json={"username": "testuser", "password": "WrongPassword123456"}
        )
        assert response.status_code == 401
    
    def test_login_nonexistent_user_fails(self):
        """Test login fails for non-existent user."""
        response = client.post(
            "/api/v1/token",
            json={"username": "nonexistent", "password": "Pass123456"}
        )
        assert response.status_code == 401


# ============================================================================
# Protected Endpoint Tests
# ============================================================================
class TestProtectedEndpoints:
    """Test endpoints requiring authentication."""
    
    def test_dashboard_without_auth_fails(self):
        """Test dashboard endpoint requires authentication."""
        response = client.get("/api/v1/dashboard")
        assert response.status_code == 401
    
    def test_dashboard_with_valid_token(self, auth_token):
        """Test dashboard succeeds with valid authentication."""
        response = client.get(
            "/api/v1/dashboard",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
    
    def test_forecasts_with_valid_token(self, auth_token):
        """Test forecasts endpoint with authentication."""
        response = client.get(
            "/api/v1/forecasts",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
    
    def test_alerts_with_valid_token(self, auth_token):
        """Test alerts endpoint with authentication."""
        response = client.get(
            "/api/v1/alerts",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
    
    def test_admin_health_with_valid_token(self, auth_token):
        """Test admin health endpoint returns system metrics."""
        response = client.get(
            "/api/v1/admin/health",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "Healthy"
        assert "api_version" in data
        assert "workspaces" in data
        assert "processed_files" in data


# ============================================================================
# Response Format Tests
# ============================================================================
class TestResponseFormats:
    """Test API response formatting and error handling."""
    
    def test_unauthorized_response_format(self):
        """Test unauthorized responses return proper error."""
        response = client.get("/api/v1/forecasts")  # No auth header
        assert response.status_code == 401
    
    def test_root_response_contains_docs_link(self):
        """Test root endpoint provides link to documentation."""
        response = client.get("/")
        data = response.json()
        assert "/api/docs" in str(data)


# ============================================================================
# Test Execution
# ============================================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
