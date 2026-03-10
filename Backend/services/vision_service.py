"""
Vision Service for ContentOS

AWS Rekognition-first with free fallback:
1. AWS Rekognition - PRIMARY for hackathon
2. Simple safety fallback when provider unavailable

Handles image analysis for content moderation.
"""
import logging
import base64
import re
from typing import Optional, Dict, Any, List
from pathlib import Path

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
                import boto3
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
                from groq import Groq
                self.groq_client = Groq(api_key=settings.grok_api_key)
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
            moderation_response = self.aws_client.detect_moderation_labels(
                Image={'Bytes': image_bytes},
                MinConfidence=50.0
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
            labels_response = self.aws_client.detect_labels(
                Image={'Bytes': image_bytes},
                MaxLabels=10,
                MinConfidence=70.0
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
                logger.warning("AWS Rekognition failed, using simple fallback")
                fallback_used = True

        return {
            "safety_score": 50,
            "moderation_labels": [],
            "content_labels": [],
            "provider": "simple_fallback",
            "fallback_used": True,
            "note": "Analysis unavailable, manual review recommended",
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
