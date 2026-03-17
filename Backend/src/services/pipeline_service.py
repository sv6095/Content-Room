"""
Unified Pre-Flight Pipeline Service
One-click multi-model analysis pipeline for Scheduler.

Runs all 6 Intelligence checks in parallel using asyncio.gather():
  1. Culture Engine (Emotional Adaptation)
  2. Risk vs Reach (Virality Score)
  3. Anti-Cancel Shield (Toxicity / NLP)
  4. Shadowban Predictor (Algorithm Safety)
  5. Mental Health Meter (Sentiment Trend)
  6. Asset Explosion (Content Spin-offs)

Returns a single unified PreFlight report.
"""
import asyncio
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)


async def run_preflight_pipeline(
    content: str,
    region: str = "general",
    target_language: str = "English",
    platform: str = "instagram",
    niche: Optional[str] = None,
    risk_level: int = 50,
    festival: Optional[str] = None,
    user_id: Optional[str] = None,
) -> dict:
    """
    Run all intelligence checks in parallel and return a unified report.

    Args:
        content: The content to analyze
        region: Target region (e.g. 'mumbai', 'chennai')
        target_language: Language for emotional adaptation
        platform: Target social media platform
        niche: Content niche (e.g. 'Fashion', 'Tech')
        risk_level: 0-100 risk dial setting
        festival: Optional festival context

    Returns:
        Unified pre-flight report dict
    """
    results: dict = {
        "culture": None,
        "risk_reach": None,
        "anti_cancel": None,
        "shadowban": None,
        "mental_health": None,
        "assets": None,
        "errors": {},
        "passed": False,
        "summary": {},
    }

    # ── 1. Culture Engine ───────────────────────────────────────
    async def run_culture():
        try:
            from services.culture_engine import rewrite_for_region
            return await rewrite_for_region(
                content,
                region,
                festival,
                niche,
                target_language=target_language,
                user_id=user_id,
            )
        except Exception as e:
            logger.warning(f"Pipeline: culture_engine failed: {e}")
            results["errors"]["culture"] = str(e)
            return None

    # ── 2. Risk vs Reach ─────────────────────────────────────────
    async def run_risk_reach():
        try:
            from services.risk_reach_service import generate_risk_reach_content
            return await generate_risk_reach_content(
                content,
                risk_level,
                platform,
                niche,
                user_id=user_id,
            )
        except Exception as e:
            logger.warning(f"Pipeline: risk_reach failed: {e}")
            results["errors"]["risk_reach"] = str(e)
            return None

    # ── 3. Anti-Cancel Shield ────────────────────────────────────
    async def run_anti_cancel():
        try:
            from services.anti_cancel_service import analyze_cancel_risk
            return await analyze_cancel_risk(content, user_id=user_id)
        except Exception as e:
            logger.warning(f"Pipeline: anti_cancel failed: {e}")
            results["errors"]["anti_cancel"] = str(e)
            return None

    # ── 4. Shadowban Predictor ───────────────────────────────────
    async def run_shadowban():
        try:
            # Re-use inline shadowban logic via LLM + rule engine
            from services.llm_service import get_llm_service
            import re

            ENGAGEMENT_BAIT = [
                "comment yes", "comment below", "tag 3", "double tap",
                "like if you agree", "smash the like", "retweet if",
                "follow for follow", "share for a shoutout",
            ]
            content_lower = content.lower()
            rule_score = 100
            rule_factors: List[str] = []
            for pattern in ENGAGEMENT_BAIT:
                if pattern in content_lower:
                    rule_factors.append(f"Engagement bait: '{pattern}'")
                    rule_score -= 18
            rule_score = max(5, min(100, rule_score))

            llm = get_llm_service()
            prompt = (
                f"You are a shadowban detection expert for {platform}.\n"
                f"Analyze this content for shadowban risk:\n{content}\n\n"
                "Reply ONLY:\n"
                "SHADOWBAN_SCORE: [0-100]\n"
                "RECOMMENDATION: [one sentence]"
            )
            res = await llm.generate(
                prompt,
                task="shadowban_predict",
                max_tokens=180,
                user_id=user_id,
            )
            m = re.search(r"SHADOWBAN_SCORE:\s*(\d+)", res["text"], re.IGNORECASE)
            llm_score = int(m.group(1)) if m else 50
            final = min(95, int(llm_score * 0.70 + (100 - rule_score) * 0.30))
            rec_m = re.search(r"RECOMMENDATION:\s*(.+?)$", res["text"], re.IGNORECASE | re.DOTALL)
            rec = rec_m.group(1).strip() if rec_m else (
                "🚨 High risk — review before posting." if final >= 60 else "✅ Low shadowban risk."
            )
            return {
                "shadowban_probability": final,
                "risk_level": "HIGH" if final >= 60 else "MEDIUM" if final >= 30 else "LOW",
                "recommendation": rec,
                "rule_safety_score": rule_score,
                "risk_factors": rule_factors,
                "provider": res["provider"],
            }
        except Exception as e:
            logger.warning(f"Pipeline: shadowban failed: {e}")
            results["errors"]["shadowban"] = str(e)
            return None

    # ── 5. Mental Health (single-post sentiment) ─────────────────
    async def run_mental_health():
        try:
            import boto3

            client = boto3.client("comprehend")
            sentiment_res = client.detect_sentiment(Text=content, LanguageCode="en")
            sentiment = sentiment_res.get("Sentiment", "NEUTRAL").upper()
            tone_advice = (
                "Keep this tone, it reads positive." if sentiment == "POSITIVE"
                else "Consider softening wording for audience wellness." if sentiment == "NEGATIVE"
                else "Neutral tone detected; add more empathy for connection."
            )
            return {
                "sentiment": sentiment,
                "tone_advice": tone_advice,
                "provider": "aws_comprehend",
                "scores": sentiment_res.get("SentimentScore", {}),
            }
        except Exception as e:
            logger.warning(f"Pipeline: mental_health failed: {e}")
            results["errors"]["mental_health"] = str(e)
            return None

    # ── 6. Quick Asset Suggestions (top 3 assets only) ───────────
    async def run_assets():
        try:
            from services.asset_explosion_service import _generate_single_asset, ASSET_PERSONAS
            from services.llm_service import get_llm_service
            llm = get_llm_service()
            # Only generate top 3 for speed in the pipeline context
            top_keys = ["tweet_thread", "instagram_caption" if "instagram_caption" in ASSET_PERSONAS else "carousel_copy", "hook_variants"]
            top_keys = [k for k in top_keys if k in ASSET_PERSONAS][:3]
            tasks = [
                _generate_single_asset(content, k, niche, llm, user_id=user_id)
                for k in top_keys
            ]
            assets = await asyncio.gather(*tasks, return_exceptions=False)
            return {
                "assets": [a for a in assets if a.get("success")],
                "total_generated": len([a for a in assets if a.get("success")]),
            }
        except Exception as e:
            logger.warning(f"Pipeline: assets failed: {e}")
            results["errors"]["assets"] = str(e)
            return None

    # ── Run all checks in parallel ────────────────────────────────
    (
        culture_res,
        risk_res,
        cancel_res,
        shadow_res,
        mental_res,
        asset_res,
    ) = await asyncio.gather(
        run_culture(),
        run_risk_reach(),
        run_anti_cancel(),
        run_shadowban(),
        run_mental_health(),
        run_assets(),
        return_exceptions=False,
    )

    results["culture"] = culture_res
    results["risk_reach"] = risk_res
    results["anti_cancel"] = cancel_res
    results["shadowban"] = shadow_res
    results["mental_health"] = mental_res
    results["assets"] = asset_res

    # ── Build pass/fail summary ───────────────────────────────────
    cancel_ok = (cancel_res is None) or (cancel_res.get("risk_level") != "HIGH")
    shadow_ok = (shadow_res is None) or (shadow_res.get("risk_level") != "HIGH")
    results["passed"] = cancel_ok and shadow_ok

    results["summary"] = {
        "culture_adapted": culture_res is not None,
        "alignment_score": (culture_res or {}).get("alignment_score"),
        "risk_tone": (risk_res or {}).get("tone_label", "Unknown"),
        "safety_score": (risk_res or {}).get("safety_score"),
        "cancel_risk": (cancel_res or {}).get("risk_level", "UNKNOWN"),
        "shadowban_probability": (shadow_res or {}).get("shadowban_probability"),
        "content_sentiment": (mental_res or {}).get("sentiment", "UNKNOWN"),
        "assets_generated": (asset_res or {}).get("total_generated", 0),
        "overall_pass": results["passed"],
        "errors_count": len(results["errors"]),
    }

    return results
