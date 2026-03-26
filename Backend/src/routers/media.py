"""
Media Router for ContentOS

Handles file uploads with S3 → Firebase → Local fallback.
"""
import logging
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Depends
from pydantic import BaseModel

from routers.auth import CurrentUser, get_current_user_optional
from services.dynamo_repositories import get_users_repo
from services.storage_service import get_storage_service, UploadError
from services.motion_video_service import get_motion_video_service, MotionVideoError
from services.image_generation_service import get_image_generation_service, ImageGenerationError

logger = logging.getLogger(__name__)
router = APIRouter()


class UploadResponse(BaseModel):
    """Response for file upload."""
    success: bool
    url: str
    key: str
    provider: str
    size: int
    content_type: str


class StorageStatusResponse(BaseModel):
    """Response for storage status."""
    providers: dict


class PresignedUploadRequest(BaseModel):
    filename: str
    content_type: str
    folder: str = "uploads"


class NovaReelRequest(BaseModel):
    prompt: str
    duration_seconds: int = 6
    aspect_ratio: str = "16:9"


class ImageGenerationRequest(BaseModel):
    prompt: str
    engine: str = "titan"  # titan | nova_canvas
    width: int = 1024
    height: int = 1024


def _consume_best_tier_nova_quota_or_raise(current_user: Optional[CurrentUser]) -> None:
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Login is required for Best-tier Nova generation",
        )
    users_repo = get_users_repo()
    allowed = users_repo.consume_high_cost_nova_usage_once(current_user.id)
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="Best-tier Nova features can be used only once per user in Creator Studio",
        )


def _consume_modality_quota_or_raise(
    current_user: Optional[CurrentUser],
    modality: str,
    limit: int = 3,
) -> None:
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail=f"Login is required for {modality} actions",
        )
    users_repo = get_users_repo()
    allowed = users_repo.consume_feature_usage(
        user_id=current_user.id,
        feature=f"{modality}_generation",
        limit=limit,
    )
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"{modality.capitalize()} actions are limited to {limit} per user in Creator Studio",
        )


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    folder: str = Form(default="uploads"),
    preferred_provider: Optional[str] = Form(default=None),
):
    """
    Upload a file to storage.
    
    Files are stored using the priority: S3 → Firebase → Local.
    
    Args:
        file: The file to upload
        folder: Folder to store in (default: "uploads")
        preferred_provider: Optionally specify "s3", "firebase", or "local"
    
    Returns:
        Upload result with URL and metadata
    """
    storage = get_storage_service()
    
    try:
        # Read file contents
        file_data = await file.read()
        
        if not file_data:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # Validate file size (max 50MB)
        max_size = 50 * 1024 * 1024
        if len(file_data) > max_size:
            raise HTTPException(status_code=413, detail="File too large (max 50MB)")
        
        # Upload
        result = await storage.upload(
            file_data=file_data,
            filename=file.filename or "unnamed",
            content_type=file.content_type,
            folder=folder,
            preferred_provider=preferred_provider,
        )
        
        return UploadResponse(
            success=True,
            url=result["url"],
            key=result["key"],
            provider=result["provider"],
            size=result["size"],
            content_type=result["content_type"],
        )
        
    except UploadError as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected upload error: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")


@router.post("/presigned-upload")
async def create_presigned_upload(request: PresignedUploadRequest):
    storage = get_storage_service()
    try:
        result = await storage.create_presigned_upload_url(
            filename=request.filename,
            content_type=request.content_type,
            folder=request.folder,
        )
        return result
    except UploadError as e:
        logger.error(f"Presigned upload creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Presigned URL failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected presigned upload error: {e}")
        raise HTTPException(status_code=500, detail="Presigned URL failed")


@router.get("/status", response_model=StorageStatusResponse)
async def storage_status():
    """Get storage provider status."""
    storage = get_storage_service()
    return StorageStatusResponse(providers=storage.get_status())


@router.delete("/{provider}/{file_key:path}")
async def delete_file(provider: str, file_key: str):
    """
    Delete a file from storage.
    
    Args:
        provider: Storage provider ("s3", "firebase", "local")
        file_key: File key/path
    """
    storage = get_storage_service()
    
    success = await storage.delete(file_key, provider)
    if success:
        return {"message": "File deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="File not found or delete failed")


@router.post("/motion/mediaconvert")
async def start_mediaconvert_job(
    file: UploadFile = File(...),
    output_prefix: str = Form(default="processed/video"),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """
    Upload a video file to S3 and start a MediaConvert transcoding job.
    """
    storage = get_storage_service()
    motion = get_motion_video_service()
    try:
        _consume_modality_quota_or_raise(current_user, "video", limit=3)
        file_data = await file.read()
        if not file_data:
            raise HTTPException(status_code=400, detail="Empty file")

        upload_result = await storage.upload(
            file_data=file_data,
            filename=file.filename or "video.mp4",
            content_type=file.content_type or "video/mp4",
            folder="video-inputs",
            preferred_provider="s3",
        )
        if upload_result.get("provider") != "s3":
            raise HTTPException(status_code=400, detail="S3 upload is required for MediaConvert")

        bucket = upload_result.get("bucket")
        key = upload_result.get("key")
        if not bucket or not key:
            raise HTTPException(status_code=500, detail="Invalid upload metadata for MediaConvert")

        input_s3_uri = f"s3://{bucket}/{key}"
        return await motion.start_mediaconvert_job(
            input_s3_uri=input_s3_uri,
            output_prefix=output_prefix,
        )
    except UploadError as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    except MotionVideoError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MediaConvert start failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/motion/mediaconvert/{job_id}")
async def get_mediaconvert_job_status(job_id: str):
    """Get MediaConvert job status by ID."""
    try:
        motion = get_motion_video_service()
        return motion.get_mediaconvert_job(job_id)
    except MotionVideoError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"MediaConvert status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/motion/nova-reel")
async def start_nova_reel_job(
    request: NovaReelRequest,
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """Start Amazon Nova Reel text-to-video async generation."""
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt is required")
    try:
        _consume_modality_quota_or_raise(current_user, "video", limit=3)
        _consume_best_tier_nova_quota_or_raise(current_user)
        motion = get_motion_video_service()
        return await motion.start_nova_reel_job(
            prompt=request.prompt.strip(),
            duration_seconds=request.duration_seconds,
            aspect_ratio=request.aspect_ratio,
        )
    except MotionVideoError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Nova Reel start failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/motion/nova-reel/status")
async def get_nova_reel_job_status(invocation_arn: str = Query(...)):
    """Get Nova Reel async invocation status by ARN."""
    try:
        motion = get_motion_video_service()
        return motion.get_nova_reel_status(invocation_arn=invocation_arn)
    except MotionVideoError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Nova Reel status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/image/generate")
async def generate_image(
    request: ImageGenerationRequest,
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """Generate image asset using Titan or Nova Canvas."""
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt is required")
    try:
        # One shared image_generation budget for both Titan and Nova Canvas.
        # Do NOT use _consume_best_tier_nova_quota_or_raise here: that flag is shared with
        # Nova Reel and is single-use per user, so switching to Nova Canvas would 403
        # after any prior Nova-tier action and block every subsequent Nova image attempt.
        _consume_modality_quota_or_raise(current_user, "image", limit=3)
        service = get_image_generation_service()
        return await service.generate(
            prompt=request.prompt.strip(),
            engine=request.engine,
            width=request.width,
            height=request.height,
        )
    except ImageGenerationError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
