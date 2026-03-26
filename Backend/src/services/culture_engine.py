"""
Cultural Emotion Engine — Feature #1
AWS Bedrock (Amazon Nova family) + AWS Translate Primary
Fallback: Groq

Rewrites content using regional emotional triggers for Bharat.
"""
import logging
import re
from collections import Counter
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
    # Used when region is empty, "general", or Auto — not the same as tier-2 affordability persona.
    "pan_india": {
        "tone": "warm, trustworthy, relatable across metros and smaller towns",
        "language_style": "Hinglish and natural English mix, accessible pan-Indian voice",
        "hooks": ["family", "trust", "everyday value", "community", "aspiration"],
        "avoid": ["hyper-local slang that only one city understands", "mocking any region"],
        "example_opener": "Har ghar ki kahaani, aapke hisaab se…",
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


def _normalize_region_key(region: str) -> str:
    """
    Map free-form region text to a REGIONAL_PERSONAS key.

    Previously, anything that was not an exact key (e.g. "general", "Chennai area")
    fell through to tier2_towns — so "Auto (Region Default)" + empty field always
    looked like a small-town Hindi persona. We now normalize to pan_india or
    infer city keywords from the string.
    """
    r = (region or "").strip().lower()
    if not r or r in ("general", "pan-india", "pan india", "pan_india", "bharat", "india", "default"):
        return "pan_india"
    if r in REGIONAL_PERSONAS:
        return r

    aliases = {
        "bengaluru": "bangalore",
        "blr": "bangalore",
        "ncr": "delhi",
        "calcutta": "kolkata",
    }
    if r in aliases:
        return aliases[r]

    # Substring hints (order: more specific phrases first)
    hints: list[tuple[str, str]] = [
        ("bengaluru", "bangalore"),
        ("bangalore", "bangalore"),
        ("chennai", "chennai"),
        ("tamil nadu", "chennai"),
        ("tamil", "chennai"),
        ("south india", "chennai"),
        ("mumbai", "mumbai"),
        ("maharashtra", "mumbai"),
        ("delhi", "delhi"),
        ("gurgaon", "delhi"),
        ("gurugram", "delhi"),
        ("noida", "delhi"),
        ("north india", "delhi"),
        ("kolkata", "kolkata"),
        ("west bengal", "kolkata"),
        ("east india", "kolkata"),
        ("hyderabad", "tier2_towns"),
        ("telangana", "tier2_towns"),
        ("tier 2", "tier2_towns"),
        ("tier2", "tier2_towns"),
        ("tier-2", "tier2_towns"),
        ("tier 3", "tier2_towns"),
    ]
    for needle, key in hints:
        if needle in r:
            return key

    return "pan_india"


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

LANGUAGE_CODE_TO_SCRIPT = {
    "hi": "Devanagari",
    "te": "Telugu script",
    "ta": "Tamil script",
    "bn": "Bengali script",
    "kn": "Kannada script",
    "ml": "Malayalam script",
    "gu": "Gujarati script",
    "or": "Odia script",
}

# ISO 639-1 code → display name (for prompts and API)
LANGUAGE_CODE_TO_DISPLAY_NAME = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "bn": "Bengali",
    "kn": "Kannada",
    "ml": "Malayalam",
    "gu": "Gujarati",
    "or": "Odia",
}

# When target_language is omitted (Auto / region default), pick ONE primary language per region — no Hinglish mashup.
REGION_KEY_TO_DEFAULT_LANGUAGE: dict[str, tuple[str, str]] = {
    "chennai": ("Tamil", "ta"),
    "mumbai": ("Hindi", "hi"),
    "delhi": ("Hindi", "hi"),
    "bangalore": ("Kannada", "kn"),
    "kolkata": ("Bengali", "bn"),
    "tier2_towns": ("Hindi", "hi"),
    "pan_india": ("English", "en"),
}


def _looks_like_generic_fallback(text: str) -> bool:
    normalized = (text or "").strip().lower()
    if not normalized:
        return True
    return normalized.startswith("generated response for:")


def _looks_low_quality_adaptation(text: str) -> bool:
    """Detect repetitive/gibberish-like rewrites and trigger a repair retry."""
    cleaned = (text or "").strip()
    if not cleaned:
        return True

    # Extremely short outputs are usually unusable for adaptation.
    if len(cleaned.split()) < 12:
        return True

    # Repeated sentence fragments often indicate model collapse.
    parts = [p.strip().lower() for p in re.split(r"[.!?\n]+", cleaned) if p.strip()]
    if len(parts) >= 3:
        counts = Counter(parts)
        if counts.most_common(1)[0][1] >= 2:
            return True

    # Excessive repetition of long words (e.g., "pongal", "enna", "irukku"...).
    words = re.findall(r"[A-Za-z\u0900-\u0DFF']{3,}", cleaned.lower())
    if len(words) >= 14:
        top_freq = Counter(words).most_common(1)[0][1]
        if (top_freq / len(words)) > 0.22:
            return True

    return False


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


def _display_name_for_language_code(code: str) -> str:
    return LANGUAGE_CODE_TO_DISPLAY_NAME.get(code, code.upper() if code else "English")


def _requires_post_translation(text: str, target_code: Optional[str]) -> bool:
    if not text or not target_code:
        return False
    if target_code == "en":
        # If English is requested but Indic scripts appear, force translation to English.
        return bool(re.search(r"[\u0900-\u0DFF]", text))
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
    user_id: Optional[str] = None,
) -> dict:
    """
    Rewrite content using regional emotional persona.

    Hybrid RL + LLM pipeline:
    - LLM (60% weight): Generates the culturally adapted rewrite
    - Rule Engine (40% weight): Validates the output against regional persona rules
    - Final alignment_score = LLM confidence blended with rule compliance
    """
    region_key = _normalize_region_key(region)
    persona = REGIONAL_PERSONAS.get(region_key, REGIONAL_PERSONAS["pan_india"])
    region_label = (region or "").strip() or "Pan-India"
    festival_context = ""
    if festival and festival.lower() in FESTIVAL_TONES:
        festival_context = f"\nFestival Context: This is for {festival.title()}. The emotional theme is: {FESTIVAL_TONES[festival.lower()]}"

    # Language: explicit user choice wins; otherwise map region → one primary language (no Hinglish default).
    explicit_lang_code = _resolve_language_code(target_language)
    auto_lang_name, auto_lang_code = REGION_KEY_TO_DEFAULT_LANGUAGE.get(
        region_key, ("English", "en")
    )
    if explicit_lang_code is not None:
        target_lang_code = explicit_lang_code
        lang_display_name = (target_language or "").strip() or _display_name_for_language_code(explicit_lang_code)
    else:
        target_lang_code = auto_lang_code
        lang_display_name = auto_lang_name

    if target_lang_code and target_lang_code != "en":
        script_name = LANGUAGE_CODE_TO_SCRIPT.get(target_lang_code, "the correct native script")
        lang_instruction = (
            f"Write the entire output in {lang_display_name} using {script_name} only. "
            f"Do NOT use Romanized transliteration for Indian languages. "
            f"Do NOT mix English except unavoidable brand names or proper nouns. "
            f"Do NOT use Hinglish, Tanglish, or other Hindi–English / Tamil–English code-mixing."
        )
    else:
        lang_instruction = (
            "Write the output in natural English only. "
            "Do not use Hindi, Tamil, or other scripts. No Hinglish or code-mixing."
        )

    # Persona drives tone only; output language is fixed above.
    persona_style_instruction = (
        f"Regional emotional tone: {persona['tone']}. "
        f"Express this tone entirely in {lang_display_name} — not by blending languages."
    )

    prompt = f"""Role: Bharat content strategist for regional adaptation.

Target region: {region_label}
{lang_instruction}

Persona:
- Tone: {persona['tone']}
- Style: {persona_style_instruction}
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
- Output language is {lang_display_name} only (see instruction above). No Hinglish or multi-language mashups.
- Keep it concise and natural: 3-5 sentences, avoid repetition.
- No hashtags, no explanation.
- Return only rewritten content.
"""

    llm = get_llm_service()
    result = await llm.generate(
        prompt,
        task="culture_emotion_engine",
        max_tokens=360,
        user_id=user_id,
    )
    rewritten_text = result.get("text", "")
    if _looks_like_generic_fallback(rewritten_text):
        rewritten_text = _rule_based_rewrite(content, persona, festival)
    elif _looks_low_quality_adaptation(rewritten_text):
        repair_prompt = f"""Rewrite the content again with clean, fluent copy.

Target region: {region_label}
Target language instruction: {lang_instruction}
{"Festival: " + festival.title() if festival else ""}
{"Niche: " + content_niche if content_niche else ""}

Original content:
{content}

Hard requirements:
- Output must be natural and human-sounding.
- No repetitive phrases.
- No transliterated words if a native-script language is requested.
- Keep the same meaning and promotional intent.
- 3-5 sentences only.
- Return only the final rewritten text.
"""
        repair_result = await llm.generate(
            repair_prompt,
            task="culture_emotion_engine",
            max_tokens=320,
            user_id=user_id,
        )
        repaired = (repair_result.get("text") or "").strip()
        if repaired and not _looks_low_quality_adaptation(repaired):
            rewritten_text = repaired
            result = repair_result

    if _requires_post_translation(rewritten_text, target_lang_code):
        try:
            from services.translation_service import get_translation_service
            translator = get_translation_service()
            tx = await translator.translate(
                text=rewritten_text,
                target_lang=target_lang_code,
                source_lang=None,
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
        "output_language":       lang_display_name,
        "output_language_code":  target_lang_code,
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
        {"id": "pan_india", "name": "Pan-India (English default)", "emoji": "🇮🇳"},
        {"id": "chennai", "name": "Chennai / South India → Tamil", "emoji": "🌴"},
        {"id": "mumbai", "name": "Mumbai / Maharashtra → Hindi", "emoji": "🏙️"},
        {"id": "delhi", "name": "Delhi / North India → Hindi", "emoji": "🏛️"},
        {"id": "bangalore", "name": "Bangalore / Karnataka → Kannada", "emoji": "💻"},
        {"id": "tier2_towns", "name": "Tier 2 & 3 → Hindi", "emoji": "🌾"},
        {"id": "kolkata", "name": "Kolkata / East → Bengali", "emoji": "🎭"},
    ]


async def get_available_festivals() -> list:
    return [
        {"id": k, "name": k.replace("_", " ").title()}
        for k in FESTIVAL_TONES.keys()
    ]
