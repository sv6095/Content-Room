"""
Novel Hub Router — Future Enhancement Features
=================================================
Exposes the 5 novel agentic features as API endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
import json
import logging
from routers.auth import CurrentUser, get_current_user_optional
from services.dynamo_repositories import get_ai_cache_repo, get_content_repo

logger = logging.getLogger(__name__)
# Prefix is applied in main.py ("/api/v1/novel"), so keep router paths relative.
router = APIRouter(tags=["novel"])


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


def _truncate(value: Optional[str], max_len: int) -> Optional[str]:
    if not value:
        return value
    if len(value) <= max_len:
        return value
    return value[: max_len - 1] + "…"


def _build_cache_key(feature: str, payload: dict) -> str:
    return json.dumps({"feature": feature, "payload": payload}, sort_keys=True, ensure_ascii=False)


def _get_cached_result(feature: str, payload: dict) -> Optional[dict]:
    try:
        cache_repo = get_ai_cache_repo()
        cache_key = _build_cache_key(feature, payload)
        cached = cache_repo.get(cache_key, feature)
        if not cached or not cached.get("response"):
            return None
        parsed = json.loads(cached["response"])
        if isinstance(parsed, dict):
            parsed["cached"] = True
            return parsed
    except Exception as exc:
        logger.warning("Novel cache read failed for %s: %s", feature, exc)
    return None


def _put_cached_result(feature: str, payload: dict, result: dict) -> None:
    try:
        cache_repo = get_ai_cache_repo()
        cache_key = _build_cache_key(feature, payload)
        cache_repo.put(cache_key, feature, json.dumps(result, ensure_ascii=False), ttl_days=7)
    except Exception as exc:
        logger.warning("Novel cache write failed for %s: %s", feature, exc)


def _extract_summary(feature: str, result: dict) -> str:
    if feature == "signal-intelligence":
        return _truncate(result.get("agents", {}).get("strategist", {}).get("output"), 10000) or "Signal Intelligence result."
    if feature == "trend-injection":
        return _truncate(result.get("enhanced_content"), 10000) or "Trend Injection result."
    if feature == "multimodal-production":
        productions = result.get("productions") or []
        combined = "\n\n".join(
            f"{p.get('format_name', 'Format')}:\n{p.get('content', '')}"
            for p in productions
            if p.get("success")
        )
        return _truncate(combined, 10000) or "Multimodal production result."
    if feature == "auto-publish":
        previews = result.get("previews") or []
        combined = "\n\n".join(
            f"{p.get('platform', 'platform')}:\n{p.get('optimized_content', '')}"
            for p in previews
            if p.get("success")
        )
        return _truncate(combined, 10000) or "Platform adaptation result."
    if feature == "burnout-predict":
        return _truncate(result.get("adapted_schedule"), 10000) or "Burnout prediction result."
    return _truncate(json.dumps(result, ensure_ascii=False), 10000) or "Novel AI Lab result."


def _save_novel_result_to_content(
    *,
    user: Optional[CurrentUser],
    feature: str,
    input_payload: dict,
    result: dict,
) -> None:
    if not user:
        return
    try:
        get_content_repo().create_content(
            {
                "user_id": user.id,
                "record_type": "content",
                "content_type": "text",
                "original_text": _truncate(json.dumps(input_payload, ensure_ascii=False), 4000),
                "caption": f"Novel AI Lab - {feature}",
                "summary": _extract_summary(feature, result),
                "moderation_status": "pending",
                "status": "draft",
            }
        )
    except Exception as exc:
        logger.warning("Novel result save failed for %s: %s", feature, exc)


# ─── Endpoints ─────────────────────────────────────────────────

@router.post("/signal-intelligence")
async def signal_intelligence(
    request: SignalIntelRequest,
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """Multi-Agent Competitor Signal Intelligence."""
    payload = request.model_dump()
    cached = _get_cached_result("signal-intelligence", payload)
    if cached:
        _save_novel_result_to_content(
            user=current_user,
            feature="signal-intelligence",
            input_payload=payload,
            result=cached,
        )
        return cached
    try:
        from services.novel_services import competitor_signal_intelligence
        result = await competitor_signal_intelligence(
            competitor_handles=request.competitor_handles,
            niche=request.niche,
            region=request.region,
            platforms=request.platforms,
            user_id=current_user.id if current_user else None,
        )
        _put_cached_result("signal-intelligence", payload, result)
        _save_novel_result_to_content(
            user=current_user,
            feature="signal-intelligence",
            input_payload=payload,
            result=result,
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
    payload = request.model_dump()
    cached = _get_cached_result("trend-injection", payload)
    if cached:
        _save_novel_result_to_content(
            user=current_user,
            feature="trend-injection",
            input_payload=payload,
            result=cached,
        )
        return cached
    try:
        from services.novel_services import hyper_local_trend_injection
        result = await hyper_local_trend_injection(
            content=request.content,
            region=request.region,
            niche=request.niche,
            inject_trends=request.inject_trends,
            user_id=current_user.id if current_user else None,
        )
        _put_cached_result("trend-injection", payload, result)
        _save_novel_result_to_content(
            user=current_user,
            feature="trend-injection",
            input_payload=payload,
            result=result,
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
    payload = request.model_dump()
    cached = _get_cached_result("multimodal-production", payload)
    if cached:
        _save_novel_result_to_content(
            user=current_user,
            feature="multimodal-production",
            input_payload=payload,
            result=cached,
        )
        return cached
    try:
        from services.novel_services import multimodal_production as produce
        result = await produce(
            seed_content=request.seed_content,
            formats=request.formats,
            niche=request.niche,
            target_language=request.target_language,
            user_id=current_user.id if current_user else None,
        )
        _put_cached_result("multimodal-production", payload, result)
        _save_novel_result_to_content(
            user=current_user,
            feature="multimodal-production",
            input_payload=payload,
            result=result,
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
    payload = request.model_dump()
    cached = _get_cached_result("auto-publish", payload)
    if cached:
        _save_novel_result_to_content(
            user=current_user,
            feature="auto-publish",
            input_payload=payload,
            result=cached,
        )
        return cached
    try:
        from services.novel_services import auto_publish_preview
        result = await auto_publish_preview(
            content=request.content,
            platforms=request.platforms,
            niche=request.niche,
            schedule_time=request.schedule_time,
            user_id=current_user.id if current_user else None,
        )
        _put_cached_result("auto-publish", payload, result)
        _save_novel_result_to_content(
            user=current_user,
            feature="auto-publish",
            input_payload=payload,
            result=result,
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
    payload = request.model_dump()
    cached = _get_cached_result("burnout-predict", payload)
    if cached:
        _save_novel_result_to_content(
            user=current_user,
            feature="burnout-predict",
            input_payload=payload,
            result=cached,
        )
        return cached
    try:
        from services.novel_services import predictive_burnout_workload
        result = await predictive_burnout_workload(
            posts=request.posts,
            niche=request.niche,
            weekly_target=request.weekly_target,
            user_id=current_user.id if current_user else None,
        )
        _put_cached_result("burnout-predict", payload, result)
        _save_novel_result_to_content(
            user=current_user,
            feature="burnout-predict",
            input_payload=payload,
            result=result,
        )
        return result
    except Exception as e:
        logger.error(f"Burnout Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
