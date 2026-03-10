"""
Pre-Flight Pipeline Router — /api/v1/pipeline
One-click unified multi-model analysis for the Scheduler.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from routers.auth import CurrentUser, get_current_user_optional

logger = logging.getLogger(__name__)
router = APIRouter()


SUPPORTED_LANGUAGES = [
    "Hindi", "Tamil", "Telugu", "Kannada", "Malayalam",
    "Bengali", "Marathi", "Gujarati", "Punjabi", "Odia",
    "Urdu", "English", "Hinglish", "Tanglish",
]


class PipelineRequest(BaseModel):
    content: str
    region: str = "general"
    target_language: str = "English"
    platform: str = "instagram"
    niche: Optional[str] = None
    risk_level: int = Field(default=50, ge=0, le=100)
    festival: Optional[str] = None


class PipelineStartResponse(BaseModel):
    analysis_id: str
    execution_arn: Optional[str] = None
    status: str
    orchestrator: str


@router.get("/languages")
async def get_supported_languages():
    """Return list of supported output languages for the pipeline."""
    return {"languages": SUPPORTED_LANGUAGES}


@router.post("/analyze", response_model=PipelineStartResponse)
async def analyze_preflight(
    request: PipelineRequest,
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """
    Run all 6 intelligence checks in parallel and return a unified pre-flight report.
    Safe to call before adding content to the Schedule.
    """
    try:
        from services.pipeline_orchestration_service import get_pipeline_orchestration_service
        svc = get_pipeline_orchestration_service()
        return await svc.start_preflight(
            payload=request.model_dump(),
            user_id=current_user.id if current_user else "anonymous",
        )
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{analysis_id}")
async def get_preflight_status(analysis_id: str):
    try:
        from services.pipeline_orchestration_service import get_pipeline_orchestration_service
        return get_pipeline_orchestration_service().get_status(analysis_id)
    except Exception as e:
        logger.error(f"Pipeline status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/result/{analysis_id}")
async def get_preflight_result(analysis_id: str):
    try:
        from services.pipeline_orchestration_service import get_pipeline_orchestration_service
        result = get_pipeline_orchestration_service().get_result(analysis_id)
        if not result:
            raise HTTPException(status_code=404, detail="Analysis not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pipeline result error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
