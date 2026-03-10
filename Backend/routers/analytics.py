"""
Analytics Router for ContentOS

Handles performance metrics - AUTH OPTIONAL (uses authenticated user when available).
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from routers.auth import CurrentUser, get_current_user
from services.dynamo_repositories import get_content_repo

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
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Get dashboard overview metrics.
    Uses authenticated user's ID.
    """
    week_ago = datetime.utcnow() - timedelta(days=7)
    repo = get_content_repo()
    content_items = repo.list_for_user(current_user.id, record_type="content")
    schedule_items = repo.list_for_user(current_user.id, record_type="scheduled")

    total_content = len(content_items)
    content_this_week = sum(
        1
        for c in content_items
        if c.get("created_at") and datetime.fromisoformat(c["created_at"]) >= week_ago
    )
    moderation_safe = sum(1 for c in content_items if c.get("moderation_status") == "safe")
    moderation_flagged = sum(1 for c in content_items if c.get("moderation_status") in {"warning", "unsafe"})

    if platform:
        schedule_items = [s for s in schedule_items if s.get("platform") == platform]
    scheduled_posts = sum(1 for s in schedule_items if s.get("status") == "queued")
    published_posts = sum(1 for s in schedule_items if s.get("status") == "published")
    
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
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Get moderation statistics.
    Uses authenticated user's ID.
    """
    content_items = get_content_repo().list_for_user(current_user.id, record_type="content")
    if platform:
        content_items = [c for c in content_items if c.get("platform") == platform]
    status_counts = {
        "safe": sum(1 for c in content_items if c.get("moderation_status") == "safe"),
        "warning": sum(1 for c in content_items if c.get("moderation_status") == "warning"),
        "unsafe": sum(1 for c in content_items if c.get("moderation_status") == "unsafe"),
        "escalated": sum(1 for c in content_items if c.get("moderation_status") == "escalated"),
        "pending": sum(1 for c in content_items if c.get("moderation_status") in (None, "pending")),
    }
    scores = [float(c["safety_score"]) for c in content_items if c.get("safety_score") is not None]
    avg_score = (sum(scores) / len(scores)) if scores else 0.0
    
    total = sum(status_counts.values())
    
    return ModerationStats(
        total_moderated=total,
        safe_count=status_counts.get("safe", 0),
        warning_count=status_counts.get("warning", 0),
        unsafe_count=status_counts.get("unsafe", 0),
        escalated_count=status_counts.get("escalated", 0),
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
        "scheduler_mode": "infra_eventbridge_rule_plus_local_calendar",
        "scheduler_runtime_client_initialized": False,
        "aws_service_alignment_doc": "/Backend/AWS_SERVICE_ALIGNMENT.md",
        "fallback_chain": {
            "llm": ["aws_bedrock", "grok", "openrouter", "ollama"],
            "vision": ["aws_rekognition", "simple_fallback"],
            "speech": ["aws_transcribe", "whisper"],
            "translation": ["aws_translate", "google_free"],
        },
        "services_initialized_in_code": [
            "bedrock-runtime",
            "rekognition",
            "comprehend",
            "translate",
            "transcribe",
            "dynamodb",
            "s3",
            "stepfunctions",
        ],
        "services_infra_managed": [
            "apigateway",
            "lambda",
            "eventbridge",
            "cloudwatch",
            "xray",
            "cloudfront",
        ],
    }
