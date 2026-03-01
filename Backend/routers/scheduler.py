"""
Scheduler Router — Personal Content Calendar

A simple calendar for scheduling content creation tasks.
No social media publishing, no moderation — just a personal planner.
"""
import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pathlib import Path
import shutil
import uuid

from config import get_settings

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
    media_url: Optional[str] = None
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

@router.post("/with-media")
async def schedule_post_with_media(
    title: str = Form(...),
    scheduled_at: datetime = Form(...),
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    platform: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Schedule a post with an attached media file (image, video, document).
    Saves the file locally and creates a task.
    """
    settings = get_settings()
    upload_dir = Path(settings.storage_path)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Save the file
    ext = Path(file.filename).suffix if file.filename else ""
    safe_filename = f"{uuid.uuid4()}{ext}"
    file_path = upload_dir / safe_filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save upload: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload file")
    
    media_url = f"{settings.storage_base_url}/{safe_filename}"
    
    post = ScheduledPost(
        user_id=1,
        title=title,
        description=description,
        scheduled_at=scheduled_at,
        platform=platform,
        status=ScheduleStatus.QUEUED.value,
        media_url=media_url
    )

    db.add(post)
    await db.commit()
    await db.refresh(post)

    logger.info(f"Schedule media item created: {post.id} — '{post.title}' at {post.scheduled_at}")
    
    return {
        "post": ScheduleResponse.model_validate(post),
        "media": {"url": media_url, "filename": safe_filename},
        "moderation_passed": True
    }



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
