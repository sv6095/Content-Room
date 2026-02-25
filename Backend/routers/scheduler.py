"""
Scheduler Router — Personal Content Calendar

A simple calendar for scheduling content creation tasks.
No social media publishing, no moderation — just a personal planner.
"""
import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from database import get_db
from models.schedule import ScheduledPost, ScheduleStatus

logger = logging.getLogger(__name__)
router = APIRouter()


class ScheduleRequest(BaseModel):
    """Request to add an item to the schedule."""
    title: str
    description: Optional[str] = None
    scheduled_at: datetime
    user_id: int = 1
    content_id: Optional[int] = None  # Optionally link to a piece of content


class ScheduleResponse(BaseModel):
    """A scheduled calendar item."""
    id: int
    title: str
    description: Optional[str]
    scheduled_at: datetime
    status: str
    platform: Optional[str] = None  # kept for DB compatibility, always None
    ai_optimized: bool
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/", response_model=ScheduleResponse)
async def schedule_post(
    request: ScheduleRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Add an item to the content schedule calendar.
    No social media publishing — this is a personal content planner.
    """
    post = ScheduledPost(
        user_id=request.user_id,
        content_id=request.content_id,
        title=request.title,
        description=request.description,
        scheduled_at=request.scheduled_at,
        platform=None,  # not used
        status=ScheduleStatus.QUEUED.value,
    )

    db.add(post)
    await db.commit()
    await db.refresh(post)

    logger.info(f"Schedule item created: {post.id} — '{post.title}' at {post.scheduled_at}")
    return ScheduleResponse.model_validate(post)


@router.get("/", response_model=List[ScheduleResponse])
async def list_scheduled_posts(
    user_id: int = 1,
    db: AsyncSession = Depends(get_db),
):
    """
    List all active calendar items for the user (excludes cancelled/deleted entries).
    """
    query = (
        select(ScheduledPost)
        .where(
            ScheduledPost.user_id == user_id,
            ScheduledPost.status != ScheduleStatus.CANCELLED.value,
        )
        .order_by(ScheduledPost.scheduled_at)
    )
    result = await db.execute(query)
    posts = result.scalars().all()
    return [ScheduleResponse.model_validate(p) for p in posts]


@router.get("/{post_id}", response_model=ScheduleResponse)
async def get_scheduled_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific scheduled calendar item."""
    result = await db.execute(
        select(ScheduledPost).where(ScheduledPost.id == post_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Item not found")
    return ScheduleResponse.model_validate(post)


@router.delete("/{post_id}")
async def delete_scheduled_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Permanently delete a scheduled calendar item.
    The item is removed from the database entirely so it no longer appears on the calendar.
    """
    result = await db.execute(
        select(ScheduledPost).where(ScheduledPost.id == post_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Item not found")

    await db.execute(delete(ScheduledPost).where(ScheduledPost.id == post_id))
    await db.commit()

    logger.info(f"Schedule item deleted: {post_id}")
    return {"message": "Item removed from schedule"}
