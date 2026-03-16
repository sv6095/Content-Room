"""
Image generation service for Creator Studio.

Supports:
- Amazon Titan Image Generator v2
- Amazon Nova Canvas
"""
import base64
import json
import logging
from typing import Any, Dict, Optional

from config import settings
from services.storage_service import get_storage_service

logger = logging.getLogger(__name__)


class ImageGenerationError(Exception):
    """Base exception for image generation failures."""
    pass


class ImageGenerationService:
    """Bedrock-based image generation with Titan and Nova Canvas."""

    def __init__(self):
        self.client = None
        if settings.aws_configured and (settings.use_aws_titan_image or settings.use_aws_nova_canvas):
            try:
                import boto3
                self.client = boto3.client("bedrock-runtime", region_name="us-east-1")
                logger.info("Image generation client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize image generation client: {e}")

    def _extract_base64_image(self, payload: Any) -> Optional[str]:
        if isinstance(payload, dict):
            if "images" in payload and isinstance(payload["images"], list) and payload["images"]:
                first = payload["images"][0]
                if isinstance(first, str):
                    return first
                if isinstance(first, dict):
                    for k in ("base64", "image", "data"):
                        if k in first and isinstance(first[k], str):
                            return first[k]
            if "artifacts" in payload and isinstance(payload["artifacts"], list) and payload["artifacts"]:
                first = payload["artifacts"][0]
                if isinstance(first, dict):
                    for k in ("base64", "image", "data"):
                        if k in first and isinstance(first[k], str):
                            return first[k]
            for value in payload.values():
                found = self._extract_base64_image(value)
                if found:
                    return found
        elif isinstance(payload, list):
            for value in payload:
                found = self._extract_base64_image(value)
                if found:
                    return found
        return None

    async def generate(
        self,
        prompt: str,
        engine: str = "titan",
        width: int = 1024,
        height: int = 1024,
    ) -> Dict[str, Any]:
        if not self.client:
            raise ImageGenerationError("Image generation is not configured")

        if not prompt.strip():
            raise ImageGenerationError("Prompt is required")

        normalized_engine = engine.strip().lower()
        if normalized_engine not in ("titan", "nova_canvas"):
            raise ImageGenerationError("Engine must be 'titan' or 'nova_canvas'")

        model_id = (
            settings.titan_image_model_id
            if normalized_engine == "titan"
            else settings.nova_canvas_model_id
        )

        body = {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {"text": prompt.strip()},
            "imageGenerationConfig": {
                "numberOfImages": 1,
                "quality": "standard",
                "height": max(512, min(height, 1408)),
                "width": max(512, min(width, 1408)),
            },
        }

        try:
            response = self.client.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )
            payload = json.loads(response["body"].read())
            image_b64 = self._extract_base64_image(payload)
            if not image_b64:
                raise ImageGenerationError("No image returned by provider")

            image_bytes = base64.b64decode(image_b64)
            storage = get_storage_service()
            upload = await storage.upload(
                file_data=image_bytes,
                filename=f"{normalized_engine}-generated.png",
                content_type="image/png",
                folder="generated/images",
                preferred_provider="s3",
            )

            return {
                "prompt": prompt.strip(),
                "engine": normalized_engine,
                "model_id": model_id,
                "image_url": upload.get("url"),
                "image_key": upload.get("key"),
                "provider": f"bedrock_{normalized_engine}",
            }
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            if isinstance(e, ImageGenerationError):
                raise
            raise ImageGenerationError(str(e))


_image_generation_service: Optional[ImageGenerationService] = None


def get_image_generation_service() -> ImageGenerationService:
    """Get or create singleton image generation service."""
    global _image_generation_service
    if _image_generation_service is None:
        _image_generation_service = ImageGenerationService()
    return _image_generation_service

