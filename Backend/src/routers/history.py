"""
History Router for Content Room

Provides unified history view combining content items and scheduled posts.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from routers.auth import CurrentUser, get_current_user
from services.dynamo_repositories import get_content_repo

logger = logging.getLogger(__name__)
router = APIRouter()


class HistoryItem(BaseModel):
    """Unified history item."""
    id: str
    item_type: str  # 'content' or 'scheduled'
    title: str
    description: Optional[str] = None
    status: str
    platform: Optional[str] = None
    safety_score: Optional[float] = None
    created_at: str
    updated_at: Optional[str] = None


class HistoryResponse(BaseModel):
    """History list response with pagination."""
    items: List[HistoryItem]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class HistoryStats(BaseModel):
    """Statistics for history items."""
    total_content: int
    total_scheduled: int
    published_count: int
    moderated_count: int
    this_week_content: int
    this_week_scheduled: int


@router.get("/", response_model=HistoryResponse)
async def get_user_history(
    item_type: Optional[str] = Query(None, description="Filter by type: 'content' or 'scheduled'"),
    time_range: Optional[str] = Query(None, description="Filter by time: 'today', 'week', 'month'"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Get user's activity history combining content and scheduled posts.
    
    Parameters:
    - item_type: Filter by 'content' or 'scheduled'
    - time_range: Filter by 'today', 'week', or 'month'
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    
    Returns paginated list of history items sorted by creation date (newest first).
    """
    items: List[HistoryItem] = []
    
    # Calculate time filter
    time_filter = None
    if time_range:
        now = datetime.utcnow()
        if time_range == 'today':
            time_filter = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_range == 'week':
            time_filter = now - timedelta(days=7)
        elif time_range == 'month':
            time_filter = now - timedelta(days=30)
    
    repo = get_content_repo()
    content_items = repo.list_for_user(current_user.id, record_type="content")
    schedule_items = repo.list_for_user(current_user.id, record_type="scheduled")

    # Fetch content items
    if not item_type or item_type == 'content':
        for c in content_items:
            created_at = c.get("created_at", "")
            if time_filter and created_at and datetime.fromisoformat(created_at) < time_filter:
                continue
            # Determine workflow status
            status = 'draft'
            if c.get("moderation_status") and c.get("moderation_status") != "pending":
                status = 'moderated'
            if c.get("translated_text"):
                status = 'translated'
            
            original = c.get("original_text")
            title = (
                c.get("caption")
                or c.get("summary")
                or (original[:50] + "..." if original and len(original) > 50 else original)
                or f"Content #{c.get('content_id')}"
            )
            
            items.append(HistoryItem(
                id=c["content_id"],
                item_type='content',
                title=title or f"Content #{c.get('content_id')}",
                description=original[:100] if original else None,
                status=status,
                platform=None,
                safety_score=c.get("safety_score"),
                created_at=created_at,
                updated_at=c.get("updated_at"),
            ))
    
    # Fetch scheduled posts
    if not item_type or item_type == 'scheduled':
        for p in schedule_items:
            created_at = p.get("created_at", "")
            if time_filter and created_at and datetime.fromisoformat(created_at) < time_filter:
                continue
            description = p.get("description")
            items.append(HistoryItem(
                id=p["content_id"],
                item_type='scheduled',
                title=p.get("title", "Scheduled Item"),
                description=description[:100] if description else None,
                status=p.get("status", "queued"),
                platform=p.get("platform"),
                safety_score=None,
                created_at=created_at,
                updated_at=p.get("updated_at"),
            ))
    
    # Sort all items by created_at descending
    items.sort(key=lambda x: x.created_at, reverse=True)
    
    # Calculate pagination
    total_count = len(items)
    total_pages = (total_count + page_size - 1) // page_size
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_items = items[start_idx:end_idx]
    
    return HistoryResponse(
        items=paginated_items,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/stats", response_model=HistoryStats)
async def get_history_stats(
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Get statistics for user's history.
    
    Returns counts for content, scheduled posts, and weekly activity.
    """
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    repo = get_content_repo()
    content_items = repo.list_for_user(current_user.id, record_type="content")
    schedule_items = repo.list_for_user(current_user.id, record_type="scheduled")
    total_content = len(content_items)
    total_scheduled = len(schedule_items)
    published_count = sum(1 for p in schedule_items if p.get("status") == "published")
    moderated_count = sum(1 for c in content_items if c.get("moderation_status") not in (None, "pending"))
    this_week_content = sum(
        1 for c in content_items if c.get("created_at") and datetime.fromisoformat(c["created_at"]) >= week_ago
    )
    this_week_scheduled = sum(
        1 for p in schedule_items if p.get("created_at") and datetime.fromisoformat(p["created_at"]) >= week_ago
    )
    
    return HistoryStats(
        total_content=total_content,
        total_scheduled=total_scheduled,
        published_count=published_count,
        moderated_count=moderated_count,
        this_week_content=this_week_content,
        this_week_scheduled=this_week_scheduled,
    )
