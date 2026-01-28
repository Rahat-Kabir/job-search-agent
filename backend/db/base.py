"""Database configuration and session management."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""

    pass


# Create engine lazily to allow testing without database
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create database engine."""
    global _engine
    if _engine is None:
        if not settings.database_url:
            raise ValueError("DATABASE_URL not configured")
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,  # Test connections before use
            pool_recycle=300,  # Recycle connections after 5 minutes
        )
    return _engine


def get_session_factory():
    """Get or create session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions."""
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    from backend.db import tables  # noqa: F401

    Base.metadata.create_all(bind=get_engine())
