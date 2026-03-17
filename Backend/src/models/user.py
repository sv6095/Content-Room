"""
User Model for ContentOS

Handles user authentication and profile data.
Uses bcrypt for password hashing.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class User(Base):
    """
    User model for authentication and profile management.
    
    Attributes:
        id: Primary key
        email: Unique email address
        name: Display name
        hashed_password: bcrypt-hashed password
        is_active: Account status
        is_verified: Email verification status
        preferred_language: User's preferred language code
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Preferences
    preferred_language: Mapped[Optional[str]] = mapped_column(String(10), default="en")
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"
