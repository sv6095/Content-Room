"""
Pre-Flight Pipeline Router — /api/v1/pipeline
One-click unified multi-model analysis for the Scheduler.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

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


@router.get("/languages")
async def get_supported_languages():
    """Return list of supported output languages for the pipeline."""
    return {"languages": SUPPORTED_LANGUAGES}


@router.post("/analyze")
async def analyze_preflight(request: PipelineRequest):
    """
    Run all 6 intelligence checks in parallel and return a unified pre-flight report.
    Safe to call before adding content to the Schedule.
    """
    try:
        from services.pipeline_service import run_preflight_pipeline
        result = await run_preflight_pipeline(
            content=request.content,
            region=request.region,
            target_language=request.target_language,
            platform=request.platform,
            niche=request.niche,
            risk_level=request.risk_level,
            festival=request.festival,
        )
        return result
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
