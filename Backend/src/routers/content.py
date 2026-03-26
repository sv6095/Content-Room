"""
Content Router for Content Room

My Content pipeline: list, get, create draft.
Supports workflow: Create -> Moderate -> Translate -> Schedule.
"""
import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from routers.auth import CurrentUser, get_current_user
from services.dynamo_repositories import get_content_repo
from services.storage_service import (
    StorageError,
    get_storage_service,
    parse_s3_bucket_and_key,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ContentCreate(BaseModel):
    """Create a content draft (from Studio or first step)."""
    content_type: str = Field(default="text", description="text, image, audio, video")
    original_text: Optional[str] = None
    caption: Optional[str] = None
    summary: Optional[str] = None
    hashtags: Optional[List[str]] = None
    file_path: Optional[str] = None


class ContentItem(BaseModel):
    """Single content item for list/detail."""
    id: str
    content_type: str
    original_text: Optional[str] = None
    caption: Optional[str] = None
    summary: Optional[str] = None
    hashtags: Optional[dict | List[str]] = None
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    translated_text: Optional[str] = None
    source_language: Optional[str] = None
    target_language: Optional[str] = None
    moderation_status: str
    safety_score: Optional[float] = None
    moderation_explanation: Optional[str] = None
    workflow_status: str  # draft | moderated | translated | scheduled
    is_scheduled: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


def _workflow_status(content: dict, is_scheduled: bool) -> str:
    if is_scheduled:
        return "scheduled"
    if content.get("translated_text"):
        return "translated"
    if content.get("moderation_status") and content.get("moderation_status") != "pending" and content.get("safety_score") is not None:
        return "moderated"
    return "draft"


async def _resolve_accessible_file_url(file_path: Optional[str]) -> Optional[str]:
    """
    Private S3 objects need presigned URLs. Uses bucket+key from the stored
    reference (including path-style HTTPS URLs and alternate output buckets).
    """
    if not file_path:
        return None

    raw = file_path.strip()
    if not raw:
        return None

    if parse_s3_bucket_and_key(raw):
        try:
            storage = get_storage_service()
            return await storage.get_presigned_url_for_file_reference(
                raw, expires_in=24 * 60 * 60
            )
        except StorageError as e:
            logger.warning("Could not presign file reference: %s", e)
            return None
        except Exception as e:
            logger.warning("Unexpected error presigning file URL: %s", e)
            return None

    return raw


# ---------------------------------------------------------------------------
# List & Get
# ---------------------------------------------------------------------------

@router.get("/", response_model=List[ContentItem])
async def list_content(
    status_filter: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    List current user's content (My Content).
    Optional ?status_filter=draft|moderated|translated|scheduled.
    """
    repo = get_content_repo()
    contents = repo.list_for_user(current_user.id, record_type="content")
    schedules = repo.list_for_user(current_user.id, record_type="scheduled")
    scheduled_ids = {s.get("content_id") for s in schedules if s.get("content_id")}

    out = []
    for c in contents:
        is_sched = c.get("content_id") in scheduled_ids
        ws = _workflow_status(c, is_sched)
        if status_filter and ws != status_filter:
            continue
        created_at = c.get("created_at", "")
        updated_at = c.get("updated_at", created_at)
        out.append(ContentItem(
            id=c["content_id"],
            content_type=c.get("content_type", "text"),
            original_text=c.get("original_text"),
            caption=c.get("caption"),
            summary=c.get("summary"),
            hashtags=c.get("hashtags"),
            file_path=c.get("file_path"),
            file_url=await _resolve_accessible_file_url(c.get("file_path")),
            translated_text=c.get("translated_text"),
            source_language=c.get("source_language"),
            target_language=c.get("target_language"),
            moderation_status=c.get("moderation_status", "pending"),
            safety_score=c.get("safety_score"),
            moderation_explanation=c.get("moderation_explanation"),
            workflow_status=ws,
            is_scheduled=is_sched,
            created_at=created_at,
            updated_at=updated_at,
        ))
    return out


@router.get("/{content_id}", response_model=ContentItem)
async def get_content(
    content_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get one content item (own only)."""
    repo = get_content_repo()
    content = repo.get_content(content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    if content.get("user_id") != current_user.id or content.get("record_type") != "content":
        raise HTTPException(status_code=404, detail="Content not found")

    # Check if scheduled
    schedules = repo.list_for_user(current_user.id, record_type="scheduled")
    is_scheduled = any(p.get("content_id") == content_id for p in schedules)

    return ContentItem(
        id=content["content_id"],
        content_type=content.get("content_type", "text"),
        original_text=content.get("original_text"),
        caption=content.get("caption"),
        summary=content.get("summary"),
        hashtags=content.get("hashtags"),
        file_path=content.get("file_path"),
        file_url=await _resolve_accessible_file_url(content.get("file_path")),
        translated_text=content.get("translated_text"),
        source_language=content.get("source_language"),
        target_language=content.get("target_language"),
        moderation_status=content.get("moderation_status", "pending"),
        safety_score=content.get("safety_score"),
        moderation_explanation=content.get("moderation_explanation"),
        workflow_status=_workflow_status(content, is_scheduled),
        is_scheduled=is_scheduled,
        created_at=content.get("created_at", ""),
        updated_at=content.get("updated_at", ""),
    )


# ---------------------------------------------------------------------------
# Create draft
# ---------------------------------------------------------------------------

@router.post("/", response_model=ContentItem, status_code=status.HTTP_201_CREATED)
async def create_content(
    body: ContentCreate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Create a content draft (e.g. from Studio after generating caption/summary/hashtags).
    Starts the pipeline: Create -> Moderate -> Translate -> Schedule.
    """
    hashtags_json = None
    if body.hashtags is not None:
        hashtags_json = {"items": body.hashtags} if isinstance(body.hashtags, list) else body.hashtags

    content = get_content_repo().create_content(
        {
            "user_id": current_user.id,
            "record_type": "content",
            "content_type": body.content_type or "text",
            "original_text": body.original_text,
            "caption": body.caption,
            "summary": body.summary,
            "hashtags": hashtags_json,
            "file_path": body.file_path,
            "moderation_status": "pending",
            "status": "draft",
            "created_at": datetime.utcnow().isoformat(),
        }
    )

    return ContentItem(
        id=content["content_id"],
        content_type=content.get("content_type", "text"),
        original_text=content.get("original_text"),
        caption=content.get("caption"),
        summary=content.get("summary"),
        hashtags=content.get("hashtags"),
        file_path=content.get("file_path"),
        file_url=await _resolve_accessible_file_url(content.get("file_path")),
        translated_text=content.get("translated_text"),
        source_language=content.get("source_language"),
        target_language=content.get("target_language"),
        moderation_status=content.get("moderation_status", "pending"),
        safety_score=content.get("safety_score"),
        moderation_explanation=content.get("moderation_explanation"),
        workflow_status="draft",
        is_scheduled=False,
        created_at=content.get("created_at", ""),
        updated_at=content.get("updated_at", ""),
    )
