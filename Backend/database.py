"""
Database Configuration for ContentOS

Primary: Amazon RDS (PostgreSQL) when AWS_RDS_URL is set.
Fallback: SQLite with async support for local dev / zero-cost deployment.
The active URL is resolved by settings.active_database_url.
"""
import logging
from typing import AsyncGenerator

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from config import settings

logger = logging.getLogger(__name__)
DEFAULT_ADMIN_EMAIL = "admin@contentroom.local"
LEGACY_ADMIN_EMAIL = "admin"


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
    await ensure_default_admin_user()


async def ensure_default_admin_user() -> None:
    """
    Ensure a default admin user exists for local login.
    Creates/refreshes email: admin@contentroom.local / password: shan.
    """
    from models.user import User

    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.email.in_([DEFAULT_ADMIN_EMAIL, LEGACY_ADMIN_EMAIL]))
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            existing_user.email = DEFAULT_ADMIN_EMAIL
            existing_user.hashed_password = bcrypt.hashpw(
                b"shan",
                bcrypt.gensalt(),
            ).decode("utf-8")
            existing_user.is_active = True
            existing_user.is_verified = True
            if not existing_user.name:
                existing_user.name = "Admin"
            await session.commit()
            logger.info("Default admin credentials refreshed")
            return

        default_user = User(
            name="Admin",
            email=DEFAULT_ADMIN_EMAIL,
            hashed_password=bcrypt.hashpw(
                b"shan",
                bcrypt.gensalt(),
            ).decode("utf-8"),
            is_active=True,
            is_verified=True,
        )
        session.add(default_user)
        await session.commit()
        logger.info("Default admin user created")


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
