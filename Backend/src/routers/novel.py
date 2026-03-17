"""
Novel Hub Router — Future Enhancement Features
=================================================
Exposes the 5 novel agentic features as API endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
import logging
from routers.auth import CurrentUser, get_current_user_optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/novel", tags=["novel"])


# ─── Request Models ────────────────────────────────────────────

class SignalIntelRequest(BaseModel):
    competitor_handles: List[str]
    niche: str
    region: str = "pan-india"
    platforms: Optional[List[str]] = None


class TrendInjectionRequest(BaseModel):
    content: str
    region: str
    niche: str
    inject_trends: bool = True


class MultimodalRequest(BaseModel):
    seed_content: str
    formats: List[str]
    niche: str
    target_language: str = "Hindi"


class PlatformAdaptRequest(BaseModel):
    content: str
    platforms: List[str]
    niche: str
    schedule_time: Optional[str] = None


class BurnoutRequest(BaseModel):
    posts: List[str]
    niche: str
    weekly_target: int = 7


# ─── Endpoints ─────────────────────────────────────────────────

@router.post("/signal-intelligence")
async def signal_intelligence(
    request: SignalIntelRequest,
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """Multi-Agent Competitor Signal Intelligence."""
    try:
        from services.novel_services import competitor_signal_intelligence
        result = await competitor_signal_intelligence(
            competitor_handles=request.competitor_handles,
            niche=request.niche,
            region=request.region,
            platforms=request.platforms,
            user_id=current_user.id if current_user else None,
        )
        return result
    except Exception as e:
        logger.error(f"Signal Intelligence failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trend-injection")
async def trend_injection(
    request: TrendInjectionRequest,
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """Hyper-Local Trend Injection via Contextual RAG."""
    try:
        from services.novel_services import hyper_local_trend_injection
        result = await hyper_local_trend_injection(
            content=request.content,
            region=request.region,
            niche=request.niche,
            inject_trends=request.inject_trends,
            user_id=current_user.id if current_user else None,
        )
        return result
    except Exception as e:
        logger.error(f"Trend Injection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/multimodal-production")
async def multimodal_production(
    request: MultimodalRequest,
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """Omnichannel Multimodal Content Production."""
    try:
        from services.novel_services import multimodal_production as produce
        result = await produce(
            seed_content=request.seed_content,
            formats=request.formats,
            niche=request.niche,
            target_language=request.target_language,
            user_id=current_user.id if current_user else None,
        )
        return result
    except Exception as e:
        logger.error(f"Multimodal Production failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/production-formats")
async def get_production_formats():
    """List available multimodal production formats."""
    from services.novel_services import PRODUCTION_FORMATS
    return {
        "formats": [
            {"key": k, "name": v["name"], "description": v["description"]}
            for k, v in PRODUCTION_FORMATS.items()
        ]
    }


@router.post("/auto-publish")
async def auto_publish(
    request: PlatformAdaptRequest,
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """Platform Adapter — generates platform-optimized content previews showing how content differs per platform."""
    try:
        from services.novel_services import auto_publish_preview
        result = await auto_publish_preview(
            content=request.content,
            platforms=request.platforms,
            niche=request.niche,
            schedule_time=request.schedule_time,
            user_id=current_user.id if current_user else None,
        )
        return result
    except Exception as e:
        logger.error(f"Auto-Publish failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/burnout-predict")
async def burnout_predict(
    request: BurnoutRequest,
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """Predictive Creator Burnout & Self-Evolving Workload."""
    try:
        from services.novel_services import predictive_burnout_workload
        result = await predictive_burnout_workload(
            posts=request.posts,
            niche=request.niche,
            weekly_target=request.weekly_target,
            user_id=current_user.id if current_user else None,
        )
        return result
    except Exception as e:
        logger.error(f"Burnout Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
