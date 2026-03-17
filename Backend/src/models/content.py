"""
Content Model for ContentOS

Stores generated content, moderation results, and metadata.
"""
from datetime import datetime
from typing import Optional
from enum import Enum

from sqlalchemy import String, DateTime, Text, Integer, Float, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class ContentType(str, Enum):
    """Supported content types."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"


class ModerationStatus(str, Enum):
    """Moderation status values."""
    PENDING = "pending"
    SAFE = "safe"
    WARNING = "warning"
    UNSAFE = "unsafe"
    ESCALATED = "escalated"


class Content(Base):
    """
    Content model for storing created and moderated content.
    
    Attributes:
        id: Primary key
        user_id: Owner of the content
        content_type: Type of content (text, image, audio, video)
        original_text: Original text input
        file_path: Path to uploaded file (if any)
        
        # AI Generated Fields
        caption: AI-generated caption
        summary: AI-generated summary
        hashtags: AI-generated hashtags (JSON array)
        translated_text: Translated version
        source_language: Detected source language
        target_language: Translation target language
        
        # Moderation Results
        moderation_status: Current moderation status
        safety_score: 0-100 safety score
        moderation_flags: Detected issues (JSON array)
        moderation_explanation: AI explanation
        
        # Engagement Prediction
        predicted_engagement: Predicted engagement score
        recommended_post_time: AI-recommended posting time
        
        # Timestamps
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = "contents"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    
    # Content Data
    content_type: Mapped[str] = mapped_column(String(20), nullable=False)
    original_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # AI Generated Fields
    caption: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hashtags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Translation
    translated_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    target_language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    
    # Moderation Results
    moderation_status: Mapped[str] = mapped_column(
        String(20), 
        default=ModerationStatus.PENDING.value
    )
    safety_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    moderation_flags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    moderation_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Engagement Prediction
    predicted_engagement: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recommended_post_time: Mapped[Optional[datetime]] = mapped_column(
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
        return f"<Content(id={self.id}, type={self.content_type})>"
