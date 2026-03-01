"""
Schedule Model for ContentOS

Manages scheduled posts and distribution queue.
"""
from datetime import datetime
from typing import Optional
from enum import Enum

from sqlalchemy import String, DateTime, Text, Integer, ForeignKey, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class ScheduleStatus(str, Enum):
    """Scheduled post status values."""
    QUEUED = "queued"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScheduledPost(Base):
    """
    Scheduled post model for content distribution queue.
    
    Attributes:
        id: Primary key
        user_id: Owner of the scheduled post
        content_id: Reference to content
        
        title: Post title
        description: Post description/caption
        
        scheduled_at: When to publish
        published_at: Actual publish time (if published)
        
        platform: Target platform (optional)
        status: Current status
        
        ai_optimized: Whether AI optimized the timing
        original_scheduled_at: Original time before AI optimization
    """
    __tablename__ = "scheduled_posts"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    content_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("contents.id"), 
        nullable=True
    )
    
    # Post Data
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    media_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    
    # Scheduling
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False,
        index=True
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    
    # Platform and Status
    platform: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), 
        default=ScheduleStatus.QUEUED.value
    )
    
    # AI Optimization
    ai_optimized: Mapped[bool] = mapped_column(Boolean, default=False)
    original_scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    
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
        return f"<ScheduledPost(id={self.id}, scheduled_at={self.scheduled_at})>"
