"""
Vision Service for ContentOS

AWS Rekognition-first with free fallback:
1. AWS Rekognition - PRIMARY for hackathon
2. Groq Vision - secondary fallback
3. Simple safety fallback when provider unavailable

Handles image analysis for content moderation.
"""
import asyncio
import logging
import base64
import re
import tempfile
from typing import Optional, Dict, Any, List

import numpy as np
from config import settings

logger = logging.getLogger(__name__)


class VisionError(Exception):
    """Base exception for vision errors."""
    pass


class VisionService:
    """
    Vision service with AWS Rekognition primary and simple fallback.
    
    Fallback chain:
    1. AWS Rekognition - PRIMARY (cloud, accurate)
    2. Groq Vision - Llama 4 Scout (FREE, good rate limits)
    3. Simple fallback
    """
    
    def __init__(self):
        self.aws_client = None
        self.groq_client = None
        
        # Initialize AWS Rekognition if configured
        if settings.aws_configured and settings.use_aws_rekognition:
            try:
                import importlib
                boto3 = importlib.import_module("boto3")
                self.aws_client = boto3.client(
                    'rekognition',
                    region_name=settings.aws_region,
                )
                logger.info("AWS Rekognition initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize AWS Rekognition: {e}")
        
        # Initialize Groq Vision backup
        if settings.grok_api_key:
            try:
                import importlib
                groq_module = importlib.import_module("groq")
                self.groq_client = groq_module.Groq(api_key=settings.grok_api_key)
                self.groq_model = "meta-llama/llama-4-scout-17b-16e-instruct"
                logger.info("Groq Vision initialized (Llama 4 Scout)")
            except Exception as e:
                logger.warning(f"Failed to initialize Groq Vision: {e}")
    
    async def analyze_aws(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analyze image using AWS Rekognition.
        
        Returns moderation labels and confidence scores.
        """
        if not self.aws_client:
            raise VisionError("AWS Rekognition not configured")
        
        try:
            # Detect moderation labels
            moderation_response = await asyncio.to_thread(
                self.aws_client.detect_moderation_labels,
                Image={"Bytes": image_bytes},
                MinConfidence=50.0,
            )
            
            moderation_labels = [
                {
                    "name": label["Name"],
                    "parent": label.get("ParentName", ""),
                    "confidence": label["Confidence"],
                }
                for label in moderation_response.get("ModerationLabels", [])
            ]
            
            # Detect labels for content understanding
            labels_response = await asyncio.to_thread(
                self.aws_client.detect_labels,
                Image={"Bytes": image_bytes},
                MaxLabels=10,
                MinConfidence=70.0,
            )
            
            content_labels = [
                {
                    "name": label["Name"],
                    "confidence": label["Confidence"],
                }
                for label in labels_response.get("Labels", [])
            ]
            
            # Calculate safety score (inverse of max moderation confidence)
            max_moderation = max(
                [l["confidence"] for l in moderation_labels],
                default=0
            )
            safety_score = max(0, 100 - max_moderation)
            
            return {
                "safety_score": safety_score,
                "moderation_labels": moderation_labels,
                "content_labels": content_labels,
                "provider": "aws_rekognition",
            }
            
        except Exception as e:
            logger.error(f"AWS Rekognition error: {e}")
            raise VisionError(f"AWS Rekognition failed: {e}")

    async def analyze_groq(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analyze image using Groq Vision fallback.
        Returns normalized moderation result shape.
        """
        if not self.groq_client:
            raise VisionError("Groq Vision not configured")

        try:
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            prompt = (
                "You are an image moderation assistant. "
                "Assess whether this image is safe for social media posting.\n"
                "Output EXACTLY:\n"
                "SAFETY_SCORE: <0-100 integer, where 100 is safest>\n"
                "FLAGS: <comma-separated risk categories or none>\n"
                "LABELS: <comma-separated content labels or none>"
            )
            response = await asyncio.to_thread(
                self.groq_client.chat.completions.create,
                model=self.groq_model,
                temperature=0.1,
                max_tokens=220,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                        ],
                    }
                ],
            )
            content = (response.choices[0].message.content or "").strip()

            safety_match = re.search(r"SAFETY_SCORE:\s*(\d+)", content, re.IGNORECASE)
            flags_match = re.search(r"FLAGS:\s*(.+)", content, re.IGNORECASE)
            labels_match = re.search(r"LABELS:\s*(.+)", content, re.IGNORECASE)

            safety_score = int(safety_match.group(1)) if safety_match else 50
            safety_score = max(0, min(100, safety_score))

            raw_flags = flags_match.group(1).strip() if flags_match else "none"
            flags = [] if raw_flags.lower() == "none" else [f.strip() for f in raw_flags.split(",") if f.strip()]

            raw_labels = labels_match.group(1).strip() if labels_match else "none"
            labels = [] if raw_labels.lower() == "none" else [l.strip() for l in raw_labels.split(",") if l.strip()]

            return {
                "safety_score": safety_score,
                "flags": flags,
                "moderation_labels": [{"name": flag, "parent": "", "confidence": 70.0} for flag in flags],
                "content_labels": [{"name": label, "confidence": 70.0} for label in labels],
                "provider": "groq_vision",
            }
        except Exception as e:
            logger.error(f"Groq Vision error: {e}")
            raise VisionError(f"Groq Vision failed: {e}")


    async def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analyze image with AWS Rekognition, then a minimal fallback.
        """
        fallback_used = False
        
        # Try AWS Rekognition first (PRIMARY)
        if self.aws_client:
            try:
                logger.info("Analyzing with AWS Rekognition")
                result = await self.analyze_aws(image_bytes)
                result["fallback_used"] = fallback_used
                return result
            except VisionError:
                logger.warning("AWS Rekognition failed, trying Groq Vision fallback")
                fallback_used = True

        # Try Groq Vision fallback
        if self.groq_client:
            try:
                logger.info("Analyzing with Groq Vision fallback")
                result = await self.analyze_groq(image_bytes)
                result["fallback_used"] = True
                return result
            except VisionError:
                logger.warning("Groq Vision failed, using simple fallback")

        return {
            "safety_score": 50,
            "moderation_labels": [],
            "content_labels": [],
            "provider": "simple_fallback",
            "fallback_used": True,
            "note": "Analysis unavailable, manual review recommended",
        }

    async def _extract_video_frames(
        self,
        video_bytes: bytes,
        max_frames: int = 6,
    ) -> Dict[str, Any]:
        """
        Extract evenly-spaced key frames from uploaded video bytes.
        """
        try:
            import cv2  # Optional dependency; imported lazily.
        except Exception as e:
            raise VisionError(f"Video processing dependency unavailable: {e}")

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                tmp.write(video_bytes)
                temp_path = tmp.name

            cap = cv2.VideoCapture(temp_path)
            if not cap.isOpened():
                raise VisionError("Failed to open video stream")

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
            if fps <= 0:
                fps = 25.0
            duration_seconds = (total_frames / fps) if total_frames > 0 else 0.0

            if total_frames <= 0:
                cap.release()
                raise VisionError("Video contains no readable frames")

            sample_count = max(1, min(max_frames, total_frames))
            frame_indices = np.linspace(0, total_frames - 1, num=sample_count, dtype=int).tolist()

            frames: List[Dict[str, Any]] = []
            for idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ok, frame = cap.read()
                if not ok or frame is None:
                    continue
                success, encoded = cv2.imencode(".jpg", frame)
                if not success:
                    continue
                frames.append(
                    {
                        "frame_index": int(idx),
                        "timestamp": round(float(idx) / fps, 3),
                        "bytes": encoded.tobytes(),
                    }
                )

            cap.release()

            if not frames:
                raise VisionError("No frames could be extracted from video")

            return {
                "frames": frames,
                "video_info": {
                    "duration_seconds": round(duration_seconds, 3),
                    "total_frames": total_frames,
                    "frames_analyzed": len(frames),
                },
            }
        except VisionError:
            raise
        except Exception as e:
            raise VisionError(f"Video frame extraction failed: {e}")
        finally:
            if temp_path:
                try:
                    import os

                    os.unlink(temp_path)
                except Exception:
                    pass

    async def analyze_video(self, video_bytes: bytes, max_frames: int = 6) -> Dict[str, Any]:
        """
        Moderate video by extracting frames and analyzing each frame.
        """
        extracted = await self._extract_video_frames(video_bytes, max_frames=max_frames)
        frames = extracted["frames"]
        video_info = extracted["video_info"]

        frame_results: List[Dict[str, Any]] = []
        all_flags: List[str] = []
        all_labels: List[str] = []
        providers: List[str] = []
        min_safety = 100.0

        for frame in frames:
            analysis = await self.analyze(frame["bytes"])
            safety_score = float(analysis.get("safety_score", 50))
            min_safety = min(min_safety, safety_score)

            moderation_labels = analysis.get("moderation_labels", [])
            content_labels = analysis.get("content_labels", [])
            flags = [x.get("name", "") for x in moderation_labels if isinstance(x, dict) and x.get("name")]
            labels = [x.get("name", "") for x in content_labels if isinstance(x, dict) and x.get("name")]
            if not labels:
                labels = [str(x) for x in content_labels if x]

            all_flags.extend(flags)
            all_labels.extend(labels)
            providers.append(str(analysis.get("provider", "unknown")))

            frame_results.append(
                {
                    "frame_index": frame["frame_index"],
                    "timestamp": frame["timestamp"],
                    "safety_score": round(safety_score, 2),
                    "flags": sorted(set(flags)),
                    "labels": sorted(set(labels)),
                    "provider": analysis.get("provider", "unknown"),
                }
            )

        return {
            "safety_score": round(min_safety, 2),
            "flags": sorted(set([f for f in all_flags if f])),
            "content_labels": sorted(set([l for l in all_labels if l])),
            "provider": "video_frame_pipeline",
            "provider_chain": sorted(set(providers)),
            "video_info": video_info,
            "frame_results": frame_results,
            "fallback_used": any("fallback" in p for p in providers),
        }
    
    async def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze image from file path."""
        with open(file_path, "rb") as f:
            image_bytes = f.read()
        return await self.analyze(image_bytes)


# Singleton instance
_vision_service: Optional[VisionService] = None


def get_vision_service() -> VisionService:
    """Get or create the vision service singleton."""
    global _vision_service
    if _vision_service is None:
        _vision_service = VisionService()
    return _vision_service
