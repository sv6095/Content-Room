"""
Translation Service for ContentOS

AWS Translate-first service:
1. AWS Translate - PRIMARY for hackathon
2. deep-translator fallback

Supports 9 Indian languages + English:
- Telugu (te), Tamil (ta), Hindi (hi), Bangla (bn)
- Kannada (kn), Malayalam (ml), Gujarati (gu), Odia (or)
- English (en)

Also handles TRANSLITERATED text (Indian languages in English script).
"""
import logging
from typing import Optional, Dict, Any, List
from enum import Enum
import re

from config import settings

logger = logging.getLogger(__name__)


class SupportedLanguage(str, Enum):
    """Supported languages with ISO 639-1 codes."""
    ENGLISH = "en"
    HINDI = "hi"
    TELUGU = "te"
    TAMIL = "ta"
    BANGLA = "bn"
    KANNADA = "kn"
    MALAYALAM = "ml"
    GUJARATI = "gu"
    ODIA = "or"


# Language metadata for UI
LANGUAGE_INFO = {
    "en": {"name": "English", "native": "English", "font": "font-english"},
    "hi": {"name": "Hindi", "native": "हिंदी", "font": "font-hindi"},
    "te": {"name": "Telugu", "native": "తెలుగు", "font": "font-telugu"},
    "ta": {"name": "Tamil", "native": "தமிழ்", "font": "font-tamil"},
    "bn": {"name": "Bengali", "native": "বাংলা", "font": "font-bangla"},
    "kn": {"name": "Kannada", "native": "ಕನ್ನಡ", "font": "font-kannada"},
    "ml": {"name": "Malayalam", "native": "മലയാളം", "font": "font-malayalam"},
    "gu": {"name": "Gujarati", "native": "ગુજરાતી", "font": "font-gujarati"},
    "or": {"name": "Odia", "native": "ଓଡ଼ିଆ", "font": "font-odia"},
}


class TranslationError(Exception):
    """Base exception for translation errors."""
    pass


class TranslationService:
    """
    Translation service with AWS Translate primary and free fallback.
    Supports transliterated Indian language detection.
    """
    
    # Common transliterated words for each language (romanized)
    TRANSLITERATION_HINTS = {
        "te": ["nenu", "meeru", "ela", "undi", "chala", "bagundi", "emiti", "chestu", 
               "vellali", "randi", "vastanu", "chesanu", "ikkada", "akkada", "manchi"],
        "hi": ["mujhe", "aapka", "kaise", "kya", "hain", "bahut", "acha", "theek", 
               "karo", "chahiye", "raha", "karna", "hona", "tum", "aap", "yeh", "woh"],
        "ta": ["naan", "enna", "epdi", "irukku", "nalla", "vendum", "panna", 
               "sollu", "vaanga", "pogalam", "inge", "ange", "romba"],
        "bn": ["ami", "tumi", "kemon", "ache", "bhalo", "korbo", "jabo", "elo", 
               "koro", "apni", "amader", "tomar"],
        "kn": ["nanu", "nimma", "hege", "ide", "chennagi", "maadu", "banni", 
               "hogona", "illi", "alli", "tumba"],
        "ml": ["njan", "ningal", "engane", "und", "nalla", "cheyyuka", "varu", 
               "poku", "ivide", "avide", "valare"],
        "gu": ["hu", "tame", "kem", "chhe", "saru", "karvu", "aavo", "javu", 
               "ahiya", "tyaan", "ghanu"],
    }

    @staticmethod
    def _normalized_tokens(text: str) -> List[str]:
        """Tokenize transliterated text robustly (handles punctuation/suffix noise)."""
        # Keep alpha tokens only so words like "pongal-in," become ["pongal", "in"].
        return re.findall(r"[a-z]+", (text or "").lower())
    
    def __init__(self):
        self.aws_client = None
        
        # Initialize AWS Translate if configured
        if settings.aws_configured and settings.use_aws_translate:
            try:
                import boto3
                self.aws_client = boto3.client(
                    'translate',
                    region_name=settings.aws_region,
                )
                logger.info("AWS Translate initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize AWS Translate: {e}")
    
    def detect_language(self, text: str) -> str:
        """
        Detect the language of input text.
        Supports both native script AND transliterated text (English script).
        
        Examples:
        - "నమస్కారం" → "te" (Telugu script)
        - "nenu chala bagundi" → "te" (Telugu transliterated)
        - "mujhe bahut acha laga" → "hi" (Hindi transliterated)
        
        Args:
            text: Input text (native or transliterated)
            
        Returns:
            ISO 639-1 language code
        """
        words = self._normalized_tokens(text)
        
        # First, check for transliterated Indian language words
        for lang_code, hints in self.TRANSLITERATION_HINTS.items():
            hint_roots = {h.lower() for h in hints}
            matches = 0
            for word in words:
                if word in hint_roots:
                    matches += 1
                    continue
                # Accept light suffixing/noise (e.g., "irukkuin", "naanum").
                if any(word.startswith(root) and len(root) >= 4 for root in hint_roots):
                    matches += 1
            if matches >= 2:  # At least 2 matching words
                logger.info(f"Detected transliterated {lang_code} (matched {matches} words)")
                return lang_code
        
        return "en"
    
    def detect_transliteration(self, text: str) -> Optional[str]:
        """
        Check if text is transliterated Indian language in English script.
        
        Returns:
            Language code if transliterated, None otherwise
        """
        words = self._normalized_tokens(text)
        
        for lang_code, hints in self.TRANSLITERATION_HINTS.items():
            hint_roots = {h.lower() for h in hints}
            matches = 0
            for word in words:
                if word in hint_roots:
                    matches += 1
                    continue
                if any(word.startswith(root) and len(root) >= 4 for root in hint_roots):
                    matches += 1
            if matches >= 2:
                return lang_code
        return None
    
    async def translate_aws(
        self,
        text: str,
        source_lang: str,
        target_lang: str
    ) -> str:
        """Translate using AWS Translate."""
        if not self.aws_client:
            raise TranslationError("AWS Translate not configured")
        
        try:
            response = self.aws_client.translate_text(
                Text=text,
                SourceLanguageCode=source_lang,
                TargetLanguageCode=target_lang,
            )
            return response['TranslatedText']
        except Exception as e:
            logger.error(f"AWS Translate error: {e}")
            raise TranslationError(f"AWS Translate failed: {e}")
    
    async def translate_free(
        self,
        text: str,
        source_lang: str,
        target_lang: str
    ) -> str:
        """Translate using deep-translator (Google Translate wrapper - FREE)."""
        try:
            from deep_translator import GoogleTranslator
            
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            result = translator.translate(text)
            return result
        except Exception as e:
            logger.error(f"Free translation error: {e}")
            raise TranslationError(f"Free translation failed: {e}")
    
    async def translate(
        self,
        text: str,
        target_lang: str,
        source_lang: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Translate text with automatic fallback.
        Handles both native script and transliterated input.
        
        Args:
            text: Text to translate (native or transliterated)
            target_lang: Target language code
            source_lang: Source language code (auto-detected if None)
            
        Returns:
            Dict with translated_text, source_lang, target_lang, provider
        """
        # Auto-detect source language if not provided
        if not source_lang:
            source_lang = self.detect_language(text)
        
        # Check if source was transliterated
        is_transliterated = self.detect_transliteration(text) is not None
        
        # Skip if source and target are the same
        if source_lang == target_lang:
            return {
                "translated_text": text,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "provider": "none",
                "fallback_used": False,
                "transliterated_input": is_transliterated,
            }
        
        # Try AWS first
        if self.aws_client:
            try:
                logger.info(f"Translating with AWS: {source_lang} → {target_lang}")
                translated = await self.translate_aws(text, source_lang, target_lang)
                return {
                    "translated_text": translated,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "provider": "aws_translate",
                    "fallback_used": False,
                    "transliterated_input": is_transliterated,
                }
            except TranslationError:
                logger.warning("AWS Translate failed, using free fallback")
        
        # Fallback to free translation
        try:
            logger.info(f"Translating with free provider: {source_lang} → {target_lang}")
            translated = await self.translate_free(text, source_lang, target_lang)
            return {
                "translated_text": translated,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "provider": "google_free",
                "fallback_used": True,
                "transliterated_input": is_transliterated,
            }
        except TranslationError as e:
            raise TranslationError(f"All translation providers failed: {e}")
    
    async def translate_batch(
        self,
        texts: List[str],
        target_lang: str,
        source_lang: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Translate multiple texts."""
        results = []
        for text in texts:
            result = await self.translate(text, target_lang, source_lang)
            results.append(result)
        return results
    
    def get_supported_languages(self) -> List[Dict[str, str]]:
        """Get list of supported languages with metadata."""
        return [
            {
                "code": code,
                **info
            }
            for code, info in LANGUAGE_INFO.items()
        ]


# Singleton instance
_translation_service: Optional[TranslationService] = None


def get_translation_service() -> TranslationService:
    """Get or create the translation service singleton."""
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service
