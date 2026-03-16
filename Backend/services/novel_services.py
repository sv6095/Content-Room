"""
Novel Future Enhancement Services — Content Room
=================================================
Implements 5 advanced agentic features using the existing LLM fallback chain.
Primary: AWS Bedrock (Nova) with Groq fallback via shared llm_service.

Features:
1. Multi-Agent Competitor Intelligence (Signal Intelligence)
2. Contextual RAG for Hyper-Local Trend Injection
3. Omnichannel Multimodal Production
4. Platform Adapter (Content Differences per Platform)
5. Predictive Creator Burnout & Self-Evolving Workloads
"""
import logging
import re
from typing import Optional, List
from datetime import datetime

from utils.linguistics import (
    compute_normalised_entropy,
    compute_repetition_index,
    sentiment_word_ratio,
    count_burnout_keywords,
    post_length_decline,
)

logger = logging.getLogger(__name__)


def _missing_required_markers(text: str, required_markers: Optional[List[str]] = None) -> List[str]:
    """Return missing required markers (case-insensitive substring match)."""
    if not required_markers:
        return []
    normalized = (text or "").lower()
    return [m for m in required_markers if m.lower() not in normalized]


async def _generate_with_validation(
    llm,
    prompt: str,
    task: str,
    max_tokens: int,
    required_markers: Optional[List[str]] = None,
    min_len: int = 40,
) -> dict:
    """
    Generate once, validate output shape, and auto-retry once if malformed.
    Returns llm.generate() result payload.
    """
    first = await llm.generate(prompt, task=task, max_tokens=max_tokens)
    text = (first.get("text") or "").strip()
    missing = _missing_required_markers(text, required_markers)
    if text and len(text) >= min_len and not missing:
        return first

    retry_prompt = (
        f"{prompt}\n\n"
        "IMPORTANT: Follow the required output structure exactly."
        + (f" Include these markers: {', '.join(required_markers)}." if required_markers else "")
        + " Return only the final structured output."
    )
    second = await llm.generate(retry_prompt, task=task, max_tokens=max_tokens)
    second_text = (second.get("text") or "").strip()
    second_missing = _missing_required_markers(second_text, required_markers)
    if second_text and len(second_text) >= min_len and not second_missing:
        second["fallback_used"] = True if second.get("fallback_used") else True
        return second

    raise RuntimeError(
        f"Malformed LLM output for task '{task}' "
        f"(missing markers: {second_missing or missing}, len={len(second_text)})"
    )


# ═══════════════════════════════════════════════════════════════
# 1. MULTI-AGENT COMPETITOR INTELLIGENCE
# ═══════════════════════════════════════════════════════════════

# Multi-agent architecture:
#   Agent A (Scraper)   → We use LLM to simulate extracted competitor data
#   Agent B (Analyst)   → LLM analyzes patterns
#   Agent C (Strategist)→ LLM generates actionable briefs

async def competitor_signal_intelligence(
    competitor_handles: List[str],
    niche: str,
    region: str = "pan-india",
    platforms: Optional[List[str]] = None,
) -> dict:
    """
    Multi-Agent Signal Intelligence Pipeline.
    Deploys 3 virtual agents to analyze competitors and generate content briefs.
    """
    from services.llm_service import get_llm_service
    llm = get_llm_service()

    platforms_str = ", ".join(platforms) if platforms else "Instagram, YouTube, Twitter"
    handles_str = ", ".join(competitor_handles)

    # ── Agent A: Scraper Agent (LLM intelligence proxy) ────────────────
    scraper_prompt = f"""Agent A (signal scraper).
Competitors: {handles_str}
Platforms: {platforms_str}
Niche: {niche}
Region: {region}

Build a realistic intelligence estimate from typical public creator behavior (use ranges, avoid presenting invented facts as verified).
Return sections:
TOP_POST_PATTERNS
HOOK_PATTERNS
POSTING_CADENCE
HASHTAG_STRATEGY
FORMAT_DISTRIBUTION
"""

    agent_a_result = await _generate_with_validation(
        llm,
        scraper_prompt,
        task="signal_intel_scraper",
        max_tokens=520,
        required_markers=[
            "TOP_POST_PATTERNS",
            "HOOK_PATTERNS",
            "POSTING_CADENCE",
            "HASHTAG_STRATEGY",
            "FORMAT_DISTRIBUTION",
        ],
    )

    # ── Agent B: Analyst Agent ────────────────────────────────────
    analyst_prompt = f"""Agent B (competitive analyst).
Niche: {niche}
Input from Agent A:
{agent_a_result['text'][:1200]}

Return concise sections:
VIRALITY_PATTERNS
CONTENT_GAPS
TIMING_INSIGHTS
AUDIENCE_SENTIMENT
WEAKNESS_MAP
Use specific, actionable insights with estimated confidence where needed.
"""

    agent_b_result = await _generate_with_validation(
        llm,
        analyst_prompt,
        task="signal_intel_analyst",
        max_tokens=520,
        required_markers=[
            "VIRALITY_PATTERNS",
            "CONTENT_GAPS",
            "TIMING_INSIGHTS",
            "AUDIENCE_SENTIMENT",
            "WEAKNESS_MAP",
        ],
    )

    # ── Agent C: Strategist Agent ─────────────────────────────────
    strategist_prompt = f"""Agent C (content strategist) for niche={niche}, region={region}.
Input from Agent B:
{agent_b_result['text'][:1200]}

Create 5 content briefs.
For each brief include:
TITLE
FORMAT
HOOK (2 lines)
ANGLE
URGENCY (HIGH/MEDIUM/LOW)

Then include:
WEEKLY_STRATEGY_SUMMARY (3 sentences)
CONTENT_CALENDAR_SUGGESTION (this week)
"""

    agent_c_result = await _generate_with_validation(
        llm,
        strategist_prompt,
        task="signal_intel_strategist",
        max_tokens=560,
        required_markers=[
            "TITLE",
            "FORMAT",
            "HOOK",
            "ANGLE",
            "URGENCY",
            "WEEKLY_STRATEGY_SUMMARY",
            "CONTENT_CALENDAR_SUGGESTION",
        ],
    )

    return {
        "competitor_handles": competitor_handles,
        "niche": niche,
        "region": region,
        "agents": {
            "scraper": {
                "name": "Agent A — Scraper",
                "output": agent_a_result["text"],
                "provider": agent_a_result["provider"],
            },
            "analyst": {
                "name": "Agent B — Analyst",
                "output": agent_b_result["text"],
                "provider": agent_b_result["provider"],
            },
            "strategist": {
                "name": "Agent C — Strategist",
                "output": agent_c_result["text"],
                "provider": agent_c_result["provider"],
            },
        },
        "provider_chain": [
            agent_a_result["provider"],
            agent_b_result["provider"],
            agent_c_result["provider"],
        ],
        "timestamp": datetime.utcnow().isoformat(),
    }


# ═══════════════════════════════════════════════════════════════
# 2. CONTEXTUAL RAG — HYPER-LOCAL TREND INJECTION
# ═══════════════════════════════════════════════════════════════

REGION_CONTEXT = {
    "mumbai": {
        "languages": ["Hindi", "Marathi", "English"],
        "festivals": ["Ganpati", "Diwali", "Holi", "Eid", "Christmas"],
        "local_topics": ["Bollywood", "Stock Market", "Mumbai Rains", "Local Trains", "Street Food"],
    },
    "delhi": {
        "languages": ["Hindi", "Punjabi", "English"],
        "festivals": ["Diwali", "Holi", "Lohri", "Eid"],
        "local_topics": ["Politics", "Pollution", "Metro", "Street Food", "Cricket"],
    },
    "chennai": {
        "languages": ["Tamil", "English"],
        "festivals": ["Pongal", "Deepavali", "Tamil New Year"],
        "local_topics": ["Rajinikanth", "Filter Coffee", "Marina Beach", "IT Industry", "Classical Music"],
    },
    "kolkata": {
        "languages": ["Bengali", "Hindi", "English"],
        "festivals": ["Durga Puja", "Diwali", "Poila Baisakh"],
        "local_topics": ["Literature", "Rosogolla", "Howrah Bridge", "Football", "Art Cinema"],
    },
    "bangalore": {
        "languages": ["Kannada", "English", "Hindi"],
        "festivals": ["Ugadi", "Dasara", "Diwali"],
        "local_topics": ["Tech Startups", "Traffic", "Craft Beer", "Weekend Getaways", "IT Parks"],
    },
    "hyderabad": {
        "languages": ["Telugu", "Urdu", "Hindi", "English"],
        "festivals": ["Bonalu", "Bathukamma", "Diwali", "Eid"],
        "local_topics": ["Biryani", "HITEC City", "Charminar", "Tollywood", "Pharma Industry"],
    },
    "punjab": {
        "languages": ["Punjabi", "Hindi"],
        "festivals": ["Lohri", "Baisakhi", "Diwali"],
        "local_topics": ["Agriculture", "Bhangra", "Paratha", "NRI Culture", "Music Industry"],
    },
    "pan-india": {
        "languages": ["Hindi", "English"],
        "festivals": ["Diwali", "Holi", "Eid", "Christmas", "Pongal"],
        "local_topics": ["Cricket", "Bollywood", "Tech", "Startups", "Elections"],
    },
}


async def hyper_local_trend_injection(
    content: str,
    region: str,
    niche: str,
    inject_trends: bool = True,
) -> dict:
    """
    RAG-enhanced content adaptation with hyper-local trend injection.
    Fetches simulated trending topics and injects them into the content.
    """
    from services.llm_service import get_llm_service
    llm = get_llm_service()

    region_key = region.lower().replace(" ", "_")
    region_data = REGION_CONTEXT.get(region_key, REGION_CONTEXT["pan-india"])

    if not inject_trends:
        return {
            "original_content": content,
            "region": region,
            "niche": niche,
            "region_context": region_data,
            "trending_topics": "",
            "enhanced_content": content,
            "trend_provider": "disabled",
            "injection_provider": "disabled",
            "timestamp": datetime.utcnow().isoformat(),
        }

    # ── Trend Discovery Agent ─────────────────────────────────────
    trend_prompt = f"""You are a Hyper-Local Trend Discovery Agent for {region}, India.

Current date context: {datetime.now().strftime('%B %Y')}
Region: {region}
Languages spoken: {', '.join(region_data['languages'])}
Major festivals: {', '.join(region_data['festivals'])}
Local trending topics: {', '.join(region_data['local_topics'])}
Creator niche: {niche}

Return top 5 trend opportunities for {niche}.
For each: TREND | WHY | RELEVANCE(1-10) | HOOK | HASHTAGS(3).
Be region-specific, avoid generic filler.
"""

    trends_result = await _generate_with_validation(
        llm,
        trend_prompt,
        task="rag_trend_discovery",
        max_tokens=420,
        required_markers=["TREND", "WHY", "RELEVANCE", "HOOK", "HASHTAGS"],
    )

    # ── Content Injection Agent ───────────────────────────────────
    injection_prompt = f"""Role: regional content enhancer for {region}.
Niche: {niche}
Primary language: {region_data['languages'][0]} (code-switch with English if natural)
Original content:
{content}

Trend candidates:
{trends_result['text'][:900]}

Rewrite by naturally injecting 2-3 relevant trends while preserving core message.
Output EXACT sections:
ENHANCED_CONTENT:
INJECTED_TRENDS:
LOCAL_HASHTAGS:
CULTURAL_NOTES:
"""

    injection_result = await _generate_with_validation(
        llm,
        injection_prompt,
        task="rag_trend_injection",
        max_tokens=520,
        required_markers=["ENHANCED_CONTENT", "INJECTED_TRENDS", "LOCAL_HASHTAGS", "CULTURAL_NOTES"],
    )

    return {
        "original_content": content,
        "region": region,
        "niche": niche,
        "region_context": region_data,
        "trending_topics": trends_result["text"],
        "enhanced_content": injection_result["text"],
        "trend_provider": trends_result["provider"],
        "injection_provider": injection_result["provider"],
        "timestamp": datetime.utcnow().isoformat(),
    }


# ═══════════════════════════════════════════════════════════════
# 3. OMNICHANNEL MULTIMODAL PRODUCTION
# ═══════════════════════════════════════════════════════════════

PRODUCTION_FORMATS = {
    "podcast_script": {
        "name": "🎙️ Podcast Script",
        "description": "Full conversational podcast script with host/guest dialogues",
    },
    "video_storyboard": {
        "name": "🎬 Video Storyboard",
        "description": "Scene-by-scene visual storyboard with shots, dialogues, and B-roll notes",
    },
    "audio_narration": {
        "name": "🔊 Audio Narration Script",
        "description": "Voice-over narration script optimized for text-to-speech",
    },
    "multilingual_adapt": {
        "name": "🌐 Multilingual Adaptation",
        "description": "Content adapted in 5 Indian languages with cultural nuances",
    },
    "thumbnail_brief": {
        "name": "🖼️ Thumbnail Design Brief",
        "description": "Detailed visual brief for thumbnail/cover designs",
    },
    "motion_graphics_script": {
        "name": "✨ Motion Graphics Script",
        "description": "Script with timing cues for animated content",
    },
}


async def multimodal_production(
    seed_content: str,
    formats: List[str],
    niche: str,
    target_language: str = "Hindi",
) -> dict:
    """
    Omnichannel Multimodal Production Agent.
    Generates production-ready scripts for multiple media formats from a single seed idea.
    """
    from services.llm_service import get_llm_service
    llm = get_llm_service()
    import asyncio

    async def generate_format(fmt_key: str) -> dict:
        fmt = PRODUCTION_FORMATS.get(fmt_key, {"name": fmt_key, "description": ""})

        prompt = f"""You are a Multimodal Content Production Agent.
Format: {fmt['name']}
Description: {fmt['description']}
Niche: {niche}
Language: {target_language}
Seed idea:
{seed_content}

Produce a complete, production-ready document for this format.
Include relevant structure (script cues / storyboard shots / multilingual adaptation / design notes) and platform optimization notes where useful.
Return only final document.
"""

        try:
            result = await _generate_with_validation(
                llm,
                prompt,
                task=f"multimodal_{fmt_key}",
                max_tokens=520,
                required_markers=None,
                min_len=80,
            )
            return {
                "format_key": fmt_key,
                "format_name": fmt["name"],
                "content": result["text"],
                "provider": result["provider"],
                "success": True,
            }
        except Exception as e:
            logger.error(f"Multimodal production failed for {fmt_key}: {e}")
            return {
                "format_key": fmt_key,
                "format_name": fmt["name"],
                "content": "",
                "provider": "error",
                "error": str(e)[:160],
                "success": False,
            }

    # Run all format generations in parallel
    tasks = [generate_format(fmt) for fmt in formats]
    results = await asyncio.gather(*tasks)

    successful = sum(1 for r in results if r["success"])
    if successful == 0:
        raise RuntimeError("All multimodal format generations failed")

    return {
        "seed_content": seed_content,
        "niche": niche,
        "target_language": target_language,
        "total_formats": len(formats),
        "successful": successful,
        "productions": results,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ═══════════════════════════════════════════════════════════════
# 4. PLATFORM ADAPTER (Content Differences per Platform)
# ═══════════════════════════════════════════════════════════════

PLATFORM_SPECS = {
    "instagram": {
        "max_caption_chars": 2200,
        "max_hashtags": 30,
        "best_times": ["9:00 AM", "12:00 PM", "6:00 PM", "9:00 PM"],
        "formats": ["Feed Post", "Reel", "Carousel", "Story"],
    },
    "youtube": {
        "max_title_chars": 100,
        "max_description_chars": 5000,
        "best_times": ["2:00 PM", "5:00 PM", "7:00 PM"],
        "formats": ["Long Form", "Shorts", "Community Post"],
    },
    "twitter": {
        "max_chars": 280,
        "best_times": ["8:00 AM", "12:00 PM", "5:00 PM"],
        "formats": ["Tweet", "Thread", "Poll"],
    },
    "linkedin": {
        "max_chars": 3000,
        "best_times": ["8:00 AM", "10:00 AM", "12:00 PM"],
        "formats": ["Post", "Article", "Newsletter"],
    },
}


async def auto_publish_preview(
    content: str,
    platforms: List[str],
    niche: str,
    schedule_time: Optional[str] = None,
) -> dict:
    """
    Platform Adapter — generates platform-optimized previews
    showing how content differs per platform (no actual publishing).
    """
    from services.llm_service import get_llm_service
    llm = get_llm_service()

    platform_previews = []

    for platform in platforms:
        specs = PLATFORM_SPECS.get(platform.lower(), PLATFORM_SPECS["instagram"])

        prompt = f"""Role: platform adapter for {platform}.
Niche: {niche}
Platform specs: {specs}
Original content:
{content}

Generate publication-ready output with sections:
OPTIMIZED_CONTENT:
HASHTAGS_OR_TAGS:
BEST_TIME_TO_POST:
FORMAT_RECOMMENDATION:
ENGAGEMENT_HOOKS:
SEO_METADATA:
COMPLIANCE_CHECK:
No placeholders.
"""

        try:
            result = await _generate_with_validation(
                llm,
                prompt,
                task=f"autopublish_{platform}",
                max_tokens=420,
                required_markers=[
                    "OPTIMIZED_CONTENT",
                    "HASHTAGS_OR_TAGS",
                    "BEST_TIME_TO_POST",
                    "FORMAT_RECOMMENDATION",
                    "ENGAGEMENT_HOOKS",
                    "SEO_METADATA",
                    "COMPLIANCE_CHECK",
                ],
            )
            output_text = result["text"]
            time_match = re.search(r"BEST TIME TO POST:\s*(.+)", output_text, re.IGNORECASE)
            recommended_time = schedule_time or (time_match.group(1).strip() if time_match else None)
            if not recommended_time:
                recommended_time = specs.get("best_times", ["12:00 PM"])[0]
            platform_previews.append({
                "platform": platform,
                "optimized_content": output_text,
                "provider": result["provider"],
                "specs": specs,
                "recommended_time": recommended_time,
                "status": "ready_to_publish",
                "success": True,
            })
        except Exception as e:
            platform_previews.append({
                "platform": platform,
                "optimized_content": "",
                "provider": "error",
                "error": str(e)[:160],
                "specs": specs,
                "recommended_time": None,
                "status": "failed",
                "success": False,
            })

    successful_count = sum(1 for p in platform_previews if p["success"])
    if successful_count == 0:
        raise RuntimeError("All platform adaptation generations failed")

    return {
        "original_content": content,
        "platforms": platforms,
        "niche": niche,
        "schedule_time": schedule_time,
        "previews": platform_previews,
        "total_platforms": len(platforms),
        "successful": successful_count,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ═══════════════════════════════════════════════════════════════
# 5. PREDICTIVE BURNOUT — SELF-EVOLVING WORKLOAD
# ═══════════════════════════════════════════════════════════════

def _compute_burnout_signals(posts: List[str]) -> dict:
    """
    Rule-based burnout signal detection (RL layer).
    Delegates to shared `utils.linguistics` primitives and composes a
    composite score from entropy, repetition, keyword, length, and sentiment signals.
    """
    if not posts or len(posts) < 2:
        return {
            "burnout_score": 0,
            "signals": ["Insufficient data for analysis"],
            "entropy": 0,
            "sentiment_drift": 0,
            "repetition_index": 0,
        }

    # ── Individual signal values ────────────────────────────
    entropy       = compute_normalised_entropy(posts)
    rep_index     = compute_repetition_index(posts)
    kw_hits       = count_burnout_keywords(posts)
    len_decline   = post_length_decline(posts)
    sent_ratio    = sentiment_word_ratio(posts)

    # ── Composite scoring ──────────────────────────────────
    signals: list[str] = []
    score = 0

    if entropy < 0.6:
        score += 25
        signals.append(f"Low linguistic diversity (entropy: {entropy:.2f})")
    if rep_index > 0.7:
        score += 20
        signals.append(f"High word repetition ({rep_index:.1%})")
    if kw_hits >= 2:
        score += 30
        signals.append(f"Burnout language detected ({kw_hits} keywords)")
    elif kw_hits == 1:
        score += 15
        signals.append(f"Mild burnout language ({kw_hits} keyword)")
    if len_decline > 0.3:
        score += 20
        signals.append(f"Post length declining by {len_decline:.0%}")
    if sent_ratio < 0.3:
        score += 15
        signals.append("Sentiment skewing negative")

    score = min(100, score)
    if not signals:
        signals.append("No significant burnout signals detected")

    return {
        "burnout_score": score,
        "signals": signals,
        "entropy": round(entropy, 3),
        "sentiment_drift": round(sent_ratio, 3),
        "repetition_index": round(rep_index, 3),
        "length_decline": round(len_decline, 3),
        "burnout_keywords_found": kw_hits,
        "total_posts_analyzed": len(posts),
    }


async def predictive_burnout_workload(
    posts: List[str],
    niche: str,
    weekly_target: int = 7,
) -> dict:
    """
    Predictive Creator Burnout & Self-Evolving Workload Agent.

    RL layer: Analyzes linguistic signals for burnout
    LLM layer: Generates an adapted weekly plan that adjusts intensity based on burnout level
    """
    from services.llm_service import get_llm_service
    llm = get_llm_service()

    # ── Rule Layer: Burnout Signal Detection ──────────────────────
    burnout_data = _compute_burnout_signals(posts)
    burnout_score = burnout_data["burnout_score"]

    # Determine workload adjustment
    if burnout_score >= 70:
        workload_mode = "RECOVERY"
        adjusted_target = max(2, weekly_target // 3)
        mode_desc = "🔴 High burnout detected — shifting to recovery mode"
    elif burnout_score >= 40:
        workload_mode = "REDUCED"
        adjusted_target = max(3, int(weekly_target * 0.6))
        mode_desc = "🟡 Moderate burnout — reducing workload"
    else:
        workload_mode = "NORMAL"
        adjusted_target = weekly_target
        mode_desc = "🟢 Creator appears healthy — maintaining schedule"

    # ── LLM Layer: Generate Adapted Schedule ──────────────────────
    schedule_prompt = f"""Role: creator wellness + productivity planner.
Burnout score: {burnout_score}/100
Mode: {workload_mode}
Signals: {burnout_data['signals']}
Entropy: {burnout_data['entropy']}
Sentiment drift: {burnout_data['sentiment_drift']}
Niche: {niche}
Weekly target: {weekly_target} -> adjusted {adjusted_target}

Generate weekly plan (Mon-Sun). For each day provide:
TASK | EFFORT(Easy/Medium/Hard) | FORMAT | TOPIC | WELLNESS_TIP

Rules:
- RECOVERY: 2-3 posts/week max + recovery days
- REDUCED: 4-5 posts/week, simpler formats
- NORMAL: full schedule with balanced effort
- Include one evergreen repost suggestion
- End with CREATOR_WELLNESS_SCORE for next week
"""

    schedule_result = await _generate_with_validation(
        llm,
        schedule_prompt,
        task="burnout_schedule",
        max_tokens=560,
        required_markers=["TASK", "EFFORT", "FORMAT", "TOPIC", "WELLNESS_TIP", "CREATOR_WELLNESS_SCORE"],
    )

    return {
        "burnout_analysis": burnout_data,
        "workload_mode": workload_mode,
        "mode_description": mode_desc,
        "original_target": weekly_target,
        "adjusted_target": adjusted_target,
        "adapted_schedule": schedule_result["text"],
        "schedule_provider": schedule_result["provider"],
        "niche": niche,
        "timestamp": datetime.utcnow().isoformat(),
    }
