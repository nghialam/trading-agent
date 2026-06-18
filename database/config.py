"""
Database Configuration
PostgreSQL connection and SQLAlchemy setup
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


# Database configuration from environment variables
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://trading_user:trading_pass@localhost:5432/trading_agent"
)

# Create engine with connection pool
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False  # Set True for SQL debugging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency injector for database sessions.
    Yields a session and ensures proper cleanup.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database schema"""
      # Import all models to ensure they're registered with SQLAlchemy
    from database.models import SignalReview, DailySummary, PocketPivotData  # noqa: F401
    
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully")
