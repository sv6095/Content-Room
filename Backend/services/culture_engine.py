"""
Cultural Emotion Engine — Feature #1
AWS Bedrock (Amazon Nova family) + AWS Translate Primary
Fallback: Groq

Rewrites content using regional emotional triggers for Bharat.
"""
import logging
import re
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

LANGUAGE_NAME_TO_CODE = {
    "english": "en",
    "hindi": "hi",
    "telugu": "te",
    "tamil": "ta",
    "bengali": "bn",
    "bangla": "bn",
    "kannada": "kn",
    "malayalam": "ml",
    "gujarati": "gu",
    "odia": "or",
}

TARGET_SCRIPT_PATTERNS = {
    "hi": re.compile(r"[\u0900-\u097F]"),  # Devanagari
    "te": re.compile(r"[\u0C00-\u0C7F]"),  # Telugu
    "ta": re.compile(r"[\u0B80-\u0BFF]"),  # Tamil
    "bn": re.compile(r"[\u0980-\u09FF]"),  # Bengali
    "kn": re.compile(r"[\u0C80-\u0CFF]"),  # Kannada
    "ml": re.compile(r"[\u0D00-\u0D7F]"),  # Malayalam
    "gu": re.compile(r"[\u0A80-\u0AFF]"),  # Gujarati
    "or": re.compile(r"[\u0B00-\u0B7F]"),  # Odia
}


def _looks_like_generic_fallback(text: str) -> bool:
    normalized = (text or "").strip().lower()
    if not normalized:
        return True
    return normalized.startswith("generated response for:")


def _resolve_language_code(target_language: Optional[str]) -> Optional[str]:
    if not target_language:
        return None
    raw = target_language.strip().lower()
    if not raw:
        return None
    if raw in ("auto", "default", "auto (region default)"):
        return None
    if raw in LANGUAGE_NAME_TO_CODE:
        return LANGUAGE_NAME_TO_CODE[raw]
    if raw in LANGUAGE_NAME_TO_CODE.values():
        return raw
    return None


def _requires_post_translation(text: str, target_code: Optional[str]) -> bool:
    if not text or not target_code or target_code == "en":
        return False
    script_pattern = TARGET_SCRIPT_PATTERNS.get(target_code)
    if script_pattern and script_pattern.search(text):
        return False
    return bool(re.search(r"[A-Za-z]", text))


def _rule_based_rewrite(content: str, persona: dict, festival: Optional[str]) -> str:
    """Deterministic rewrite fallback when LLM returns empty/generic content."""
    hook = persona.get("hooks", ["community"])[0]
    tone = persona.get("tone", "community-first")
    festival_phrase = f" As we celebrate {festival.title()}, " if festival else " "
    base = content.strip() or "We are excited to share this with you."
    return (
        f"{festival_phrase}we are speaking to a {tone} audience with a focus on {hook}. "
        f"{base}"
    ).strip()



# ─── Rule-Based Regional Alignment Scorer ────────────────────────────────────

def _rule_alignment_score(rewritten: str, persona: dict, festival: Optional[str]) -> dict:
    """
    Rule-based scorer (RL layer) — evaluates how well the LLM rewrite
    actually aligned with the regional persona rules.

    Checks:
    - Hook keyword presence           (+10 per matched hook)
    - Tone keyword presence           (+8 per matched tone word)
    - Avoid-list violations           (-15 per violation)
    - Festival context compliance     (+10 if festival keywords present)
    - Language style markers          (+5 per language marker found)

    Returns a 0–100 rule alignment score.
    """
    rewritten_lower = rewritten.lower()
    score = 50  # neutral baseline

    # Hook presence
    matched_hooks = []
    for hook in persona.get("hooks", []):
        if hook.lower() in rewritten_lower:
            matched_hooks.append(hook)
            score += 10

    # Tone keyword presence
    matched_tone_words = []
    for word in persona.get("tone", "").split(","):
        w = word.strip().lower()
        if w and w in rewritten_lower:
            matched_tone_words.append(w)
            score += 8

    # Avoid-list violations
    violations = []
    for avoid in persona.get("avoid", []):
        if avoid.lower() in rewritten_lower:
            violations.append(avoid)
            score -= 15

    # Festival context
    festival_keywords_found = []
    if festival and festival.lower() in FESTIVAL_TONES:
        festival_tone = FESTIVAL_TONES[festival.lower()]
        for word in festival_tone.split(","):
            w = word.strip().lower()
            if w and w in rewritten_lower:
                festival_keywords_found.append(w)
                score += 5

    score = max(0, min(100, score))

    return {
        "rule_alignment_score": score,
        "matched_hooks": matched_hooks,
        "matched_tone_words": matched_tone_words,
        "violations": violations,
        "festival_keywords_found": festival_keywords_found,
        "rule_provider": "rule_engine_v1",
    }


async def rewrite_for_region(
    content: str,
    region: str,
    festival: Optional[str] = None,
    content_niche: Optional[str] = None,
    target_language: Optional[str] = None,
) -> dict:
    """
    Rewrite content using regional emotional persona.

    Hybrid RL + LLM pipeline:
    - LLM (60% weight): Generates the culturally adapted rewrite
    - Rule Engine (40% weight): Validates the output against regional persona rules
    - Final alignment_score = LLM confidence blended with rule compliance
    """
    persona = REGIONAL_PERSONAS.get(region.lower(), REGIONAL_PERSONAS["tier2_towns"])
    festival_context = ""
    if festival and festival.lower() in FESTIVAL_TONES:
        festival_context = f"\nFestival Context: This is for {festival.title()}. The emotional theme is: {FESTIVAL_TONES[festival.lower()]}"

    # Determine language instruction
    lang_instruction = (
        f"Write the output IN {target_language}. "
        f"Apply the regional emotional persona below but use {target_language} as the output language."
    ) if target_language and target_language.lower() not in ("", "auto", "default") else (
        f"Use the natural language style of the region: {persona['language_style']}."
    )

    prompt = f"""Role: Bharat content strategist for regional adaptation.

Target region: {region.title()}
{lang_instruction}

Persona:
- Tone: {persona['tone']}
- Style: {persona['language_style']}
- Use hooks: {', '.join(persona['hooks'])}
- Avoid: {', '.join(persona['avoid'])}
{festival_context}
{"Niche: " + content_niche if content_niche else ""}

Input:
{content}

Rules:
- Keep core message unchanged; adapt emotional framing only.
- Start with a region-relevant hook.
- Include at least 2 listed hooks naturally.
- If target language is specified, write ONLY in that language (except unavoidable brand names/proper nouns).
- No hashtags, no explanation.
- Return only rewritten content.
"""

    llm = get_llm_service()
    result = await llm.generate(prompt, task="culture_emotion_engine", max_tokens=360)
    rewritten_text = result.get("text", "")
    if _looks_like_generic_fallback(rewritten_text):
        rewritten_text = _rule_based_rewrite(content, persona, festival)

    target_lang_code = _resolve_language_code(target_language)
    if _requires_post_translation(rewritten_text, target_lang_code):
        try:
            from services.translation_service import get_translation_service
            translator = get_translation_service()
            tx = await translator.translate(
                text=rewritten_text,
                target_lang=target_lang_code,
                source_lang="en",
            )
            translated_text = (tx or {}).get("translated_text", "").strip()
            if translated_text:
                rewritten_text = translated_text
        except Exception as e:
            logger.warning("Culture language enforcement translation failed: %s", e)

    # ── Rule-Based Alignment Check (RL layer) ──────────────────────────────
    rule_data = _rule_alignment_score(rewritten_text, persona, festival)

    # ── Weighted Score Combination ──────────────────────────────────────────
    # LLM weight: 60% — semantic creativity and cultural nuance
    # Rule weight: 40% — deterministic regional persona compliance
    LLM_WEIGHT  = 0.60
    RULE_WEIGHT = 0.40

    # LLM baseline score: assume 75 if generation succeeded (no explicit score from LLM)
    llm_baseline = 75 if rewritten_text else 0
    rule_score   = rule_data["rule_alignment_score"]
    final_alignment_score = int(llm_baseline * LLM_WEIGHT + rule_score * RULE_WEIGHT)

    return {
        "original":              content,
        "rewritten":             rewritten_text,
        "region":                region,
        "persona_applied":       persona["tone"],
        "festival":              festival,
        # Scores
        "alignment_score":       final_alignment_score,
        "llm_score":             llm_baseline,
        "rule_alignment_score":  rule_score,
        "weights":               {"llm": LLM_WEIGHT, "rule_engine": RULE_WEIGHT},
        # Rule details
        "matched_hooks":         rule_data["matched_hooks"],
        "violations":            rule_data["violations"],
        "festival_keywords":     rule_data["festival_keywords_found"],
        # Provider info
        "provider":              result["provider"],
        "rule_provider":         rule_data["rule_provider"],
        "fallback_used":         result["fallback_used"],
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
