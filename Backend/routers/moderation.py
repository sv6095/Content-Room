"""
Moderation Router for ContentOS

Handles multimodal content moderation - NO AUTH REQUIRED.
- Text moderation
- Image moderation
- Audio moderation
- Video moderation (frame extraction + per-frame analysis)

Now saves results to database for analytics tracking.
"""
import logging
import hashlib
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pydantic import BaseModel

from services.moderation_service import get_moderation_service
from routers.auth import CurrentUser, get_current_user_optional
from services.dynamo_repositories import get_content_repo, get_moderation_cache_repo

logger = logging.getLogger(__name__)
router = APIRouter()

moderation = get_moderation_service()


class TextModerationRequest(BaseModel):
    """Request for text moderation."""
    text: str
    language: str = "en"
    save_to_db: bool = True  # Whether to save for analytics


class ModerationResponse(BaseModel):
    """Standard moderation response."""
    decision: str
    explanation: str  # LLM-generated explanation of what and why is flagged
    flagged_content: str  # Summary of problematic content
    flags: list
    provider: str
    processing_time_ms: int


def get_moderation_status(decision: str) -> str:
    """Convert moderation decision to ModerationStatus enum value."""
    if decision == "ESCALATE":
        return "escalated"
    elif decision == "FLAG":
        return "unsafe"
    return "safe"


def _safe_score(value: object, default: float = 100.0) -> float:
    """Best-effort numeric safety score conversion for mixed provider payloads."""
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


@router.post("/text", response_model=ModerationResponse)
async def moderate_text(
    request: TextModerationRequest,
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """
    Moderate text content for safety.
    Uses AWS Comprehend with LLM fallback.
    NO AUTHENTICATION REQUIRED.
    Saves results to database for analytics.
    """
    try:
        normalized_text = (request.text or "").strip()
        if not normalized_text:
            raise HTTPException(status_code=400, detail="Text content is required for text moderation.")

        cache_repo = get_moderation_cache_repo()
        text_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
        cached = cache_repo.get(text_hash)
        result = cached.get("result") if cached and cached.get("result") else None
        if not result:
            result = await moderation.moderate_text(normalized_text)
            cache_repo.put(text_hash, {"result": result, "flagged": result["decision"] != "ALLOW"})
        
        # Save to database for analytics (uses authenticated user if available)
        if request.save_to_db:
            try:
                get_content_repo().create_content(
                    {
                        "user_id": current_user.id if current_user else "anonymous",
                        "record_type": "content",
                        "status": "moderated",
                        "content_type": "text",
                        "original_text": normalized_text[:500],
                        "moderation_status": get_moderation_status(result["decision"]),
                        "safety_score": result.get("safety_score", 100),
                        "moderation_flags": result.get("flags", []),
                        "moderation_explanation": result.get("explanation"),
                    }
                )
            except Exception as db_error:
                logger.warning(f"Failed to save moderation to DB: {db_error}")
        
        return ModerationResponse(
            decision=result["decision"],
            explanation=result.get("explanation", "No issues detected."),
            flagged_content=result.get("flagged_content", ""),
            flags=result.get("flags", []),
            provider=result.get("provider", "unknown"),
            processing_time_ms=result.get("processing_time_ms", 0),
        )
    except Exception as e:
        logger.error(f"Text moderation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/image")
async def moderate_image(
    image: UploadFile = File(...),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """
    Moderate image content for safety.
    Uses AWS Rekognition with OpenCV fallback.
    NO AUTHENTICATION REQUIRED.
    Saves results to database for analytics.
    """
    try:
        image_bytes = await image.read()
        image_hash = hashlib.sha256(image_bytes).hexdigest()
        cache_repo = get_moderation_cache_repo()
        cached = cache_repo.get(image_hash)
        result = cached.get("result") if cached and cached.get("result") else None
        if not result:
            result = await moderation.moderate_image(image_bytes)
            cache_repo.put(image_hash, {"result": result, "flagged": result["decision"] != "ALLOW"})
        
        # Save to database for analytics
        try:
            get_content_repo().create_content(
                {
                    "user_id": current_user.id if current_user else "anonymous",
                    "record_type": "content",
                    "status": "moderated",
                    "content_type": "image",
                    "original_text": f"Image: {image.filename}",
                    "moderation_status": get_moderation_status(result["decision"]),
                    "safety_score": result.get("safety_score", 100),
                    "moderation_flags": result.get("flags", []),
                }
            )
        except Exception as db_error:
            logger.warning(f"Failed to save moderation to DB: {db_error}")
        
        return {
            "filename": image.filename,
            **result,
        }
    except Exception as e:
        logger.error(f"Image moderation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/audio")
async def moderate_audio(
    audio: UploadFile = File(...),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """
    Moderate audio content for safety.
    Transcribes audio and analyzes content.
    Uses Whisper + LLM for analysis.
    NO AUTHENTICATION REQUIRED.
    """
    try:
        audio_bytes = await audio.read()
        result = await moderation.moderate_audio(audio_bytes, audio.filename)
        
        # Save to database for analytics
        try:
            get_content_repo().create_content(
                {
                    "user_id": current_user.id if current_user else "anonymous",
                    "record_type": "content",
                    "status": "moderated",
                    "content_type": "audio",
                    "original_text": f"Audio: {audio.filename}",
                    "moderation_status": get_moderation_status(result["decision"]),
                    "safety_score": result.get("safety_score", 100),
                    "moderation_flags": result.get("flags", []),
                }
            )
        except Exception as db_error:
            logger.warning(f"Failed to save moderation to DB: {db_error}")
        
        return {
            "filename": audio.filename,
            **result,
        }
    except Exception as e:
        logger.error(f"Audio moderation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/video")
async def moderate_video(
    video: UploadFile = File(...),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """
    Moderate video content for safety.
    Extracts frames and analyzes them for moderation.
    NO AUTHENTICATION REQUIRED.
    """
    try:
        video_bytes = await video.read()
        result = await moderation.moderate_video(video_bytes)

        # Save to database for analytics
        try:
            get_content_repo().create_content(
                {
                    "user_id": current_user.id if current_user else "anonymous",
                    "record_type": "content",
                    "status": "moderated",
                    "content_type": "video",
                    "original_text": f"Video: {video.filename}",
                    "moderation_status": get_moderation_status(result["decision"]),
                    "safety_score": result.get("safety_score", 100),
                    "moderation_flags": result.get("flags", []),
                    "moderation_explanation": result.get("explanation"),
                }
            )
        except Exception as db_error:
            logger.warning(f"Failed to save video moderation to DB: {db_error}")

        return {
            "filename": video.filename,
            **result,
        }
    except Exception as e:
        logger.error(f"Video moderation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/multimodal")
async def moderate_multimodal(
    text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
):
    """
    Moderate multiple content types at once.
    Combines results from all provided content types.
    NO AUTHENTICATION REQUIRED.
    """
    results = {}
    overall_safety = 100
    all_flags = []
    normalized_text = (text or "").strip()
    
    if normalized_text:
        text_result = await moderation.moderate_text(normalized_text)
        results["text"] = text_result
        overall_safety = min(overall_safety, _safe_score(text_result.get("safety_score")))
        all_flags.extend(text_result.get("flags", []))
    
    if image:
        image_bytes = await image.read()
        image_result = await moderation.moderate_image(image_bytes)
        results["image"] = image_result
        overall_safety = min(overall_safety, _safe_score(image_result.get("safety_score")))
        all_flags.extend(image_result.get("flags", []))
    
    if audio:
        audio_bytes = await audio.read()
        audio_result = await moderation.moderate_audio(audio_bytes, audio.filename)
        results["audio"] = audio_result
        overall_safety = min(overall_safety, _safe_score(audio_result.get("safety_score")))
        all_flags.extend(audio_result.get("flags", []))
    
    if not results:
        raise HTTPException(
            status_code=400,
            detail="At least one content type (text, image, or audio) is required"
        )
    
    # Combined decision
    if overall_safety >= 70:
        decision = "ALLOW"
    elif overall_safety >= 40:
        decision = "FLAG"
    else:
        decision = "ESCALATE"
    
    return {
        "decision": decision,
        "overall_safety_score": overall_safety,
        "combined_flags": list(set(all_flags)),
        "results": results,
    }
