"""
One Idea → 12 Asset Explosion Engine — Feature #9
AWS Bedrock (Claude 3.5 Sonnet) Primary
Fallback: Groq → Gemini → Templates

Prompt chaining: 1 seed → 12 platform-native assets in parallel.
"""
import logging
import asyncio
from typing import Optional
from services.llm_service import get_llm_service

logger = logging.getLogger(__name__)

ASSET_PERSONAS = {
    "reel_script": {
        "persona": "The Hook-Master Reels Creator",
        "platform": "Instagram Reels / YouTube Shorts",
        "instructions": "Write a 30-second Reel script: Hook (3 sec) | Build (20 sec) | CTA (7 sec). Use visual action cues in [brackets].",
        "max_tokens": 300,
    },
    "carousel_copy": {
        "persona": "The Carousel Educator",
        "platform": "Instagram Carousel",
        "instructions": "Write 5 slide captions: Slide 1 (hook), Slides 2-4 (value points), Slide 5 (CTA/save prompt). Each max 40 words.",
        "max_tokens": 300,
    },
    "linkedin_article": {
        "persona": "The LinkedIn Thought Leader",
        "platform": "LinkedIn",
        "instructions": "Write a 150-word LinkedIn article: bold insight opener, 2 supporting points, professional CTA. No hashtag spam.",
        "max_tokens": 350,
    },
    "tweet_thread": {
        "persona": "The Twitter/X Thread Brawler",
        "platform": "Twitter/X",
        "instructions": "Write a 5-tweet thread. Tweet 1 = hook. Tweets 2-4 = value. Tweet 5 = CTA. Each tweet < 280 chars. Number them 1/ 2/ etc.",
        "max_tokens": 400,
    },
    "youtube_short_script": {
        "persona": "The YouTube Shorts Storyteller",
        "platform": "YouTube Shorts",
        "instructions": "Write a 60-second YouTube Short script. Hook in first 3 seconds. Conversational style. End with subscribe+comment CTA.",
        "max_tokens": 300,
    },
    "blog_outline": {
        "persona": "The SEO Blog Architect",
        "platform": "Blog / Medium",
        "instructions": "Write a full blog outline: H1 title + 5 H2 sections + 3 bullet points per section + conclusion note.",
        "max_tokens": 400,
    },
    "newsletter_intro": {
        "persona": "The Newsletter Writer",
        "platform": "Email Newsletter",
        "instructions": "Write an email newsletter intro (subject line + 80-word body). Conversational, curiosity-driven. End with 'Read on → '",
        "max_tokens": 200,
    },
    "whatsapp_promo": {
        "persona": "The WhatsApp Broadcast Copywriter",
        "platform": "WhatsApp / Broadcast",
        "instructions": "Write a WhatsApp promo message. Casual, warm. Max 100 words. Use emojis naturally. Add a clear link placeholder [LINK].",
        "max_tokens": 180,
    },
    "hindi_version": {
        "persona": "The Hindi Content Creator",
        "platform": "Hindi Social Media",
        "instructions": "Rewrite in engaging, casual Hinglish (Hindi + English mix). Keep it relatable to a mass Indian audience.",
        "max_tokens": 250,
    },
    "tamil_version": {
        "persona": "The Tamil Content Creator",
        "platform": "Tamil Social Media",
        "instructions": "Rewrite in Tamil-English blend (Tanglish). Warm, traditional but modern. Respect Tamil cultural nuances.",
        "max_tokens": 250,
    },
    "hook_variants": {
        "persona": "The Hook Laboratory",
        "platform": "Any Platform",
        "instructions": "Generate 5 different hook variants for this content. Types: Question Hook, Statistic Hook, Contrarian Hook, Story Hook, Fear/Pain Hook.",
        "max_tokens": 300,
    },
    "comment_bait": {
        "persona": "The Engagement Architect",
        "platform": "Comments Section",
        "instructions": "Write 3 comment-bait lines to pin or use as caption ending. Should naturally trigger replies. Example: 'What's your take — agree or completely wrong?' Format as numbered list.",
        "max_tokens": 150,
    },
}



# ─── Platform Compliance Rules (RL layer) ────────────────────────────────────

PLATFORM_COMPLIANCE_RULES = {
    "reel_script": {
        "max_chars": 1800,
        "required_patterns": ["["],       # action cues in brackets
        "required_keywords": [],
        "warn_missing": "Reel scripts should have visual action cues in [brackets].",
    },
    "carousel_copy": {
        "max_chars": 1500,
        "required_patterns": ["slide", "1"],  # slide markers
        "required_keywords": [],
        "warn_missing": "Carousel copy should have 5 numbered slides.",
    },
    "linkedin_article": {
        "max_chars": 3000,
        "required_patterns": [],
        "required_keywords": [],
        "warn_missing": None,
    },
    "tweet_thread": {
        "max_chars": 2000,
        "required_patterns": ["1/", "1."],   # thread numbering
        "required_keywords": [],
        "warn_missing": "Tweet threads should be numbered (1/ 2/ etc.).",
    },
    "youtube_short_script": {
        "max_chars": 2000,
        "required_patterns": [],
        "required_keywords": ["subscribe", "comment"],
        "warn_missing": "YouTube Shorts scripts should end with subscribe + comment CTA.",
    },
    "blog_outline": {
        "max_chars": 2500,
        "required_patterns": ["##", "h2", "section"],  # heading markers
        "required_keywords": [],
        "warn_missing": "Blog outlines should have H2 section headings.",
    },
    "newsletter_intro": {
        "max_chars": 600,
        "required_patterns": ["subject", "read on"],
        "required_keywords": [],
        "warn_missing": "Newsletter intros should include a subject line and 'Read on →'.",
    },
    "whatsapp_promo": {
        "max_chars": 700,
        "required_patterns": ["[link]", "http"],
        "required_keywords": [],
        "warn_missing": "WhatsApp promos should include a link placeholder [LINK].",
    },
    "hindi_version": {
        "max_chars": 1000,
        "required_patterns": [],
        "required_keywords": [],
        "warn_missing": None,
    },
    "tamil_version": {
        "max_chars": 1000,
        "required_patterns": [],
        "required_keywords": [],
        "warn_missing": None,
    },
    "hook_variants": {
        "max_chars": 1500,
        "required_patterns": ["1.", "2.", "3."],  # numbered variants
        "required_keywords": [],
        "warn_missing": "Hook variants should be numbered.",
    },
    "comment_bait": {
        "max_chars": 500,
        "required_patterns": ["1.", "?"],   # numbered + question
        "required_keywords": [],
        "warn_missing": "Comment bait should be numbered and contain a question.",
    },
}

# CTA keywords for checking presence across all assets
_CTA_KEYWORDS = ["follow", "click", "watch", "like", "share", "comment", "subscribe",
                 "check", "save", "dm", "link", "visit", "join"]


def _platform_compliance_score(content: str, asset_key: str) -> dict:
    """
    Rule-Based Platform Compliance Scorer (RL layer).

    Checks:
    - Character limit adherence     (−20 if over limit)
    - Required format patterns      (−10 per missing pattern)
    - Required keyword presence     (−10 per missing keyword)
    - CTA presence                  (−10 if no CTA found)
    - Minimum content length        (−15 if too short — likely generation failure)

    Returns compliance_score (0–100) + issues list.
    """
    rules = PLATFORM_COMPLIANCE_RULES.get(asset_key, {})
    score = 100
    issues = []

    # Character limit
    max_chars = rules.get("max_chars")
    if max_chars and len(content) > max_chars:
        score -= 20
        issues.append(f"Over character limit ({len(content)}/{max_chars})")

    # Minimum length (fail-safe for truncated or empty LLM output)
    if len(content.strip()) < 20:
        score -= 40
        issues.append("Content too short — likely generation incomplete")

    # Required patterns
    content_lower = content.lower()
    for pattern in rules.get("required_patterns", []):
        if pattern.lower() not in content_lower:
            score -= 10
            issues.append(f"Missing expected pattern: '{pattern}'")

    # Required keywords
    for kw in rules.get("required_keywords", []):
        if kw.lower() not in content_lower:
            score -= 10
            issues.append(f"Missing required keyword: '{kw}'")

    # CTA presence (universal check)
    has_cta = any(cta in content_lower for cta in _CTA_KEYWORDS)
    if not has_cta:
        score -= 10
        issues.append("No CTA detected")

    if rules.get("warn_missing"):
        # Check if the warning condition is relevant by seeing if pattern already satisfied
        pass  # already handled via required_patterns above

    score = max(0, min(100, score))
    return {"compliance_score": score, "issues": issues, "rule_provider": "platform_rules_v1"}


async def _generate_single_asset(
    seed_content: str,
    asset_key: str,
    niche: Optional[str],
    llm,
) -> dict:
    """
    Generate one platform-native asset.

    Hybrid RL + LLM pipeline:
    - LLM (65% weight): Generates the creative platform content
    - Rule Engine (35% weight): Validates platform compliance
    - quality_score = weighted blend of LLM baseline + rule compliance
    """
    asset = ASSET_PERSONAS[asset_key]
    prompt = f"""You are: {asset['persona']}
Platform: {asset['platform']}
{"Creator Niche: " + niche if niche else ""}

Seed Idea / Core Content:
{seed_content}

Task: {asset['instructions']}

Output (no explanations, no headers — just the content):"""

    LLM_WEIGHT  = 0.65
    RULE_WEIGHT = 0.35

    try:
        result = await llm.generate(prompt, task=f"asset_explosion_{asset_key}", max_tokens=asset["max_tokens"])
        generated_text = result["text"]

        # ── Rule-Based Compliance Check (RL layer) ──────────────────
        compliance_data = _platform_compliance_score(generated_text, asset_key)
        compliance_score = compliance_data["compliance_score"]

        # LLM baseline: assume 80 on success
        llm_baseline = 80 if generated_text and len(generated_text.strip()) > 20 else 30
        quality_score = int(llm_baseline * LLM_WEIGHT + compliance_score * RULE_WEIGHT)

        return {
            "asset_type":        asset_key,
            "platform":          asset["platform"],
            "content":           generated_text,
            "provider":          result["provider"],
            "rule_provider":     compliance_data["rule_provider"],
            "quality_score":     quality_score,
            "llm_score":         llm_baseline,
            "compliance_score":  compliance_score,
            "compliance_issues": compliance_data["issues"],
            "weights":           {"llm": LLM_WEIGHT, "rule_engine": RULE_WEIGHT},
            "success":           True,
        }
    except Exception as e:
        logger.error(f"Asset generation failed for {asset_key}: {e}")
        return {
            "asset_type":        asset_key,
            "platform":          asset["platform"],
            "content":           f"[Generation failed: {str(e)[:100]}]",
            "provider":          "error",
            "rule_provider":     "platform_rules_v1",
            "quality_score":     0,
            "llm_score":         0,
            "compliance_score":  0,
            "compliance_issues": [str(e)[:100]],
            "weights":           {"llm": LLM_WEIGHT, "rule_engine": RULE_WEIGHT},
            "success":           False,
        }



async def explode_to_12_assets(
    seed_content: str,
    niche: Optional[str] = None,
    selected_assets: Optional[list] = None,
) -> dict:
    """
    Generate 12 platform-native assets from one seed idea.
    Uses parallel async generation for speed.
    """
    llm = get_llm_service()
    
    asset_keys = selected_assets if selected_assets else list(ASSET_PERSONAS.keys())
    
    # Run all asset generations in parallel
    tasks = [
        _generate_single_asset(seed_content, key, niche, llm)
        for key in asset_keys
        if key in ASSET_PERSONAS
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=False)
    
    successful = [r for r in results if r["success"]]
    failed = [r["asset_type"] for r in results if not r["success"]]
    
    return {
        "seed_content": seed_content,
        "niche": niche,
        "total_assets": len(results),
        "successful_assets": len(successful),
        "failed_assets": failed,
        "assets": results,
    }


def get_available_asset_types() -> list:
    return [
        {"key": k, "platform": v["platform"], "persona": v["persona"]}
        for k, v in ASSET_PERSONAS.items()
    ]
