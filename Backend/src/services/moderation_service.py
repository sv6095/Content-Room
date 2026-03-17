"""
Multimodal Moderation Service for ContentOS.
"""
import logging
import hashlib
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from config import settings
from services.llm_service import get_llm_service, AllProvidersFailedError
from services.vision_service import get_vision_service
from services.speech_service import get_speech_service

logger = logging.getLogger(__name__)


def _safe_float(value: object, default: float = 0.0) -> float:
    """Convert provider values to float safely."""
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


class ModerationDecision(str, Enum):
    ALLOW = "ALLOW"
    FLAG = "FLAG"
    ESCALATE = "ESCALATE"


@dataclass
class ModerationResult:
    decision: ModerationDecision
    safety_score: float
    confidence: float
    explanation: str
    flags: List[str]
    evidence: List[Dict[str, Any]]
    provider: str
    processing_time_ms: int
    fallback_used: bool


class ModerationCache:
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, ModerationResult] = {}
        self.max_size = max_size

    def _hash_content(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def get(self, content: bytes) -> Optional[ModerationResult]:
        return self.cache.get(self._hash_content(content))

    def set(self, content: bytes, result: ModerationResult) -> None:
        if len(self.cache) >= self.max_size:
            keys = list(self.cache.keys())[: len(self.cache) // 2]
            for k in keys:
                del self.cache[k]
        self.cache[self._hash_content(content)] = result


class ModerationService:
    SAFE_THRESHOLD = 70
    FLAG_THRESHOLD = 40

    def __init__(self):
        self.llm = get_llm_service()
        self.vision = get_vision_service()
        self.speech = get_speech_service()
        self.cache = ModerationCache()

        self.comprehend_client = None
        if settings.aws_configured and settings.use_aws_comprehend:
            try:
                import boto3

                self.comprehend_client = boto3.client(
                    "comprehend",
                    region_name=settings.aws_region,
                )
                logger.info("AWS Comprehend initialized for toxicity detection")
            except Exception as e:
                logger.warning(f"Failed to initialize AWS Comprehend: {e}")

    async def prefilter_text(self, text: str) -> Dict[str, Any]:
        offensive_keywords = [
            "hate",
            "kill",
            "violence",
            "attack",
            "terrorist",
            "abuse",
            "threat",
            "bomb",
            "weapon",
            "murder",
        ]
        text_lower = text.lower()
        found = [kw for kw in offensive_keywords if kw in text_lower]
        if len(found) >= 3:
            return {"risk": "HIGH", "flags": found, "proceed": True}
        if len(found) >= 1:
            return {"risk": "MEDIUM", "flags": found, "proceed": True}
        return {"risk": "LOW", "flags": [], "proceed": False}

    async def prefilter_image(self, image_bytes: bytes) -> Dict[str, Any]:
        # Lightweight non-ML prefilter placeholder.
        return {"risk": "UNKNOWN", "proceed": True}

    async def analyze_text_aws(self, text: str) -> Dict[str, Any]:
        if not self.comprehend_client:
            raise RuntimeError("AWS Comprehend not available")
        try:
            response = self.comprehend_client.detect_toxic_content(
                TextSegments=[{"Text": text}],
                LanguageCode="en",
            )
            results = response.get("ResultList", [{}])[0]
            toxicity = results.get("Toxicity", 0)
            labels = results.get("Labels", [])
            flags = [label["Name"] for label in labels if label.get("Score", 0) > 0.5]
            return {
                "safety_score": (1 - toxicity) * 100,
                "flags": flags,
                "provider": "aws_comprehend",
            }
        except Exception as e:
            logger.error(f"AWS Comprehend error: {e}")
            raise

    async def analyze_text_llm(self, text: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        prompt = f"""You are a content moderation AI. Analyze the following text for safety issues.

Text to analyze: "{text}"

Provide a detailed analysis in this format:
DECISION: [ALLOW/FLAG/ESCALATE]
FLAGGED_CONTENT: [quote specific problematic parts, or "None" if safe]
FLAGS: [comma-separated categories or "none"]
EXPLANATION: [clear explanation]
"""
        try:
            result = await self.llm.generate(prompt, task="moderation", user_id=user_id)
            response_text = result["text"]
            lines = response_text.strip().split("\n")
            decision = "ALLOW"
            flags: List[str] = []
            explanation = ""
            flagged_content = ""
            for line in lines:
                if "DECISION:" in line:
                    decision_str = line.split(":")[-1].strip().upper()
                    if decision_str in ["ALLOW", "FLAG", "ESCALATE"]:
                        decision = decision_str
                elif "FLAGGED_CONTENT:" in line:
                    flagged_content = line.split(":", 1)[-1].strip()
                elif "FLAGS:" in line:
                    flag_str = line.split(":")[-1].strip()
                    if flag_str.lower() != "none":
                        flags = [f.strip() for f in flag_str.split(",")]
                elif "EXPLANATION:" in line:
                    explanation = line.split(":", 1)[-1].strip()

            safety_score = 100 if decision == "ALLOW" else (50 if decision == "FLAG" else 20)
            return {
                "safety_score": safety_score,
                "flags": flags,
                "explanation": explanation,
                "flagged_content": flagged_content,
                "provider": result["provider"],
            }
        except AllProvidersFailedError:
            return {
                "safety_score": 70,
                "flags": ["analysis_unavailable"],
                "explanation": "AI analysis unavailable, manual review recommended",
                "flagged_content": "",
                "provider": "fallback",
            }

    async def analyze_text(self, text: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        if self.comprehend_client:
            try:
                return await self.analyze_text_aws(text)
            except Exception:
                logger.warning("AWS Comprehend failed, using LLM fallback")
        return await self.analyze_text_llm(text, user_id=user_id)

    async def analyze_image(self, image_bytes: bytes) -> Dict[str, Any]:
        return await self.vision.analyze(image_bytes)

    async def analyze_audio(self, audio_bytes: bytes, filename: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        transcript_result = await self.speech.transcribe_bytes(audio_bytes, filename)
        transcript = transcript_result["text"]
        text_result = await self.analyze_text(transcript, user_id=user_id)
        return {
            "transcript": transcript,
            "segments": transcript_result.get("segments", []),
            "safety_score": text_result["safety_score"],
            "flags": text_result["flags"],
            "provider": f"speech:{transcript_result['provider']}+text:{text_result['provider']}",
        }

    def make_decision(self, safety_score: float, flags: List[str]) -> ModerationDecision:
        critical_flags = ["child_abuse", "terrorism", "self_harm"]
        if any(f.lower() in str(flags).lower() for f in critical_flags):
            return ModerationDecision.ESCALATE
        if safety_score >= self.SAFE_THRESHOLD:
            return ModerationDecision.ALLOW
        if safety_score >= self.FLAG_THRESHOLD:
            return ModerationDecision.FLAG
        return ModerationDecision.ESCALATE

    async def moderate_text(self, text: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        start_time = datetime.now()
        prefilter = await self.prefilter_text(text)
        analysis = await self.analyze_text(text, user_id=user_id)
        decision = self.make_decision(analysis["safety_score"], analysis.get("flags", []))
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        return {
            "decision": decision.value,
            "safety_score": analysis["safety_score"],
            "confidence": 0.85,
            "explanation": analysis.get(
                "explanation",
                f"Content analyzed with {len(analysis.get('flags', []))} flags detected",
            ),
            "flagged_content": analysis.get("flagged_content", ""),
            "flags": analysis.get("flags", []),
            "evidence": [],
            "provider": analysis.get("provider", "unknown"),
            "processing_time_ms": processing_time,
            "prefilter_risk": prefilter.get("risk", "UNKNOWN"),
        }

    async def moderate_image(self, image_bytes: bytes) -> Dict[str, Any]:
        start_time = datetime.now()
        cached = self.cache.get(image_bytes)
        if cached:
            return {
                "decision": cached.decision.value,
                "safety_score": cached.safety_score,
                "cached": True,
            }

        prefilter = await self.prefilter_image(image_bytes)
        analysis = await self.analyze_image(image_bytes)
        safety_score = _safe_float(analysis.get("safety_score"), 0.0)
        raw_flags = analysis.get("flags", [])
        if raw_flags and isinstance(raw_flags[0], dict):
            flags = [f.get("name", "") for f in raw_flags if f.get("name")]
        else:
            flags = [str(f) for f in raw_flags if f]

        if not flags and analysis.get("moderation_labels"):
            flags = [x.get("name", "") for x in analysis["moderation_labels"] if x.get("name")]

        content_labels_raw = analysis.get("content_labels", [])
        content_labels = [c.get("name", c) if isinstance(c, dict) else str(c) for c in content_labels_raw]
        decision = self.make_decision(safety_score, flags)
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        return {
            "decision": decision.value,
            "safety_score": safety_score,
            "confidence": 0.9 if "aws_rekognition" in str(analysis.get("provider", "")) else 0.7,
            "explanation": (
                f"Image analyzed: {len(flags)} moderation flag(s) detected"
                if flags
                else "Image analyzed; no issues detected"
            ),
            "flags": flags,
            "content_labels": content_labels,
            "provider": analysis.get("provider", "unknown"),
            "processing_time_ms": processing_time,
            "prefilter_risk": prefilter.get("risk", "UNKNOWN"),
            "fallback_used": analysis.get("fallback_used", False),
        }

    async def moderate_audio(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        start_time = datetime.now()
        analysis = await self.analyze_audio(audio_bytes, filename, user_id=user_id)
        decision = self.make_decision(analysis["safety_score"], analysis.get("flags", []))
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        flagged_segments = []
        if analysis.get("flags") and analysis.get("segments"):
            for seg in analysis["segments"]:
                flagged_segments.append(
                    {
                        "start": seg["start"],
                        "end": seg["end"],
                        "text": seg["text"],
                        "flags": analysis["flags"],
                    }
                )
        return {
            "decision": decision.value,
            "safety_score": analysis["safety_score"],
            "confidence": 0.8,
            "explanation": f"Audio analyzed: {len(analysis.get('flags', []))} issues detected",
            "flags": analysis.get("flags", []),
            "transcript": analysis.get("transcript", ""),
            "flagged_segments": flagged_segments,
            "provider": analysis["provider"],
            "processing_time_ms": processing_time,
        }

    async def moderate_video(self, video_bytes: bytes) -> Dict[str, Any]:
        raise RuntimeError(
            "Direct synchronous video moderation is deprecated. "
            "Use start_video_moderation() and get_video_moderation_result()."
        )

    async def start_video_moderation(self, video_bytes: bytes, filename: str) -> Dict[str, Any]:
        return await self.vision.start_video_moderation(video_bytes, filename)

    async def get_video_moderation_result(self, job_id: str) -> Dict[str, Any]:
        start_time = datetime.now()
        analysis = await self.vision.get_video_moderation(job_id)
        status = analysis.get("status", "UNKNOWN")
        if status != "SUCCEEDED":
            return {
                "job_id": job_id,
                "status": status,
                "provider": analysis.get("provider", "aws_rekognition_video"),
                "status_message": analysis.get("status_message"),
            }

        labels = analysis.get("moderation_labels", [])
        flags = sorted(set([str(x.get("name", "")) for x in labels if x.get("name")]))
        max_conf = max([float(x.get("confidence", 0.0)) for x in labels], default=0.0)
        safety_score = max(0.0, 100.0 - max_conf)
        decision = self.make_decision(safety_score, flags)
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        return {
            "job_id": job_id,
            "status": status,
            "decision": decision.value,
            "safety_score": round(safety_score, 2),
            "confidence": round(max_conf, 2),
            "flags": flags,
            "moderation_labels": labels,
            "provider": analysis.get("provider", "aws_rekognition_video"),
            "processing_time_ms": processing_time,
            "explanation": (
                f"Rekognition video moderation completed with {len(flags)} unique moderation flag(s)."
                if flags
                else "Rekognition video moderation completed with no moderation flags."
            ),
        }


_moderation_service: Optional[ModerationService] = None


def get_moderation_service() -> ModerationService:
    global _moderation_service
    if _moderation_service is None:
        _moderation_service = ModerationService()
    return _moderation_service
