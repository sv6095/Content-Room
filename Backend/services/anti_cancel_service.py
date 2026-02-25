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

# Regional sensitivity blacklist for India
INDIA_SENSITIVITY_KEYWORDS = {
    "religious": [
        "cow slaughter", "beef", "pork", "temple destruction", "mosque",
        "church demolition", "conversion", "blasphemy",
    ],
    "political": [
        "sedition", "anti-national", "treason", "jai shri ram fight",
        "bharat mata ki jai forced",
    ],
    "caste": [
        "upper caste supremacy", "lower caste insult", "dalit slur",
        "brahmin hate", "kshatriya",
    ],
    "regional": [
        "south india lazy", "north india aggression", "bihari", "bhaiyya insult",
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
    """Scan text against local India-specific sensitivity keyword list."""
    text_lower = text.lower()
    flags = []
    for category, keywords in INDIA_SENSITIVITY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                flags.append({"keyword": kw, "category": category, "risk": "HIGH"})
    return flags


async def analyze_cancel_risk(
    text: str,
    target_regions: Optional[List[str]] = None,
) -> dict:
    """
    Analyze content for cancel/controversy risk across Indian regions.
    Returns risk score, flagged entities, and alternative phrasings.
    """
    # Entity detection
    entity_result = await _aws_entity_detection(text)

    # Local keyword scan
    local_flags = _local_sensitivity_scan(text)

    # Compute overall risk score
    risk_score = min(100, len(local_flags) * 20 + len(entity_result["entities"]) * 5)
    if risk_score == 0:
        risk_score = 5  # baseline minimum

    # Build heatmap tokens
    words = text.split()
    flagged_keywords = [f["keyword"] for f in local_flags]
    heatmap = []
    for word in words:
        risk_level = "safe"
        if any(kw in word.lower() for kw in flagged_keywords):
            risk_level = "red"
        elif any(e["text"].lower() in word.lower() for e in entity_result["entities"] if e["type"] in ["PERSON", "ORGANIZATION", "LOCATION"]):
            risk_level = "yellow"
        heatmap.append({"word": word, "risk": risk_level})

    # LLM: alternative phrasings
    llm = get_llm_service()
    alternatives = []
    if local_flags or risk_score > 30:
        alt_prompt = f"""You are an expert in Indian digital content sensitivity.

The following content has been flagged for potential controversy in the Indian social media landscape.
Flags found: {[f['keyword'] + ' (' + f['category'] + ')' for f in local_flags][:5]}

Original content:
{text}

Rewrite this content to be culturally safe while preserving the core message.
Also suggest 2 alternative safe phrasings for the risky sections.

Format:
SAFE VERSION: [rewritten text]
ALT 1: [alternative phrase]
ALT 2: [alternative phrase]"""
        alt_result = await llm.generate(alt_prompt, task="anti_cancel", max_tokens=400)
        alternatives = [alt_result["text"]]

    return {
        "risk_score": risk_score,
        "risk_level": "HIGH" if risk_score >= 60 else "MEDIUM" if risk_score >= 30 else "LOW",
        "local_flags": local_flags,
        "detected_entities": entity_result["entities"][:10],
        "heatmap": heatmap,
        "safe_alternatives": alternatives,
        "target_regions": target_regions or ["pan-india"],
        "comprehend_provider": entity_result["provider"],
        "recommendation": (
            "⚠️ High cultural sensitivity detected. Review before posting."
            if risk_score >= 60 else
            "✅ Content appears regionally safe."
        ),
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
