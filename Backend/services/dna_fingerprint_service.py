"""
Content DNA Fingerprinting — Feature #3
AWS SageMaker (Object2Vec) + S3 Primary
Fallback: sentence-transformers (local)

Builds a vector "Style Centroid" from creator history.
Alerts if new content drifts > 30% from their brand voice.
"""
import logging
import json
import math
from typing import List, Optional
from config import settings
from services.llm_service import get_llm_service

logger = logging.getLogger(__name__)


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a ** 2 for a in vec_a))
    mag_b = math.sqrt(sum(b ** 2 for b in vec_b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _centroid(vectors: List[List[float]]) -> List[float]:
    """Compute the mean vector (centroid) of a list of vectors."""
    if not vectors:
        return []
    dim = len(vectors[0])
    return [sum(v[i] for v in vectors) / len(vectors) for i in range(dim)]


async def _embed_text(text: str) -> List[float]:
    """
    Generate text embeddings.
    Primary: AWS SageMaker endpoint (if configured).
    Fallback: sentence-transformers locally.
    """
    if settings.aws_configured:
        try:
            import boto3
            import json
            runtime = boto3.client(
                "sagemaker-runtime",
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
            )
            endpoint_name = "content-room-embeddings"
            payload = json.dumps({"inputs": text})
            response = runtime.invoke_endpoint(
                EndpointName=endpoint_name,
                ContentType="application/json",
                Body=payload,
            )
            result = json.loads(response["Body"].read())
            if isinstance(result, list):
                return result
        except Exception as e:
            logger.warning(f"SageMaker embedding failed: {e}, falling back to local")

    # Fallback: sentence-transformers
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        embedding = model.encode(text).tolist()
        return embedding
    except Exception as e:
        logger.warning(f"sentence-transformers failed: {e}, using simple TF-IDF fallback")

    # Ultimate fallback: character-frequency vector (very basic)
    chars = "abcdefghijklmnopqrstuvwxyz "
    freq = [text.lower().count(c) / max(len(text), 1) for c in chars]
    return freq


async def analyze_content_dna(
    new_content: str,
    post_history: List[str],
    user_id: Optional[int] = None,
) -> dict:
    """
    Fingerprint a creator's content DNA and check if new content drifts.

    Args:
        new_content: The new draft to check.
        post_history: List of past posts (top 10–20 recommended).
        user_id: For future S3 caching of embeddings.

    Returns:
        Dict with similarity score, drift alert, and style breakdown.
    """
    if not post_history:
        return {
            "similarity_score": 1.0,
            "drift_detected": False,
            "message": "Not enough history to build DNA fingerprint.",
            "provider": "none",
        }

    # Embed all posts
    history_vectors = []
    embed_provider = "local"
    for post in post_history[:20]:
        vec = await _embed_text(post)
        history_vectors.append(vec)

    # Build centroid (brand voice fingerprint)
    centroid = _centroid(history_vectors)

    # Embed new content
    new_vector = await _embed_text(new_content)

    # Measure similarity
    similarity = _cosine_similarity(centroid, new_vector)
    drift_detected = similarity < 0.70

    # Analyze style traits via LLM
    llm = get_llm_service()
    style_prompt = f"""Analyze the content style of these posts and describe the creator's "Content DNA" in 3 bullet points.
Focus on: Tone, Sentence Rhythm, CTA Style, Emotional Polarity.

Post samples:
{chr(10).join(post_history[:5])}

Content DNA (3 bullet points only, no headers):"""

    style_result = await llm.generate(style_prompt, task="dna_fingerprint", max_tokens=200)

    recommendation = ""
    if drift_detected:
        realign_prompt = f"""The creator's brand voice is: {style_result['text'][:300]}

Their new draft feels off-brand. Rewrite the following to realign with their Content DNA:
{new_content}

Realigned version (same message, correct voice):"""
        realign_result = await llm.generate(realign_prompt, task="dna_realign", max_tokens=400)
        recommendation = realign_result["text"]

    return {
        "similarity_score": round(similarity, 4),
        "drift_detected": drift_detected,
        "drift_severity": "HIGH" if similarity < 0.5 else "MEDIUM" if similarity < 0.7 else "NONE",
        "content_dna_traits": style_result["text"],
        "realignment_suggestion": recommendation,
        "posts_analyzed": len(history_vectors),
        "embedding_provider": embed_provider,
        "llm_provider": style_result["provider"],
    }
