"""
Speech Service for ContentOS

AWS Transcribe-first with free fallback:
1. AWS Transcribe - PRIMARY for hackathon
2. OpenAI Whisper (local) - FREE fallback

Supports audio transcription with timestamp extraction.
"""
import logging
import tempfile
import os
import uuid
from typing import Optional, Dict, Any, List
from pathlib import Path

from config import settings

logger = logging.getLogger(__name__)


class SpeechError(Exception):
    """Base exception for speech errors."""
    pass


class SpeechService:
    """
    Speech-to-text service with AWS Transcribe primary and Whisper fallback.
    """
    
    def __init__(self):
        self.aws_client = None
        self.whisper_model = None
        
        # Initialize AWS Transcribe if configured
        if settings.aws_configured and settings.use_aws_transcribe:
            try:
                import boto3
                self.aws_client = boto3.client(
                    'transcribe',
                    region_name=settings.aws_region,
                )
                logger.info("AWS Transcribe initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize AWS Transcribe: {e}")
    
    def _load_whisper(self):
        """Lazy load Whisper model."""
        if self.whisper_model is None:
            try:
                import whisper
                # Use 'base' model for balance of speed and accuracy
                self.whisper_model = whisper.load_model("base")
                logger.info("Whisper model loaded")
            except Exception as e:
                logger.error(f"Failed to load Whisper: {e}")
                raise SpeechError(f"Whisper not available: {e}")
        return self.whisper_model
    
    async def transcribe_whisper(
        self,
        audio_path: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio using Whisper (FREE, local).
        
        Args:
            audio_path: Path to audio file
            language: Optional language hint
            
        Returns:
            Dict with text, segments, and language
        """
        try:
            model = self._load_whisper()
            
            options = {"task": "transcribe"}
            if language:
                options["language"] = language
            
            result = model.transcribe(audio_path, **options)
            
            # Extract segments with timestamps
            segments = [
                {
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip(),
                }
                for seg in result.get("segments", [])
            ]
            
            return {
                "text": result["text"].strip(),
                "segments": segments,
                "language": result.get("language", "en"),
                "provider": "whisper",
            }
            
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            raise SpeechError(f"Whisper failed: {e}")
    
    async def transcribe_google_free(
        self,
        audio_path: str,
        language: str = "en-US"
    ) -> Dict[str, Any]:
        """
        Transcribe using Google Speech Recognition (FREE tier).
        Note: Limited to shorter audio clips.
        """
        try:
            import speech_recognition as sr
            
            recognizer = sr.Recognizer()
            
            with sr.AudioFile(audio_path) as source:
                audio = recognizer.record(source)
            
            text = recognizer.recognize_google(audio, language=language)
            
            return {
                "text": text,
                "segments": [],  # Google free doesn't provide segments
                "language": language.split("-")[0],
                "provider": "google_speech_free",
            }
            
        except Exception as e:
            logger.error(f"Google Speech error: {e}")
            raise SpeechError(f"Google Speech failed: {e}")
    
    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio with automatic fallback.
        
        Priority: AWS Transcribe → Whisper (local)
        
        Args:
            audio_path: Path to audio file
            language: Optional language hint
            
        Returns:
            Dict with text, segments, language, provider
        """
        fallback_used = False
        
        # AWS Transcribe remains async (job-based). Interactive routes still use
        # local transcription while the Step Functions pipeline uses job APIs.
        
        # Try Whisper first (fast local processing)
        try:
            logger.info("Transcribing with Whisper")
            result = await self.transcribe_whisper(audio_path, language)
            result["fallback_used"] = fallback_used
            return result
        except SpeechError:
            logger.warning("Whisper failed, trying Google Speech")
            fallback_used = True
        
        # Fallback to Google Speech (free tier)
        try:
            lang_code = f"{language or 'en'}-US" if language else "en-US"
            result = await self.transcribe_google_free(audio_path, lang_code)
            result["fallback_used"] = fallback_used
            return result
        except SpeechError as e:
            logger.warning(f"All speech providers failed: {e}, using simple fallback")
            # Ultimate simple fallback - return placeholder
            return {
                "text": "[Audio transcription unavailable - please review manually]",
                "segments": [],
                "language": language or "en",
                "provider": "simple_fallback",
                "fallback_used": True,
                "note": "Speech recognition unavailable, manual transcription recommended",
            }

    def start_transcription_job(
        self,
        media_uri: str,
        media_format: str = "mp4",
        language_code: str = "en-US",
    ) -> Dict[str, Any]:
        if not self.aws_client:
            raise SpeechError("AWS Transcribe not configured")
        job_name = f"content-room-{uuid.uuid4().hex[:20]}"
        self.aws_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={"MediaFileUri": media_uri},
            MediaFormat=media_format,
            LanguageCode=language_code,
        )
        return {"job_name": job_name, "provider": "aws_transcribe"}

    def get_transcription_job(self, job_name: str) -> Dict[str, Any]:
        if not self.aws_client:
            raise SpeechError("AWS Transcribe not configured")
        result = self.aws_client.get_transcription_job(TranscriptionJobName=job_name)
        return result.get("TranscriptionJob", {})
    
    async def transcribe_bytes(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio from bytes.
        
        Args:
            audio_bytes: Audio file bytes
            filename: Original filename for extension detection
            language: Optional language hint
        """
        # Get file extension
        ext = Path(filename).suffix or ".wav"
        
        # Write to temp file
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name
        
        try:
            return await self.transcribe(temp_path, language)
        finally:
            # Cleanup temp file
            os.unlink(temp_path)


# Singleton instance
_speech_service: Optional[SpeechService] = None


def get_speech_service() -> SpeechService:
    """Get or create the speech service singleton."""
    global _speech_service
    if _speech_service is None:
        _speech_service = SpeechService()
    return _speech_service
