"""
Risk vs Reach Dial — Feature #2
AWS Comprehend (Sentiment/Toxicity) + AWS Bedrock Primary
Fallback: TextBlob + Gemini

Multi-agent feedback loop:
- Agent A: Generates content based on risk dial (0–100)
- Agent B: AWS Comprehend audits safety score
"""
import logging
from typing import Optional
from config import settings
from services.llm_service import get_llm_service

logger = logging.getLogger(__name__)


def _get_risk_prompt_instructions(risk_level: int) -> tuple[str, str]:
    """Map 0–100 risk level to content generation instructions."""
    if risk_level <= 25:
        tone = "SAFE"
        instructions = """- Use polished, brand-safe, professional language.
- Avoid controversy entirely. Stick to positive, universally acceptable phrasing.
- Use inclusive language. No polarizing angles.
- CTA should be soft and inviting, not pressuring."""
    elif risk_level <= 50:
        tone = "BALANCED"
        instructions = """- Use engaging, slightly opinionated language.
- You may introduce a mild contrarian viewpoint to spark discussion.
- Use conversational, relatable tone.
- CTA can be direct but not aggressive."""
    elif risk_level <= 75:
        tone = "BOLD"
        instructions = """- Use sharp, hook-driven, high-energy language.
- Introduce a bold or contrarian take. Challenge conventional wisdom.
- Use "Hot Take" style opening (e.g., "Everyone is wrong about…")
- CTA should be urgent and FOMO-inducing."""
    else:
        tone = "VIRAL"
        instructions = """- MAXIMUM IMPACT. Use bold, provocative, pattern-interrupting language.
- Use "Negative Constraint" style: ignore generic PR safety. Create shock value.
- The hook must be instantly shareable, even controversial.
- Sentence rhythm: short. Punchy. Frequent line breaks. Like a punch to the face.
- CTA: "This will change everything." Style urgency."""
    return tone, instructions


async def _aws_comprehend_safety_score(text: str) -> dict:
    """AWS Comprehend sentiment + toxicity check. Falls back to heuristics."""
    if settings.aws_configured and settings.use_aws_comprehend:
        try:
            import boto3
            client = boto3.client(
                "comprehend",
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
            )
            sentiment_result = client.detect_sentiment(Text=text, LanguageCode="en")
            sentiment = sentiment_result.get("Sentiment", "NEUTRAL")
            scores = sentiment_result.get("SentimentScore", {})

            # Toxicity check
            try:
                toxicity_result = client.detect_toxic_content(
                    TextSegments=[{"Text": text}],
                    LanguageCode="en",
                )
                toxicity_score = toxicity_result["ResultList"][0].get("Toxicity", 0) if toxicity_result.get("ResultList") else 0
            except Exception:
                toxicity_score = 0.0

            negative_score = scores.get("Negative", 0)
            safety_score = max(0, 100 - int(toxicity_score * 50) - int(negative_score * 30))

            return {
                "safety_score": safety_score,
                "sentiment": sentiment,
                "toxicity": round(toxicity_score, 4),
                "provider": "aws_comprehend",
            }
        except Exception as e:
            logger.warning(f"AWS Comprehend failed: {e}, using heuristic fallback")

    # Fallback: local heuristic
    try:
        from textblob import TextBlob
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity  # -1 to 1
        safety_score = int((polarity + 1) / 2 * 100)  # map to 0-100
        return {
            "safety_score": safety_score,
            "sentiment": "POSITIVE" if polarity > 0.1 else "NEGATIVE" if polarity < -0.1 else "NEUTRAL",
            "toxicity": 0.0,
            "provider": "textblob_fallback",
        }
    except Exception:
        return {"safety_score": 70, "sentiment": "NEUTRAL", "toxicity": 0.0, "provider": "heuristic"}


async def generate_risk_reach_content(
    content: str,
    risk_level: int,
    platform: Optional[str] = None,
    niche: Optional[str] = None,
) -> dict:
    """
    Generate content at the specified risk level (0–100).
    Runs safety audit via AWS Comprehend on the result.
    """
    risk_level = max(0, min(100, risk_level))
    tone_label, instructions = _get_risk_prompt_instructions(risk_level)

    prompt = f"""You are a strategic content creator calibrated for "{tone_label}" mode.

Original Content / Idea:
{content}

{"Platform: " + platform if platform else ""}
{"Niche: " + niche if niche else ""}

Risk Dial Level: {risk_level}/100 ({tone_label} mode)

Rewriting Instructions:
{instructions}

Generate the content now — one polished output, no commentary:"""

    llm = get_llm_service()
    result = await llm.generate(prompt, task="risk_reach_dial", max_tokens=400)
    generated_text = result["text"]

    # Run safety audit
    audit = await _aws_comprehend_safety_score(generated_text)

    # Estimate engagement probability (simple heuristic based on risk)
    engagement_probability = min(95, 40 + risk_level * 0.55)
    moderation_risk = min(95, risk_level * 0.7)

    return {
        "original": content,
        "generated": generated_text,
        "risk_level": risk_level,
        "tone_label": tone_label,
        "platform": platform,
        "safety_score": audit["safety_score"],
        "sentiment": audit["sentiment"],
        "toxicity_score": audit["toxicity"],
        "estimated_engagement_probability": round(engagement_probability, 1),
        "moderation_risk_percent": round(moderation_risk, 1),
        "llm_provider": result["provider"],
        "audit_provider": audit["provider"],
        "fallback_used": result["fallback_used"],
    }
