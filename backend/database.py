"""
Database configuration and session management.
Uses SQLAlchemy with SQLite for Phase 1, upgradeable to PostgreSQL.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATASET_DIR

# ============================================================================
# Database URL Configuration
# ============================================================================
# Phase 1: SQLite for simplicity
# Production: Upgrade to PostgreSQL with psycopg2
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(DATASET_DIR, 'app.db')}"
)

# ============================================================================
# SQLAlchemy Engine & Session
# ============================================================================
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=os.getenv("SQL_ECHO", "false").lower() == "true"
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ============================================================================
# Database Dependency Injection
# ============================================================================
def get_db():
    """FastAPI dependency to provide database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# Initialize Database
# ============================================================================
def init_db():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)
