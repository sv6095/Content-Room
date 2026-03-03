"""
Database Configuration for ContentOS

Primary: Amazon RDS (PostgreSQL) when AWS_RDS_URL is set.
Fallback: SQLite with async support for local dev / zero-cost deployment.
The active URL is resolved by settings.active_database_url.
"""
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from config import settings

logger = logging.getLogger(__name__)


# Resolve the active database URL:
# - Amazon RDS (PostgreSQL) if AWS_RDS_URL is set  → settings.aws_rds_url
# - SQLite fallback for local dev                  → settings.database_url
_db_url = settings.active_database_url
_is_sqlite = _db_url.startswith("sqlite")

# SQLite requires check_same_thread=False; PostgreSQL does not need it
_connect_args = {"check_same_thread": False} if _is_sqlite else {}

# Create async engine
engine = create_async_engine(
    _db_url,
    echo=settings.debug,
    future=True,
    connect_args=_connect_args,
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


async def init_db() -> None:
    """
    Initialize database tables.
    Creates all tables defined in models.
    """
    async with engine.begin() as conn:
        # Import models to register them
        from models import user, content, schedule
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injection for database sessions.
    
    Yields:
        AsyncSession: Database session for the request
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
