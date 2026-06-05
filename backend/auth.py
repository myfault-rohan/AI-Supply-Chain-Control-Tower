"""
Authentication and JWT Token Management.
Upgraded to use SQLAlchemy models instead of JSON files.
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES
from backend.models import User
import bcrypt as _bcrypt

# ============================================================================
# Password Hashing  (direct bcrypt — passlib not used as it breaks on bcrypt 4.x)
# ============================================================================

def hash_password(plain: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return _bcrypt.hashpw(plain.encode(), _bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return _bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


# ============================================================================
# JWT Token Management
# ============================================================================
def create_access_token(data: dict, expires_minutes: int = None) -> str:
    """Generate a JWT access token with expiration."""
    to_encode = data.copy()
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or JWT_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expires})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """
    Verify and decode a JWT token.
    Raises JWTError if token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise JWTError("Token missing 'sub' claim")
        return payload
    except JWTError:
        raise


# ============================================================================
# User Authentication (Database-backed)
# ============================================================================
def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """
    Authenticate user credentials against database.
    Returns User object if valid, None otherwise.
    """
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user


def get_user_by_username(db: Session, username: str) -> User | None:
    """Retrieve user by username."""
    return db.query(User).filter(User.username == username).first()


def create_user(db: Session, username: str, email: str, password: str, role: str = "analyst") -> User:
    """
    Create a new user in the database.
    Raises ValueError if username already exists.
    """
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise ValueError(f"Username '{username}' already exists")
    
    new_user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        role=role,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
