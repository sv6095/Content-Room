"""
Creator Mental Health Meter — Feature #6
AWS Comprehend (Sentiment over time) Primary
Fallback: TextBlob + local linguistic entropy analysis

Tracks "Linguistic Entropy" across recent posts to detect burnout.
"""
import logging
import math
import re
from typing import List
from services.llm_service import get_llm_service
from config import settings

logger = logging.getLogger(__name__)


def _linguistic_entropy(texts: List[str]) -> float:
    """
    Compute vocabulary diversity (Shannon entropy).
    Low entropy = restricted vocabulary = burnout marker.
    """
    all_words = []
    for t in texts:
        words = re.findall(r'\b[a-zA-Z]{3,}\b', t.lower())
        all_words.extend(words)

    if not all_words:
        return 0.0

    word_freq = {}
    for w in all_words:
        word_freq[w] = word_freq.get(w, 0) + 1

    total = len(all_words)
    entropy = -sum((c / total) * math.log2(c / total) for c in word_freq.values())
    return round(entropy, 4)


def _avg_sentiment(texts: List[str], provider: str = "local") -> dict:
    """Get average sentiment across posts. Local TextBlob fallback."""
    sentiments = []
    for text in texts:
        try:
            from textblob import TextBlob
            blob = TextBlob(text)
            sentiments.append(blob.sentiment.polarity)
        except Exception:
            sentiments.append(0.0)
    avg = sum(sentiments) / len(sentiments) if sentiments else 0.0
    return {"avg_polarity": round(avg, 4), "provider": "textblob"}


async def _aws_comprehend_batch_sentiment(texts: List[str]) -> dict:
    """Batch sentiment analysis using AWS Comprehend."""
    if settings.aws_configured and settings.use_aws_comprehend:
        try:
            import boto3
            client = boto3.client(
                "comprehend",
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
            )
            batch = [{"Index": i, "Text": t[:4900]} for i, t in enumerate(texts[:25])]
            response = client.batch_detect_sentiment(TextList=[b["Text"] for b in batch], LanguageCode="en")
            polarities = []
            for item in response.get("ResultList", []):
                scores = item.get("SentimentScore", {})
                polarity = scores.get("Positive", 0) - scores.get("Negative", 0)
                polarities.append(polarity)
            avg = sum(polarities) / len(polarities) if polarities else 0.0
            return {"avg_polarity": round(avg, 4), "provider": "aws_comprehend"}
        except Exception as e:
            logger.warning(f"AWS Comprehend batch sentiment failed: {e}")
    return _avg_sentiment(texts)


def _detect_repetitive_phrases(texts: List[str]) -> List[str]:
    """Detect repeated phrases/openers across posts — sign of creative stagnation."""
    phrase_count = {}
    for text in texts:
        # Extract first sentence or first 10 words
        opener = " ".join(text.split()[:8]).lower().strip(".,!?")
        phrase_count[opener] = phrase_count.get(opener, 0) + 1
    return [phrase for phrase, count in phrase_count.items() if count > 1]


async def analyze_mental_health(
    posts: List[str],
    user_id: int = 1,
) -> dict:
    """
    Analyze creator mental health from posting patterns.
    
    Returns:
        - burnout_risk: LOW / MEDIUM / HIGH
        - linguistic_entropy: diversity score
        - avg_sentiment: polarity trend
        - recommendations
    """
    if len(posts) < 5:
        return {
            "burnout_risk": "INSUFFICIENT_DATA",
            "message": "Need at least 5 posts to analyze mental health patterns.",
            "posts_analyzed": len(posts),
        }

    # Metrics
    entropy = _linguistic_entropy(posts)
    sentiment_data = await _aws_comprehend_batch_sentiment(posts)
    repetitive = _detect_repetitive_phrases(posts)

    # Burnout score (0-100)
    burnout_score = 0
    if entropy < 3.0:
        burnout_score += 40  # low vocabulary diversity
    elif entropy < 3.5:
        burnout_score += 20
    if sentiment_data["avg_polarity"] < -0.1:
        burnout_score += 30  # negative tone drift
    if len(repetitive) >= 2:
        burnout_score += 20  # repetitive openers
    if len(posts) >= 10 and entropy < 2.5:
        burnout_score += 10  # sustained low entropy (chronic burnout)

    risk_level = "HIGH" if burnout_score >= 60 else "MEDIUM" if burnout_score >= 35 else "LOW"

    # LLM advisory
    llm = get_llm_service()
    advisory_prompt = f"""You are a creator wellness advisor. Based on this analysis:
- Burnout Score: {burnout_score}/100
- Vocabulary Entropy (diversity): {entropy} (low = restricted vocabulary)
- Average Sentiment Polarity: {sentiment_data['avg_polarity']} (-1 negative, +1 positive)
- Repetitive Patterns Detected: {len(repetitive)}
- Posts Analyzed: {len(posts)}

Provide 3 short, actionable recommendations to protect this creator's mental health and creativity.
Be warm, not clinical. Use emoji sparingly.
Format: numbered list, max 2 sentences each."""
    advisory = await llm.generate(advisory_prompt, task="mental_health_advisory", max_tokens=300)

    return {
        "burnout_score": burnout_score,
        "burnout_risk": risk_level,
        "linguistic_entropy": entropy,
        "entropy_interpretation": (
            "LOW (burnout signal)" if entropy < 3.0 else
            "MEDIUM (some risk)" if entropy < 3.5 else
            "HEALTHY (good diversity)"
        ),
        "sentiment_polarity": sentiment_data["avg_polarity"],
        "sentiment_trend": (
            "NEGATIVE DRIFT ⚠️" if sentiment_data["avg_polarity"] < -0.1 else
            "NEUTRAL" if abs(sentiment_data["avg_polarity"]) <= 0.1 else
            "POSITIVE ✅"
        ),
        "repetitive_phrases_detected": repetitive[:5],
        "recommendations": advisory["text"],
        "posts_analyzed": len(posts),
        "sentiment_provider": sentiment_data["provider"],
        "advisory_provider": advisory["provider"],
    }
