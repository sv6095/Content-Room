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


async def _generate_single_asset(
    seed_content: str,
    asset_key: str,
    niche: Optional[str],
    llm,
) -> dict:
    """Generate one asset from the seed content."""
    asset = ASSET_PERSONAS[asset_key]
    prompt = f"""You are: {asset['persona']}
Platform: {asset['platform']}
{"Creator Niche: " + niche if niche else ""}

Seed Idea / Core Content:
{seed_content}

Task: {asset['instructions']}

Output (no explanations, no headers — just the content):"""

    try:
        result = await llm.generate(prompt, task=f"asset_explosion_{asset_key}", max_tokens=asset["max_tokens"])
        return {
            "asset_type": asset_key,
            "platform": asset["platform"],
            "content": result["text"],
            "provider": result["provider"],
            "success": True,
        }
    except Exception as e:
        logger.error(f"Asset generation failed for {asset_key}: {e}")
        return {
            "asset_type": asset_key,
            "platform": asset["platform"],
            "content": f"[Generation failed: {str(e)[:100]}]",
            "provider": "error",
            "success": False,
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
