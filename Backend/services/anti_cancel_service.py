"""
Anti-Cancel Shield — Feature #4
AWS Comprehend (Custom Entity Detection) + AWS Rekognition Primary
Fallback: spaCy + local keyword blacklist

Proactive reputation defense for the Indian digital landscape.
"""
import logging
from typing import List, Optional
from config import settings
from services.llm_service import get_llm_service

logger = logging.getLogger(__name__)

# ─── Universal Threat / Harm Keywords (platform-agnostic) ────────────────────
# These apply globally regardless of region. CRITICAL = immediate HIGH RISK.
UNIVERSAL_THREAT_KEYWORDS = {
    # Direct violence & murder threats
    "violence_threat": {
        "severity": "CRITICAL",
        "keywords": [
            "i will kill", "i am going to kill", "going to murder", "i will murder",
            "i am going to murder", "will hurt you", "going to hurt you",
            "i want to kill", "i want to murder", "planning to kill",
            "will shoot", "going to shoot", "will stab", "going to stab",
            "will beat you", "going to beat you", "i'll kill", "i'll murder",
            "kill yourself", "kys", "end your life", "hope you die",
            "you deserve to die", "going to attack", "will attack you",
            "death threat", "bomb threat", "will blow up",
        ],
    },
    # Standalone high-risk single words (must be matched as whole words to reduce false positives)
    "violence_words": {
        "severity": "HIGH",
        "keywords": [
            "murder", "assassinate", "massacre", "slaughter", "genocide",
            "beheading", "lynching", "rape", "molest",
        ],
    },
    # Hate speech & discrimination
    "hate_speech": {
        "severity": "HIGH",
        "keywords": [
            "all muslims are", "all hindus are", "all christians are",
            "all blacks are", "all whites are", "all jews are",
            "go back to your country", "you people should die",
            "ethnic cleansing", "white supremacy", "nazi", "heil hitler",
            "kill all", "death to all", "wipe out",
        ],
    },
    # Self-harm & suicide encouragement
    "self_harm": {
        "severity": "CRITICAL",
        "keywords": [
            "kill yourself", "kys", "you should die", "go commit suicide",
            "go hang yourself", "slit your wrists", "end it all",
            "better off dead", "no one would miss you",
        ],
    },
    # Sexual harassment / explicit threats
    "harassment": {
        "severity": "HIGH",
        "keywords": [
            "will find you", "i know where you live", "watch your back",
            "you better watch out", "you'll regret this", "i will destroy you",
            "doxxing", "swatting", "leak your nudes", "revenge porn",
        ],
    },
    # Extremism
    "extremism": {
        "severity": "CRITICAL",
        "keywords": [
            "jihad against", "holy war against", "infidels must die",
            "blow up the", "detonate", "suicide bomber", "terrorist attack",
            "recruit for", "join isis", "join al-qaeda",
        ],
    },
}

# Severity score weights
SEVERITY_WEIGHTS = {
    "CRITICAL": 50,   # 1 match → instantly HIGH RISK (score ≥ 50)
    "HIGH":     25,   # 2 matches → HIGH RISK
    "MEDIUM":   12,
    "LOW":       6,
}

# Regional sensitivity blacklist for India (cultural / political)
INDIA_SENSITIVITY_KEYWORDS = {
    "religious": [
        "cow slaughter", "beef ban protest", "temple destruction", "mosque demolition",
        "church demolition", "forced conversion", "blasphemy against",
        "religious riots", "communal violence",
    ],
    "political": [
        "sedition", "anti-national", "treason", "jai shri ram fight",
        "bharat mata ki jai forced", "election rigging india",
    ],
    "caste": [
        "upper caste supremacy", "lower caste insult", "dalit slur",
        "brahmin hate", "caste discrimination",
    ],
    "regional": [
        "south india lazy", "north india aggression", "bhaiyya insult",
        "marathi vs bihari", "outsider ban",
    ],
    "misinformation": [
        "vaccines cause death india", "5g causes corona",
        "government is poisoning", "fake encounter",
    ],
}



async def _aws_entity_detection(text: str) -> dict:
    """AWS Comprehend custom entity + PII detection."""
    if settings.aws_configured and settings.use_aws_comprehend:
        try:
            import boto3
            client = boto3.client(
                "comprehend",
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
            )
            entities = client.detect_entities(Text=text, LanguageCode="en")
            key_phrases = client.detect_key_phrases(Text=text, LanguageCode="en")

            detected_entities = [
                {"text": e["Text"], "type": e["Type"], "score": round(e["Score"], 3)}
                for e in entities.get("Entities", [])
                if e["Score"] > 0.8
            ]
            detected_phrases = [
                kp["Text"] for kp in key_phrases.get("KeyPhrases", [])
                if kp["Score"] > 0.7
            ]
            return {
                "entities": detected_entities,
                "key_phrases": detected_phrases,
                "provider": "aws_comprehend",
            }
        except Exception as e:
            logger.warning(f"AWS Comprehend entity detection failed: {e}")

    # Fallback: spaCy
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text)
        entities = [{"text": ent.text, "type": ent.label_, "score": 0.7} for ent in doc.ents]
        return {"entities": entities, "key_phrases": [], "provider": "spacy_fallback"}
    except Exception:
        return {"entities": [], "key_phrases": [], "provider": "none"}


def _local_sensitivity_scan(text: str) -> List[dict]:
    """
    Two-tier sensitivity scan:
    Tier 1 — Universal threat/harm keywords (violence, hate, self-harm, extremism)
    Tier 2 — India-specific cultural/political sensitivity keywords

    Returns list of flag dicts with 'keyword', 'category', 'severity', 'risk'.
    """
    text_lower = text.lower()
    flags = []

    # ── Tier 1: Universal threats (checked first — highest priority) ──────────
    for category, meta in UNIVERSAL_THREAT_KEYWORDS.items():
        severity = meta["severity"]
        for kw in meta["keywords"]:
            if kw.lower() in text_lower:
                flags.append({
                    "keyword":  kw,
                    "category": category,
                    "severity": severity,
                    "risk":     severity,          # CRITICAL / HIGH
                    "tier":     "universal",
                })

    # ── Tier 2: India-specific cultural/political triggers ────────────────────
    for category, keywords in INDIA_SENSITIVITY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                flags.append({
                    "keyword":  kw,
                    "category": category,
                    "severity": "HIGH",
                    "risk":     "HIGH",
                    "tier":     "india_specific",
                })

    return flags


def _compute_rule_risk_score(flags: List[dict]) -> int:
    """
    Compute weighted risk score from sensitivity flags.
    CRITICAL flags: +50 each (1 hit = HIGH RISK threshold)
    HIGH flags:     +25 each
    Score capped at 100.
    """
    score = 0
    for flag in flags:
        weight = SEVERITY_WEIGHTS.get(flag.get("severity", "HIGH"), 25)
        score += weight
    return min(100, score)




async def analyze_cancel_risk(
    text: str,
    target_regions: Optional[List[str]] = None,
) -> dict:
    """
    Analyze content for cancel/controversy risk.

    Two-tier RL + LLM hybrid pipeline:
    Tier 1 (RL): Universal threat keywords (violence, hate, self-harm, extremism)
    Tier 2 (RL): India-specific cultural/political sensitivity keywords
    LLM: Contextual rewrite suggestions and deeper risk understanding
    """
    # Entity detection (AWS Comprehend or spaCy fallback)
    entity_result = await _aws_entity_detection(text)

    # Two-tier keyword scan
    local_flags = _local_sensitivity_scan(text)

    # Separate universal threats from India-specific cultural flags
    universal_flags = [f for f in local_flags if f.get("tier") == "universal"]
    india_flags     = [f for f in local_flags if f.get("tier") == "india_specific"]

    # Weighted risk score from rule engine
    rule_risk_score = _compute_rule_risk_score(local_flags)

    # Add a small entity-based bump (AWS Comprehend / spaCy)
    entity_bump = min(20, len(entity_result["entities"]) * 3)
    risk_score = min(100, rule_risk_score + entity_bump)

    # Enforce minimum of 5 (never absolute zero — LLM may catch things rules missed)
    if risk_score == 0:
        risk_score = 5

    # ── Build heatmap (word-level coloring) ──────────────────────────────────
    words = text.split()
    critical_keywords = {f["keyword"].lower() for f in local_flags if f.get("severity") == "CRITICAL"}
    high_keywords     = {f["keyword"].lower() for f in local_flags if f.get("severity") == "HIGH"}
    entity_texts      = {e["text"].lower() for e in entity_result["entities"] if e["type"] in ["PERSON", "ORGANIZATION", "LOCATION"]}

    heatmap = []
    for word in words:
        word_lower = word.lower().strip(".,!?;:\"'")
        if any(kw in word_lower or word_lower in kw for kw in critical_keywords):
            heatmap.append({"word": word, "risk": "red", "tooltip": "⛔ Critical threat detected"})
        elif any(kw in word_lower or word_lower in kw for kw in high_keywords):
            heatmap.append({"word": word, "risk": "red", "tooltip": "⚠️ High-risk term"})
        elif any(et in word_lower for et in entity_texts):
            heatmap.append({"word": word, "risk": "yellow", "tooltip": "Flagged entity"})
        else:
            heatmap.append({"word": word, "risk": "safe", "tooltip": None})

    # ── LLM: Contextual analysis + safe alternatives ──────────────────────────
    llm = get_llm_service()
    alternatives = []
    has_critical = any(f.get("severity") == "CRITICAL" for f in local_flags)

    if local_flags or risk_score > 30:
        flag_summary = [
            f"{f['keyword']} (category: {f['category']}, severity: {f.get('severity', 'HIGH')})"
            for f in local_flags[:6]
        ]
        alt_prompt = f"""You are an expert in social media content safety and Indian digital sensitivity.

This content has been flagged by our rule engine:
Flags: {flag_summary}
Risk Score: {risk_score}/100

Original content:
{text}

{'⚠️ CRITICAL: This content contains threat or violence language that is platform-unsafe.' if has_critical else 'This content may be culturally or regionally sensitive in India.'}

Provide:
1. A safe rewritten version preserving the core message
2. Two alternative phrasings for the risky sections
3. One sentence explaining why this is risky

Format:
SAFE VERSION: [rewritten text]
ALT 1: [alternative phrase]
ALT 2: [alternative phrase]
WHY: [explanation]"""
        alt_result = await llm.generate(alt_prompt, task="anti_cancel", max_tokens=500)
        alternatives = [alt_result["text"]]

    # ── Recommendation message ────────────────────────────────────────────────
    if has_critical:
        recommendation = "🚨 CRITICAL: Content contains threat/violence language. Do NOT post — this will be actioned by platform trust & safety."
    elif risk_score >= 60:
        recommendation = "⚠️ High sensitivity detected. Review flagged sections before posting."
    elif risk_score >= 30:
        recommendation = "⚡ Moderate risk. Consider revising the flagged phrases."
    else:
        recommendation = "✅ Content appears safe."

    return {
        "risk_score":          risk_score,
        "risk_level":          "HIGH" if risk_score >= 60 else "MEDIUM" if risk_score >= 30 else "LOW",
        "local_flags":         local_flags,
        "universal_flags":     universal_flags,
        "india_flags":         india_flags,
        "detected_entities":   entity_result["entities"][:10],
        "heatmap":             heatmap,
        "safe_alternatives":   alternatives,
        "target_regions":      target_regions or ["pan-india"],
        "comprehend_provider": entity_result["provider"],
        "recommendation":      recommendation,
        "has_critical_threat": has_critical,
    }


async def get_heatmap_for_text(text: str) -> List[dict]:
    """Stream word-level sensitivity heatmap for the Studio editor."""
    local_flags = _local_sensitivity_scan(text)
    flagged_keywords = {f["keyword"].lower() for f in local_flags}

    words = text.split()
    heatmap = []
    for word in words:
        clean = word.lower().strip(".,!?;:\"'")
        if clean in flagged_keywords or any(kw in clean for kw in flagged_keywords):
            heatmap.append({"word": word, "risk": "red", "tooltip": "Potentially sensitive in Indian context"})
        else:
            heatmap.append({"word": word, "risk": "safe", "tooltip": None})
    return heatmap
