"""
Translation Router for ContentOS

Handles multilingual translation - NO AUTH REQUIRED.
- Text translation
- Language detection
- Supported languages list
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.translation_service import get_translation_service

logger = logging.getLogger(__name__)
router = APIRouter()

translation = get_translation_service()


class TranslateRequest(BaseModel):
    """Request for translation."""
    text: str
    target_lang: str
    source_lang: Optional[str] = None  # Auto-detect if not provided


class TranslateResponse(BaseModel):
    """Response with translated text."""
    translated_text: str
    source_lang: str
    target_lang: str
    provider: str
    fallback_used: bool


class DetectRequest(BaseModel):
    """Request for language detection."""
    text: str


class LanguageInfo(BaseModel):
    """Language information."""
    code: str
    name: str
    native: str
    font: str


@router.post("/text", response_model=TranslateResponse)
async def translate_text(request: TranslateRequest):
    """
    Translate text to target language.
    Uses AWS Translate with Google Translate (free) fallback.
    NO AUTHENTICATION REQUIRED.
    """
    try:
        result = await translation.translate(
            text=request.text,
            target_lang=request.target_lang,
            source_lang=request.source_lang,
        )
        return TranslateResponse(**result)
    except Exception as e:
        logger.error(f"Translation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect")
async def detect_language(request: DetectRequest):
    """
    Detect language of input text.
    NO AUTHENTICATION REQUIRED.
    """
    detected = translation.detect_language(request.text)
    return {
        "detected_language": detected,
        "confidence": 0.9,
    }


@router.get("/languages", response_model=List[LanguageInfo])
async def get_supported_languages():
    """
    Get list of supported languages.
    Supports 9 Indian languages + English.
    NO AUTHENTICATION REQUIRED.
    """
    return translation.get_supported_languages()


@router.post("/batch")
async def translate_batch(
    texts: List[str],
    target_lang: str,
    source_lang: Optional[str] = None,
):
    """
    Translate multiple texts at once.
    NO AUTHENTICATION REQUIRED.
    """
    try:
        results = await translation.translate_batch(texts, target_lang, source_lang)
        return {
            "translations": results,
            "count": len(results),
        }
    except Exception as e:
        logger.error(f"Batch translation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
