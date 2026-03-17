"""
Content Creation Router for ContentOS

Handles AI-powered content generation - NO AUTH REQUIRED.
- Caption generation
- Summary creation
- Hashtag suggestions
- Tone rewriting
- Media content extraction (image/audio/video)
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Form, File, UploadFile, Depends
from pydantic import BaseModel

from routers.auth import CurrentUser, get_current_user_optional
from services.dynamo_repositories import get_users_repo
from services.llm_service import get_llm_service, AllProvidersFailedError
from services.vision_service import get_vision_service
from services.speech_service import get_speech_service, SpeechError

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
    model: Optional[str] = None  # Optional Nova model override


class HashtagRequest(BaseModel):
    """Request for hashtag generation."""
    content: str
    content_type: str = "text"
    language: str = "en"
    count: int = 5  # Number of hashtags to generate
    model: Optional[str] = None  # Optional Nova model override


class GenerateResponse(BaseModel):
    """Response with generated content."""
    result: str
    provider: str
    fallback_used: bool


class HashtagsResponse(BaseModel):
    """Response with generated hashtags."""
    hashtags: List[str]
    provider: str


class ScriptRequest(BaseModel):
    """Request for script generation."""
    topic: str
    script_type: str = "short_video"  # short_video, ad_copy, voiceover, podcast_intro
    tone: str = "engaging"
    duration_seconds: int = 60
    model: Optional[str] = None


class IdeasRequest(BaseModel):
    """Request for idea generation."""
    niche: str
    audience: str = "general"
    platform: str = "instagram"
    count: int = 8
    model: Optional[str] = None


class MediaExtractionResponse(BaseModel):
    """Response with extracted content and generated materials."""
    extracted_content: str
    caption: Optional[str] = None
    summary: Optional[str] = None
    hashtags: Optional[List[str]] = None
    provider: str


class TranscribeResponse(BaseModel):
    """Response with speech-to-text transcript."""
    text: str
    language: str
    provider: str
    fallback_used: bool
    segments: List[dict] = []


@router.post("/caption", response_model=GenerateResponse)
async def generate_caption(
    request: GenerateRequest,
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
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
            platform=request.platform,
            language=request.language,
            model=request.model,
            user_id=current_user.id if current_user else None,
        )
        return GenerateResponse(
            result=result["text"],
            provider=result["provider"],
            fallback_used=result["fallback_used"],
        )
    except AllProvidersFailedError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/summary", response_model=GenerateResponse)
async def generate_summary(
    request: GenerateRequest,
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """
    Generate a concise summary of content.
    NO AUTHENTICATION REQUIRED.
    
    Args:
        request: Content generation request with optional max_length (default: 150 characters)
    """
    try:
        max_length = request.max_length or 150  # Default summary length
        result = await llm.generate_summary(
            request.content,
            max_length=max_length,
            language=request.language,
            model=request.model,
            user_id=current_user.id if current_user else None,
        )
        return GenerateResponse(
            result=result["text"],
            provider=result["provider"],
            fallback_used=result["fallback_used"],
        )
    except AllProvidersFailedError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/hashtags", response_model=HashtagsResponse)
async def generate_hashtags(
    request: HashtagRequest,
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """
    Generate relevant hashtags for content.
    NO AUTHENTICATION REQUIRED.
    
    Args:
        request: Hashtag generation request with count parameter (default: 5)
    """
    try:
        result = await llm.generate_hashtags(
            request.content,
            request.count,
            language=request.language,
            model=request.model,
            user_id=current_user.id if current_user else None,
        )
        return HashtagsResponse(
            hashtags=result["hashtags"],
            provider=result["provider"],
        )
    except AllProvidersFailedError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/script")
async def generate_script(
    request: ScriptRequest,
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """Generate creator scripts for ads, reels, voiceovers, and podcasts."""
    prompt = f"""You are a senior creative copywriter.

Create a {request.script_type} script on topic: {request.topic}
Tone: {request.tone}
Target duration: {request.duration_seconds} seconds

Output requirements:
- Write clear spoken-word style lines
- Include a strong hook in first line
- Include a CTA in the ending
- Keep it production-ready with no extra commentary
"""
    try:
        result = await llm.generate(
            prompt,
            task="script",
            max_tokens=900,
            model=request.model,
            user_id=current_user.id if current_user else None,
        )
        return {
            "script": result["text"],
            "script_type": request.script_type,
            "provider": result["provider"],
            "fallback_used": result["fallback_used"],
        }
    except AllProvidersFailedError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/ideas")
async def generate_ideas(
    request: IdeasRequest,
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """Generate content ideas for creator planning and ideation."""
    count = max(3, min(request.count, 20))
    prompt = f"""Generate {count} fresh content ideas for:
- Niche: {request.niche}
- Audience: {request.audience}
- Platform: {request.platform}

Return only numbered ideas, one per line.
Each idea must be practical and execution-ready for creators.
"""
    try:
        result = await llm.generate(
            prompt,
            task="ideation",
            max_tokens=800,
            model=request.model,
            user_id=current_user.id if current_user else None,
        )
        lines = [ln.strip() for ln in result["text"].splitlines() if ln.strip()]
        ideas = []
        for line in lines:
            cleaned = line.lstrip("0123456789. -)").strip()
            if cleaned:
                ideas.append(cleaned)
        return {
            "ideas": ideas[:count],
            "provider": result["provider"],
            "fallback_used": result["fallback_used"],
        }
    except AllProvidersFailedError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/extract-and-generate", response_model=MediaExtractionResponse)
async def extract_and_generate(
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
    generate_caption: bool = Form(True),
    caption_max_length: int = Form(280),
    generate_summary: bool = Form(True),
    summary_max_length: int = Form(150),
    generate_hashtags: bool = Form(True),
    hashtag_count: int = Form(5),
    language: Optional[str] = Form("en"),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
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
        
        # Extract from video (start async moderation job)
        if video:
            video_bytes = await video.read()
            video_job = await vision.start_video_moderation(video_bytes, video.filename or "video.mp4")
            extracted_content += (
                "Video submitted for moderation analysis. "
                f"Moderation job id: {video_job.get('job_id')}. "
            )
            providers.append(video_job.get("provider", "vision_video_async"))
        
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
                max_length=caption_max_length,
                language=language,
                user_id=current_user.id if current_user else None,
            )
            caption_text = caption_result["text"]
            providers.append(caption_result["provider"])

        # Generate summary if requested
        summary_text = None
        if generate_summary:
            summary_result = await llm.generate_summary(
                extracted_content,
                max_length=summary_max_length,
                language=language,
                user_id=current_user.id if current_user else None,
            )
            summary_text = summary_result["text"]
            providers.append(summary_result["provider"])
        
        # Generate hashtags if requested
        hashtags_list = None
        if generate_hashtags:
            hashtags_result = await llm.generate_hashtags(
                extracted_content,
                hashtag_count,
                language=language,
                user_id=current_user.id if current_user else None,
            )
            hashtags_list = hashtags_result["hashtags"]
            providers.append(hashtags_result["provider"])
        
        return MediaExtractionResponse(
            extracted_content=extracted_content.strip(),
            caption=caption_text,
            summary=summary_text,
            hashtags=hashtags_list,
            provider=" + ".join(set(providers)),
        )
        
    except AllProvidersFailedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Media extraction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: Optional[str] = Form(None),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """
    Transcribe uploaded audio into text.

    Uses SpeechService fallback chain:
    Whisper -> Google Speech -> simple fallback.
    """
    try:
        if not current_user:
            raise HTTPException(
                status_code=401,
                detail="Login is required for voice actions",
            )
        allowed = get_users_repo().consume_feature_usage(
            user_id=current_user.id,
            feature="voice_generation",
            limit=3,
        )
        if not allowed:
            raise HTTPException(
                status_code=403,
                detail="Voice actions are limited to 3 per user in Creator Studio",
            )

        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file")

        transcript_result = await speech.transcribe_bytes(
            audio_bytes,
            audio.filename or "audio.wav",
            language,
        )

        return TranscribeResponse(
            text=transcript_result.get("text", "").strip(),
            language=transcript_result.get("language", language or "en"),
            provider=transcript_result.get("provider", "speech"),
            fallback_used=bool(transcript_result.get("fallback_used", False)),
            segments=transcript_result.get("segments", []),
        )
    except SpeechError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rewrite")
async def rewrite_tone(
    content: str = Form(...),
    tone: str = Form("professional"),  # professional, casual, engaging
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
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
        result = await llm.generate(
            prompt,
            task="rewrite",
            user_id=current_user.id if current_user else None,
        )
        return {
            "original": content,
            "rewritten": result["text"],
            "tone": tone,
            "provider": result["provider"],
        }
    except AllProvidersFailedError as e:
        raise HTTPException(status_code=503, detail=str(e))
