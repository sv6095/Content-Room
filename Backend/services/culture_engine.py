"""
Cultural Emotion Engine — Feature #1
AWS Bedrock (Claude 3.5 Sonnet) + AWS Translate Primary
Fallback: Gemini Pro API

Rewrites content using regional emotional triggers for Bharat.
"""
import logging
from typing import Optional
from config import settings
from services.llm_service import get_llm_service

logger = logging.getLogger(__name__)

# Regional persona metadata for Bharat
REGIONAL_PERSONAS = {
    "chennai": {
        "tone": "tradition-first, devotional, family-centric",
        "language_style": "Tamil-English blend (Tanglish)",
        "hooks": ["family values", "tradition", "devotion", "community"],
        "avoid": ["glam", "party", "nightlife"],
        "example_opener": "En kutumbam muyarchi seiyum – My family always tries…",
    },
    "mumbai": {
        "tone": "aspirational, fast-paced, glam, hustle culture",
        "language_style": "Hinglish, urban slang",
        "hooks": ["ambition", "luxury", "grind", "boss energy"],
        "avoid": ["conservative phrasing", "slow-paced content"],
        "example_opener": "Mumbai never sleeps and neither do we…",
    },
    "delhi": {
        "tone": "bold, confident, politically aware, status-conscious",
        "language_style": "Hinglish, street-smart",
        "hooks": ["power", "status", "pride", "national identity"],
        "avoid": ["self-deprecating humor"],
        "example_opener": "Dilli ka dil bolta hai…",
    },
    "bangalore": {
        "tone": "tech-forward, startup culture, innovation, work-life balance",
        "language_style": "English-dominant, startup slang",
        "hooks": ["innovation", "efficiency", "scale", "disruption"],
        "avoid": ["traditional or rural references"],
        "example_opener": "Building the future, one commit at a time…",
    },
    "tier2_towns": {
        "tone": "affordability, community, utility, long-term value",
        "language_style": "Hindi, regional warmth",
        "hooks": ["savings", "family", "local pride", "smart buying"],
        "avoid": ["luxury", "aspirational excess"],
        "example_opener": "Ghar ki zaroorat, smart khareedari…",
    },
    "kolkata": {
        "tone": "intellectual, cultural pride, poetic, artistic",
        "language_style": "Benglish (Bengali-English blend)",
        "hooks": ["culture", "arts", "heritage", "intellectualism"],
        "avoid": ["overly commercial tone"],
        "example_opener": "Kolkata mane culture, creativity, connection…",
    },
}

FESTIVAL_TONES = {
    "diwali": "celebration, light over darkness, prosperity, family reunion",
    "eid": "gratitude, brotherhood, sharing, peace",
    "christmas": "joy, giving, warmth, community celebration",
    "holi": "colors, playfulness, forgiveness, new beginnings",
    "pongal": "harvest gratitude, family, Tamil tradition, abundance",
    "durga_puja": "feminine power, cultural pride, festivity, new clothes",
    "onam": "Kerala harvest, unity, simplicity, prosperity",
}


async def rewrite_for_region(
    content: str,
    region: str,
    festival: Optional[str] = None,
    content_niche: Optional[str] = None,
) -> dict:
    """
    Rewrite content using regional emotional persona.
    AWS Bedrock primary → Gemini fallback.
    """
    persona = REGIONAL_PERSONAS.get(region.lower(), REGIONAL_PERSONAS["tier2_towns"])
    festival_context = ""
    if festival and festival.lower() in FESTIVAL_TONES:
        festival_context = f"\nFestival Context: This is for {festival.title()}. The emotional theme is: {FESTIVAL_TONES[festival.lower()]}"

    prompt = f"""You are a master Bharat content strategist specializing in regional emotional adaptation.

Rewrite the following content for a creator targeting the **{region.title()}** audience.

Regional Persona Profile:
- Tone: {persona['tone']}
- Language Style: {persona['language_style']}
- Emotional Hooks to use: {', '.join(persona['hooks'])}
- Avoid: {', '.join(persona['avoid'])}
{festival_context}
{"Niche: " + content_niche if content_niche else ""}

Original Content:
{content}

Rewrite Rules:
1. Keep the CORE MESSAGE identical — only adapt the emotional wrapper.
2. Use the regional language style naturally (don't translate, just adapt the emotion).
3. Start with a hook relevant to the region.
4. Do NOT add hashtags — the creator will add them separately.
5. Return ONLY the rewritten content, no explanations.

Rewritten Content:"""

    llm = get_llm_service()
    result = await llm.generate(prompt, task="culture_emotion_engine", max_tokens=512)

    return {
        "original": content,
        "rewritten": result["text"],
        "region": region,
        "persona_applied": persona["tone"],
        "festival": festival,
        "provider": result["provider"],
        "fallback_used": result["fallback_used"],
    }


async def get_available_regions() -> list:
    return [
        {"id": "chennai", "name": "Chennai / South India", "emoji": "🌴"},
        {"id": "mumbai", "name": "Mumbai / Maharashtra", "emoji": "🏙️"},
        {"id": "delhi", "name": "Delhi / North India", "emoji": "🏛️"},
        {"id": "bangalore", "name": "Bangalore / Tech Belt", "emoji": "💻"},
        {"id": "tier2_towns", "name": "Tier 2 & 3 Towns", "emoji": "🌾"},
        {"id": "kolkata", "name": "Kolkata / East India", "emoji": "🎭"},
    ]


async def get_available_festivals() -> list:
    return [
        {"id": k, "name": k.replace("_", " ").title()}
        for k in FESTIVAL_TONES.keys()
    ]
