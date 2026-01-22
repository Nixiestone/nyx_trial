"""
Database Configuration and Session Management
Author: BLESSING OMOREGIE
Location: config/database.py
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool
from config.settings import settings
from src.database.models import Base

# Create engine based on settings
def get_engine():
    """Create and return database engine."""
    
    # For SQLite, use StaticPool to avoid threading issues
    if settings.DATABASE_URL.startswith('sqlite'):
        engine = create_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            connect_args={'check_same_thread': False},
            poolclass=StaticPool
        )
    else:
        # For other databases (PostgreSQL, MySQL, etc.)
        engine = create_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20
        )
    
    return engine


# Create engine
engine = get_engine()

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create scoped session for thread safety
ScopedSession = scoped_session(SessionLocal)


def init_database():
    """Initialize database - create all tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    Get database session.
    Use this for dependency injection in FastAPI or similar.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    """
    Get a database session for direct use.
    Remember to close it when done.
    """
    return SessionLocal()


# Initialize database on import (optional)
if __name__ == "__main__":
    print("Initializing database...")
    init_database()
    print("Database initialized successfully!")