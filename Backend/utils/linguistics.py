"""
Linguistic Analysis Utilities — Content Room
=============================================
Shared NLP primitives used by both Mental Health Meter and Burnout Predictor.
Extracted to avoid duplication of entropy/sentiment/repetition logic.
"""
import math
import re
from collections import Counter
from typing import List, Dict


# ─── Shannon Entropy (Vocabulary Diversity) ────────────────
def compute_linguistic_entropy(texts: List[str]) -> float:
    """
    Shannon entropy over word distribution across one or more texts.
    Low entropy ⇒ restricted vocabulary ⇒ potential creative burnout signal.

    Returns normalised value in [0, 1] when `normalise=True` (default below),
    or raw entropy in bits otherwise.
    """
    all_words = re.findall(r'\b[a-zA-Z]{3,}\b', " ".join(texts).lower())
    if not all_words:
        return 0.0

    freq = Counter(all_words)
    total = len(all_words)
    entropy = -sum((c / total) * math.log2(c / total) for c in freq.values())
    return round(entropy, 4)


def compute_normalised_entropy(texts: List[str]) -> float:
    """Entropy scaled to [0 .. 1] by dividing by log₂(vocab size)."""
    all_words = re.findall(r'\b[a-zA-Z]{3,}\b', " ".join(texts).lower())
    if not all_words:
        return 0.0

    freq = Counter(all_words)
    total = len(all_words)
    raw = -sum((c / total) * math.log2(c / total) for c in freq.values())
    ceiling = math.log2(len(freq)) if freq else 1
    return round(raw / ceiling, 4) if ceiling > 0 else 0.0


# ─── Repetition Index ──────────────────────────────────────
def compute_repetition_index(texts: List[str]) -> float:
    """
    1 − (unique_words / total_words).
    Higher value → more word reuse → creative fatigue indicator.
    """
    words = " ".join(texts).lower().split()
    if not words:
        return 0.0
    return round(1 - len(set(words)) / len(words), 4)


# ─── Repeated Openers ──────────────────────────────────────
def detect_repeated_openers(texts: List[str], opener_length: int = 8) -> List[str]:
    """
    Extract the first `opener_length` words of each text and flag those
    that appear in two or more posts (stale creative pattern).
    """
    counts: Dict[str, int] = {}
    for text in texts:
        opener = " ".join(text.split()[:opener_length]).lower().strip(".,!?")
        counts[opener] = counts.get(opener, 0) + 1
    return [phrase for phrase, n in counts.items() if n > 1]


# ─── Simple Sentiment Ratio ────────────────────────────────
# Positive/negative word-list approach — used as a lightweight local fallback
# when TextBlob or AWS Comprehend are unavailable.
_POSITIVE = frozenset([
    "love", "amazing", "great", "happy", "excited", "awesome",
    "beautiful", "incredible", "fantastic", "wonderful",
])
_NEGATIVE = frozenset([
    "bad", "worst", "hate", "terrible", "awful", "boring",
    "annoyed", "angry", "frustrated", "horrible",
])


def sentiment_word_ratio(texts: List[str]) -> float:
    """
    Returns positive_count / (positive + negative).
    Values < 0.3 indicate negative skew; > 0.7 indicates healthy positivity.
    Falls back to 0.5 (neutral) when no signal words are present.
    """
    words = " ".join(texts).lower().split()
    pos = sum(1 for w in words if w in _POSITIVE)
    neg = sum(1 for w in words if w in _NEGATIVE)
    return round(pos / max(1, pos + neg), 4) if (pos + neg) else 0.5


# ─── Burnout Keyword Scan ──────────────────────────────────
BURNOUT_LEXICON = [
    "tired", "exhausted", "burnt out", "burnout", "need a break",
    "overwhelmed", "struggling", "unmotivated", "drained", "can't do this",
    "hate this", "so done", "giving up", "no energy", "frustrated",
    "bored", "same thing", "pointless", "who cares", "whatever",
]


def count_burnout_keywords(texts: List[str]) -> int:
    """Count how many burnout-lexicon phrases appear in the combined text."""
    combined = " ".join(texts).lower()
    return sum(1 for kw in BURNOUT_LEXICON if kw in combined)


# ─── Post Length Variance ──────────────────────────────────
def post_length_decline(texts: List[str]) -> float:
    """
    Compares average word-count of the recent half vs the earlier half.
    Returns a ratio ∈ [0, 1] representing the magnitude of decline.
    """
    lengths = [len(t.split()) for t in texts]
    if len(lengths) < 2:
        return 0.0
    mid = len(lengths) // 2
    earlier_avg = sum(lengths[:mid]) / max(1, mid)
    recent_avg = sum(lengths[mid:]) / max(1, len(lengths) - mid)
    return round(max(0, (earlier_avg - recent_avg) / max(1, earlier_avg)), 4)
