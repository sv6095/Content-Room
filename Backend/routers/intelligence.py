"""
Intelligence Hub Router — Features #1-6, #9, #10, #11
Aggregates all novel AI intelligence features under /api/v1/intel
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


# ─────────────────────────────────────────────────────────
# Feature #1: Cultural Emotion Engine
# ─────────────────────────────────────────────────────────

class CultureRequest(BaseModel):
    content: str
    region: str
    festival: Optional[str] = None
    content_niche: Optional[str] = None


@router.post("/culture/rewrite")
async def culture_rewrite(request: CultureRequest):
    """Rewrite content with regional emotional persona. AWS Bedrock + Translate primary."""
    try:
        from services.culture_engine import rewrite_for_region
        result = await rewrite_for_region(
            request.content,
            request.region,
            request.festival,
            request.content_niche,
        )
        return result
    except Exception as e:
        logger.error(f"Cultural rewrite error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/culture/regions")
async def get_regions():
    from services.culture_engine import get_available_regions
    return await get_available_regions()


@router.get("/culture/festivals")
async def get_festivals():
    from services.culture_engine import get_available_festivals
    return await get_available_festivals()


# ─────────────────────────────────────────────────────────
# Feature #2: Risk vs Reach Dial
# ─────────────────────────────────────────────────────────

class RiskReachRequest(BaseModel):
    content: str
    risk_level: int  # 0–100
    platform: Optional[str] = None
    niche: Optional[str] = None


@router.post("/risk-reach/generate")
async def risk_reach_generate(request: RiskReachRequest):
    """Generate content at specified risk level (0=Safe, 100=Viral). AWS Comprehend audits output."""
    try:
        from services.risk_reach_service import generate_risk_reach_content
        result = await generate_risk_reach_content(
            request.content,
            request.risk_level,
            request.platform,
            request.niche,
        )
        return result
    except Exception as e:
        logger.error(f"Risk-reach error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────
# Feature #3: Content DNA Fingerprint
# ─────────────────────────────────────────────────────────

class DNARequest(BaseModel):
    new_content: str
    post_history: List[str]
    user_id: Optional[int] = 1


@router.post("/dna/analyze")
async def analyze_dna(request: DNARequest):
    """Fingerprint creator voice & detect brand drift. AWS SageMaker + sentence-transformers fallback."""
    try:
        from services.dna_fingerprint_service import analyze_content_dna
        result = await analyze_content_dna(
            request.new_content,
            request.post_history,
            request.user_id,
        )
        return result
    except Exception as e:
        logger.error(f"DNA fingerprint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────
# Feature #4: Anti-Cancel Shield
# ─────────────────────────────────────────────────────────

class CancelShieldRequest(BaseModel):
    text: str
    target_regions: Optional[List[str]] = None


class HeatmapRequest(BaseModel):
    text: str


@router.post("/anti-cancel/analyze")
async def anti_cancel_analyze(request: CancelShieldRequest):
    """Analyze content for controversy/cancel risk. AWS Comprehend + India-specific blacklist."""
    try:
        from services.anti_cancel_service import analyze_cancel_risk
        result = await analyze_cancel_risk(request.text, request.target_regions)
        return result
    except Exception as e:
        logger.error(f"Anti-cancel error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/anti-cancel/heatmap")
async def sensitivity_heatmap(request: HeatmapRequest):
    """Return word-level sensitivity heatmap for the Studio editor's glow overlay."""
    try:
        from services.anti_cancel_service import get_heatmap_for_text
        heatmap = await get_heatmap_for_text(request.text)
        return {"heatmap": heatmap, "total_words": len(heatmap)}
    except Exception as e:
        logger.error(f"Heatmap error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────
# Feature #6: Creator Mental Health Meter
# ─────────────────────────────────────────────────────────

class MentalHealthRequest(BaseModel):
    posts: List[str]
    user_id: Optional[int] = 1


@router.post("/mental-health/analyze")
async def mental_health_analyze(request: MentalHealthRequest):
    """Analyze creator burnout via linguistic entropy + AWS Comprehend batch sentiment."""
    try:
        from services.mental_health_service import analyze_mental_health
        result = await analyze_mental_health(request.posts, request.user_id)
        return result
    except Exception as e:
        logger.error(f"Mental health analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────
# Feature #9: One Idea → 12 Asset Explosion
# ─────────────────────────────────────────────────────────

class AssetExplosionRequest(BaseModel):
    seed_content: str
    niche: Optional[str] = None
    selected_assets: Optional[List[str]] = None  # None = all 12


@router.post("/explode/assets")
async def explode_assets(request: AssetExplosionRequest):
    """Generate 12 platform-native assets from one idea. AWS Bedrock parallel generation."""
    try:
        from services.asset_explosion_service import explode_to_12_assets
        result = await explode_to_12_assets(
            request.seed_content,
            request.niche,
            request.selected_assets,
        )
        return result
    except Exception as e:
        logger.error(f"Asset explosion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/explode/asset-types")
async def get_asset_types():
    """List all available asset types."""
    from services.asset_explosion_service import get_available_asset_types
    return {"asset_types": get_available_asset_types()}


# ─────────────────────────────────────────────────────────
# Feature #11: Shadowban Predictor
# ─────────────────────────────────────────────────────────

class ShadowbanRequest(BaseModel):
    content: str
    hashtags: Optional[List[str]] = None
    platform: Optional[str] = "instagram"


ENGAGEMENT_BAIT_PATTERNS = [
    "comment yes", "comment below", "tag 3", "double tap", "like if you agree",
    "smash the like", "retweet if", "follow for follow", "share for a shoutout",
]

RISKY_SUFFIXES = [
    "f0llow", "fr33", "c0mment", "l1ke", "b00st",  # character substitution spam
]


@router.post("/shadowban/predict")
async def predict_shadowban(request: ShadowbanRequest):
    """Predict shadowban probability using platform policy pattern matching."""
    try:
        content_lower = request.content.lower()
        risk_factors = []
        score = 0

        # Engagement bait detection
        for pattern in ENGAGEMENT_BAIT_PATTERNS:
            if pattern in content_lower:
                risk_factors.append(f"Engagement bait: '{pattern}'")
                score += 15

        # Circumvented keyword detection
        for suffix in RISKY_SUFFIXES:
            if suffix in content_lower:
                risk_factors.append(f"Spam character substitution: '{suffix}'")
                score += 25

        # Hashtag audit
        risky_hashtags = []
        if request.hashtags:
            for ht in request.hashtags:
                if len(ht) < 3:
                    risky_hashtags.append(f"Too short: {ht}")
                    score += 5
                if any(bait in ht.lower() for bait in ["follow", "like4like", "f4f", "l4l"]):
                    risky_hashtags.append(f"Banned pattern: {ht}")
                    score += 10

        # Excessive CTA repetition
        cta_count = sum(content_lower.count(cta) for cta in ["follow", "like", "share", "comment", "subscribe"])
        if cta_count > 5:
            risk_factors.append(f"Excessive CTAs ({cta_count} found)")
            score += min(30, cta_count * 5)

        score = min(95, score)

        return {
            "shadowban_probability": score,
            "risk_level": "HIGH" if score >= 60 else "MEDIUM" if score >= 30 else "LOW",
            "risk_factors": risk_factors,
            "risky_hashtags": risky_hashtags,
            "platform": request.platform,
            "recommendation": (
                "🚨 High shadowban risk. Remove flagged patterns before posting."
                if score >= 60 else
                "⚠️ Moderate risk. Consider revising flagged sections."
                if score >= 30 else
                "✅ Low shadowban risk. Safe to post."
            ),
            "provider": "rule_engine_v1",
        }
    except Exception as e:
        logger.error(f"Shadowban prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
