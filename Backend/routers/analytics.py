"""
Analytics Router for ContentOS

Handles performance metrics - AUTH OPTIONAL (uses authenticated user when available).
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import get_db
from models.content import Content, ModerationStatus
from models.schedule import ScheduledPost, ScheduleStatus
from models.user import User
from routers.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


class DashboardMetrics(BaseModel):
    """Dashboard overview metrics."""
    total_content: int
    content_this_week: int
    moderation_safe: int
    moderation_flagged: int
    scheduled_posts: int
    published_posts: int


class ModerationStats(BaseModel):
    """Moderation statistics."""
    total_moderated: int
    safe_count: int
    warning_count: int
    unsafe_count: int
    escalated_count: int
    average_safety_score: float


@router.get("/dashboard", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get dashboard overview metrics.
    Uses authenticated user's ID.
    """
    effective_user_id = current_user.id
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    # Total content
    total_result = await db.execute(
        select(func.count(Content.id)).where(Content.user_id == effective_user_id)
    )
    total_content = total_result.scalar() or 0
    
    # Content this week
    week_result = await db.execute(
        select(func.count(Content.id)).where(
            Content.user_id == effective_user_id,
            Content.created_at >= week_ago,
        )
    )
    content_this_week = week_result.scalar() or 0
    
    # Moderation stats
    safe_result = await db.execute(
        select(func.count(Content.id)).where(
            Content.user_id == effective_user_id,
            Content.moderation_status == ModerationStatus.SAFE.value,
        )
    )
    moderation_safe = safe_result.scalar() or 0
    
    flagged_result = await db.execute(
        select(func.count(Content.id)).where(
            Content.user_id == effective_user_id,
            Content.moderation_status.in_([
                ModerationStatus.WARNING.value,
                ModerationStatus.UNSAFE.value,
            ])
        )
    )
    moderation_flagged = flagged_result.scalar() or 0
    
    # Scheduled posts
    scheduled_query = select(func.count(ScheduledPost.id)).where(
            ScheduledPost.user_id == effective_user_id,
            ScheduledPost.status == ScheduleStatus.QUEUED.value,
        )
    if platform:
        scheduled_query = scheduled_query.where(ScheduledPost.platform == platform)
    
    scheduled_result = await db.execute(scheduled_query)
    scheduled_posts = scheduled_result.scalar() or 0
    
    # Published posts
    published_query = select(func.count(ScheduledPost.id)).where(
            ScheduledPost.user_id == effective_user_id,
            ScheduledPost.status == ScheduleStatus.PUBLISHED.value,
        )
    if platform:
         published_query = published_query.where(ScheduledPost.platform == platform)
    
    published_result = await db.execute(published_query)
    published_posts = published_result.scalar() or 0
    
    return DashboardMetrics(
        total_content=total_content,
        content_this_week=content_this_week,
        moderation_safe=moderation_safe,
        moderation_flagged=moderation_flagged,
        scheduled_posts=scheduled_posts,
        published_posts=published_posts,
    )


@router.get("/moderation", response_model=ModerationStats)
async def get_moderation_stats(
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get moderation statistics.
    Uses authenticated user's ID.
    """
    effective_user_id = current_user.id
    
    # Count by status
    status_counts = {}
    for status in ModerationStatus:
        result = await db.execute(
            select(func.count(Content.id)).where(
                Content.user_id == effective_user_id,
                Content.moderation_status == status.value,
            )
        )
        status_counts[status.value] = result.scalar() or 0
    
    # Average safety score
    avg_result = await db.execute(
        select(func.avg(Content.safety_score)).where(
            Content.user_id == effective_user_id,
            Content.safety_score.isnot(None),
        )
    )
    avg_score = avg_result.scalar() or 0.0
    
    total = sum(status_counts.values())
    
    return ModerationStats(
        total_moderated=total,
        safe_count=status_counts.get(ModerationStatus.SAFE.value, 0),
        warning_count=status_counts.get(ModerationStatus.WARNING.value, 0),
        unsafe_count=status_counts.get(ModerationStatus.UNSAFE.value, 0),
        escalated_count=status_counts.get(ModerationStatus.ESCALATED.value, 0),
        average_safety_score=round(avg_score, 2),
    )


@router.get("/providers")
async def get_provider_stats():
    """
    Get AI provider usage statistics.
    NO AUTHENTICATION REQUIRED.
    """
    from config import settings
    
    return {
        "current_providers": {
            "llm": settings.llm_provider,
            "vision": settings.vision_provider,
            "speech": settings.speech_provider,
            "translation": settings.translation_provider,
        },
        "aws_configured": settings.aws_configured,
        "fallback_chain": {
            "llm": ["aws_bedrock", "grok", "openrouter", "ollama"],
            "vision": ["aws_rekognition", "opencv"],
            "speech": ["aws_transcribe", "whisper"],
            "translation": ["aws_translate", "google_free"],
        }
    }
