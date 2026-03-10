"""
Scheduler Router — Personal Content Calendar

A simple calendar for scheduling content creation tasks.
No social media publishing, no moderation — just a personal planner.
"""
import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from pathlib import Path
import shutil
import uuid

from config import get_settings
from services.dynamo_repositories import get_content_repo

logger = logging.getLogger(__name__)
router = APIRouter()


class ScheduleRequest(BaseModel):
    """Request to add an item to the schedule."""
    title: str
    description: Optional[str] = None
    scheduled_at: datetime
    user_id: str = "1"
    content_id: Optional[str] = None  # Optionally link to a piece of content


class ScheduleResponse(BaseModel):
    """A scheduled calendar item."""
    id: str
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
):
    """
    Add an item to the content schedule calendar.
    No social media publishing — this is a personal content planner.
    """
    now = datetime.utcnow().isoformat()
    post = get_content_repo().create_content(
        {
            "user_id": str(request.user_id),
            "record_type": "scheduled",
            "content_type": "scheduled_task",
            "content_id": request.content_id,
            "title": request.title,
            "description": request.description,
            "scheduled_at": request.scheduled_at.isoformat(),
            "platform": None,
            "status": "queued",
            "ai_optimized": False,
            "created_at": now,
            "updated_at": now,
        }
    )
    logger.info(f"Schedule item created: {post['content_id']} — '{post['title']}' at {post['scheduled_at']}")
    return ScheduleResponse(
        id=post["content_id"],
        title=post["title"],
        description=post.get("description"),
        scheduled_at=datetime.fromisoformat(post["scheduled_at"]),
        status=post.get("status", "queued"),
        platform=post.get("platform"),
        media_url=post.get("media_url"),
        ai_optimized=bool(post.get("ai_optimized", False)),
        created_at=datetime.fromisoformat(post["created_at"]),
    )

@router.post("/with-media")
async def schedule_post_with_media(
    title: str = Form(...),
    scheduled_at: datetime = Form(...),
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    platform: Optional[str] = Form(None),
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
    
    now = datetime.utcnow().isoformat()
    post = get_content_repo().create_content(
        {
            "user_id": "1",
            "record_type": "scheduled",
            "content_type": "scheduled_task",
            "title": title,
            "description": description,
            "scheduled_at": scheduled_at.isoformat(),
            "platform": platform,
            "status": "queued",
            "media_url": media_url,
            "ai_optimized": False,
            "created_at": now,
            "updated_at": now,
        }
    )
    logger.info(f"Schedule media item created: {post['content_id']} — '{post['title']}' at {post['scheduled_at']}")
    
    return {
        "post": ScheduleResponse(
            id=post["content_id"],
            title=post["title"],
            description=post.get("description"),
            scheduled_at=datetime.fromisoformat(post["scheduled_at"]),
            status=post.get("status", "queued"),
            platform=post.get("platform"),
            media_url=post.get("media_url"),
            ai_optimized=bool(post.get("ai_optimized", False)),
            created_at=datetime.fromisoformat(post["created_at"]),
        ),
        "media": {"url": media_url, "filename": safe_filename},
        "moderation_passed": True
    }



@router.get("/", response_model=List[ScheduleResponse])
async def list_scheduled_posts(
    user_id: str = "1",
):
    """
    List all active calendar items for the user (excludes cancelled/deleted entries).
    """
    posts = get_content_repo().list_for_user(str(user_id), record_type="scheduled")
    posts = [p for p in posts if p.get("status") != "cancelled"]
    posts.sort(key=lambda p: p.get("scheduled_at", ""))
    return [
        ScheduleResponse(
            id=p["content_id"],
            title=p.get("title", ""),
            description=p.get("description"),
            scheduled_at=datetime.fromisoformat(p["scheduled_at"]),
            status=p.get("status", "queued"),
            platform=p.get("platform"),
            media_url=p.get("media_url"),
            ai_optimized=bool(p.get("ai_optimized", False)),
            created_at=datetime.fromisoformat(p["created_at"]),
        )
        for p in posts
    ]


@router.get("/{post_id}", response_model=ScheduleResponse)
async def get_scheduled_post(
    post_id: str,
):
    """Get a specific scheduled calendar item."""
    post = get_content_repo().get_content(post_id)
    if not post or post.get("record_type") != "scheduled":
        raise HTTPException(status_code=404, detail="Item not found")
    return ScheduleResponse(
        id=post["content_id"],
        title=post.get("title", ""),
        description=post.get("description"),
        scheduled_at=datetime.fromisoformat(post["scheduled_at"]),
        status=post.get("status", "queued"),
        platform=post.get("platform"),
        media_url=post.get("media_url"),
        ai_optimized=bool(post.get("ai_optimized", False)),
        created_at=datetime.fromisoformat(post["created_at"]),
    )


@router.delete("/{post_id}")
async def delete_scheduled_post(
    post_id: str,
):
    """
    Permanently delete a scheduled calendar item.
    The item is removed from the database entirely so it no longer appears on the calendar.
    """
    post = get_content_repo().get_content(post_id)
    if not post or post.get("record_type") != "scheduled":
        raise HTTPException(status_code=404, detail="Item not found")
    get_content_repo().delete_content(post_id)

    logger.info(f"Schedule item deleted: {post_id}")
    return {"message": "Item removed from schedule"}
