"""
Content Creation Router for ContentOS

Handles AI-powered content generation - NO AUTH REQUIRED.
- Caption generation
- Summary creation
- Hashtag suggestions
- Tone rewriting
- Media content extraction
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Form, File, UploadFile
from pydantic import BaseModel

from services.llm_service import get_llm_service, AllProvidersFailedError
from services.vision_service import get_vision_service
from services.speech_service import get_speech_service

logger = logging.getLogger(__name__)
router = APIRouter()

llm = get_llm_service()
vision = get_vision_service()
speech = get_speech_service()


class GenerateRequest(BaseModel):
    """Request for content generation."""
    content: str = ""  # Make optional for media-only generation
    content_type: str = "text"
    language: str = "en"
    max_length: Optional[int] = None  # For caption/summary generation
    platform: Optional[str] = None  # Target platform: twitter, instagram, linkedin


class HashtagRequest(BaseModel):
    """Request for hashtag generation."""
    content: str
    content_type: str = "text"
    language: str = "en"
    count: int = 5  # Number of hashtags to generate


class GenerateResponse(BaseModel):
    """Response with generated content."""
    result: str
    provider: str
    fallback_used: bool


class HashtagsResponse(BaseModel):
    """Response with generated hashtags."""
    hashtags: List[str]
    provider: str


class MediaExtractionResponse(BaseModel):
    """Response with extracted content and generated materials."""
    extracted_content: str
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = None
    provider: str


@router.post("/caption", response_model=GenerateResponse)
async def generate_caption(request: GenerateRequest):
    """
    Generate an engaging caption for content.
    
    Uses AWS Bedrock with Grok/Gemini/Ollama fallback.
    NO AUTHENTICATION REQUIRED.
    
    Args:
        request: Content generation request with optional max_length (default: 280 characters)
    """
    try:
        max_length = request.max_length or 280  # Default Twitter/X style length
        result = await llm.generate_caption(
            request.content, 
            request.content_type,
            max_length=max_length,
            platform=request.platform
        )
        return GenerateResponse(
            result=result["text"],
            provider=result["provider"],
            fallback_used=result["fallback_used"],
        )
    except AllProvidersFailedError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/summary", response_model=GenerateResponse)
async def generate_summary(request: GenerateRequest):
    """
    Generate a concise summary of content.
    NO AUTHENTICATION REQUIRED.
    
    Args:
        request: Content generation request with optional max_length (default: 150 characters)
    """
    try:
        max_length = request.max_length or 150  # Default summary length
        result = await llm.generate_summary(request.content, max_length=max_length)
        return GenerateResponse(
            result=result["text"],
            provider=result["provider"],
            fallback_used=result["fallback_used"],
        )
    except AllProvidersFailedError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/hashtags", response_model=HashtagsResponse)
async def generate_hashtags(request: HashtagRequest):
    """
    Generate relevant hashtags for content.
    NO AUTHENTICATION REQUIRED.
    
    Args:
        request: Hashtag generation request with count parameter (default: 5)
    """
    try:
        result = await llm.generate_hashtags(request.content, request.count)
        return HashtagsResponse(
            hashtags=result["hashtags"],
            provider=result["provider"],
        )
    except AllProvidersFailedError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/extract-and-generate", response_model=MediaExtractionResponse)
async def extract_and_generate(
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
    generate_caption: bool = Form(True),
    caption_max_length: int = Form(280),
    generate_hashtags: bool = Form(True),
    hashtag_count: int = Form(5),
):
    """
    Extract content from media files and generate caption/hashtags.
    
    This endpoint allows users to upload images, audio, or video and automatically
    extract meaningful content  from them, then generate captions and hashtags.
    
    NO AUTHENTICATION REQUIRED.
    
    Args:
        image: Image file to analyze
        audio: Audio file to transcribe
        video: Video file to analyze (extracts frames)
        generate_caption: Whether to generate a caption
        caption_max_length: Maximum caption length
        generate_hashtags: Whether to generate hashtags
        hashtag_count: Number of hashtags to generate
    """
    if not image and not audio and not video:
        raise HTTPException(
            status_code=400,
            detail="At least one media file (image, audio, or video) is required"
        )
    
    try:
        extracted_content = ""
        providers = []
        
        # Extract from image
        if image:
            image_bytes = await image.read()
            image_analysis = await vision.analyze(image_bytes)
            
            # Extract content labels and descriptions
            labels = image_analysis.get("content_labels", [])
            if labels:
                label_text = ", ".join([
                    l.get("name", l) if isinstance(l, dict) else str(l)
                    for l in labels[:10]  # Top 10 labels
                ])
                extracted_content += f"Image content: {label_text}. "
                providers.append(image_analysis.get("provider", "vision"))
        
        # Extract from audio
        if audio:
            audio_bytes = await audio.read()
            transcript_result = await speech.transcribe_bytes(
                audio_bytes, 
                audio.filename or "audio.wav"
            )
            transcript = transcript_result.get("text", "")
            if transcript:
                extracted_content += f"Audio transcript: {transcript} "
                providers.append(transcript_result.get("provider", "speech"))
        
        # Extract from video (use first frame for now)
        if video:
            raise HTTPException(
                status_code=501,
                detail="Video extraction is currently unavailable",
            )
        
        if not extracted_content:
            raise HTTPException(
                status_code=500,
                detail="Failed to extract content from media files"
            )
        
        # Generate caption if requested
        caption_text = None
        if generate_caption:
            caption_result = await llm.generate_caption(
                extracted_content,
                "text",
                max_length=caption_max_length
            )
            caption_text = caption_result["text"]
            providers.append(caption_result["provider"])
        
        # Generate hashtags if requested
        hashtags_list = None
        if generate_hashtags:
            hashtags_result = await llm.generate_hashtags(extracted_content, hashtag_count)
            hashtags_list = hashtags_result["hashtags"]
            providers.append(hashtags_result["provider"])
        
        return MediaExtractionResponse(
            extracted_content=extracted_content.strip(),
            caption=caption_text,
            hashtags=hashtags_list,
            provider=" + ".join(set(providers)),
        )
        
    except AllProvidersFailedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Media extraction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rewrite")
async def rewrite_tone(
    content: str = Form(...),
    tone: str = Form("professional"),  # professional, casual, engaging
):
    """
    Rewrite content with a different tone.
    NO AUTHENTICATION REQUIRED.
    """
    prompt = f"""Rewrite the following content in a {tone} tone.
Keep the core message but adjust the style.

Original: {content}

Rewritten ({tone} tone):"""
    
    try:
        result = await llm.generate(prompt, task="rewrite")
        return {
            "original": content,
            "rewritten": result["text"],
            "tone": tone,
            "provider": result["provider"],
        }
    except AllProvidersFailedError as e:
        raise HTTPException(status_code=503, detail=str(e))
