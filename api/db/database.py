"""
Database connection and session management.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from api.core.config import settings

# from api.core.tracing import trace_function  # Removed to avoid conflicts

# Lazy initialization - only create engine when first needed
_engine = None
_SessionLocal = None


def get_engine():
    """Get database engine, creating it if necessary."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.DATABASE_URL,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_POOL_MAX_OVERFLOW,
            pool_pre_ping=True,
            pool_recycle=settings.DATABASE_POOL_RECYCLE,
            # Never use echo - it bypasses logging configuration and outputs directly to stdout
            # Use logging levels instead via app/core/logging.py configuration
            echo=False,
        )
    return _engine


def get_session_local():
    """Get session maker, creating it if necessary."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=get_engine()
        )
    return _SessionLocal


Base = declarative_base()


def get_db():
    """Dependency to get database session."""
    db = get_session_local()()
    try:
        yield db
    finally:
        db.close()
