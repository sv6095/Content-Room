"""
LLM Service for Content Room

AWS Bedrock-first with automatic fallback chain:
1. AWS Bedrock (Claude/Titan)  — PRIMARY
2. Groq Cloud                  — FREE tier (no CC), ultra-fast Llama 3.3 70B
                                  https://console.groq.com/
3. OpenRouter                  — FREE tier 50 req/day, no CC required
                                  Routes to Llama 3.3 70B / Gemini Flash / Mistral
                                  https://openrouter.ai/  (sign up → free API key)
4. Cerebras Inference          — FREE tier, ultra-fast Llama 3.1 70B
                                  https://cloud.cerebras.ai/  (sign up → free API key)
7. Simple Templates            — ULTIMATE fallback (no API needed)

Each provider is tried in order until one succeeds.
"""
import logging
import random
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from enum import Enum

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Available LLM providers."""
    AWS_BEDROCK = "aws_bedrock"
    GROK = "grok"
    OPENROUTER = "openrouter"
    CEREBRAS = "cerebras"
    OLLAMA = "ollama"
    SIMPLE = "simple_template"


class LLMError(Exception):
    """Base exception for LLM errors."""
    pass


class ProviderUnavailableError(LLMError):
    """Raised when a provider is unavailable."""
    pass


class AllProvidersFailedError(LLMError):
    """Raised when all providers fail."""
    pass


# ===========================================
# Provider Implementations
# ===========================================

class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate text completion."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is configured and available."""
        pass


class AWSBedrockProvider(BaseLLMProvider):
    """
    AWS Bedrock provider using Claude or Titan.
    PRIMARY for AWS hackathon.
    """
    
    def __init__(self):
        self.client = None
        if self.is_available():
            try:
                import boto3
                self.client = boto3.client(
                    'bedrock-runtime',
                    region_name=settings.aws_region,
                )
                logger.info("AWS Bedrock provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize AWS Bedrock: {e}")
    
    def is_available(self) -> bool:
        return settings.aws_configured and settings.use_aws_bedrock
    
    async def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        if not self.client:
            raise ProviderUnavailableError("AWS Bedrock not configured")
        
        try:
            import json
            chosen_model = model or settings.bedrock_model_id
            max_tokens = kwargs.get("max_tokens", 1024)

            if chosen_model.startswith("amazon.nova"):
                body = json.dumps(
                    {
                        "messages": [
                            {
                                "role": "user",
                                "content": [{"text": prompt}],
                            }
                        ],
                        "inferenceConfig": {
                            "max_new_tokens": max_tokens,
                            "temperature": kwargs.get("temperature", 0.7),
                        },
                    }
                )
            else:
                # Backward-compatible Anthropic format
                body = json.dumps(
                    {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": max_tokens,
                        "messages": [{"role": "user", "content": prompt}],
                    }
                )
            
            response = self.client.invoke_model(
                modelId=chosen_model,
                body=body,
                contentType="application/json",
                accept="application/json"
            )
            
            result = json.loads(response['body'].read())
            if chosen_model.startswith("amazon.nova"):
                return result.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")
            return result['content'][0]['text']
            
        except Exception as e:
            logger.error(f"AWS Bedrock error: {e}")
            raise ProviderUnavailableError(f"AWS Bedrock failed: {e}")


class GrokProvider(BaseLLMProvider):
    """
    Groq provider using Groq Cloud API.
    Fast inference with open-source models.
    First fallback when AWS is unavailable.
    
    Note: Uses GROQ_API_KEY (gsk_*) from groq.com, not X.AI Grok.
    """
    
    def __init__(self):
        self.api_key = settings.grok_api_key  # Same env var, works for Groq
        self.base_url = "https://api.groq.com/openai/v1"  # Groq API endpoint
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    async def generate(self, prompt: str, model: str = "llama-3.3-70b-versatile", **kwargs) -> str:
        if not self.api_key:
            raise ProviderUnavailableError("Groq API key not configured")
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": kwargs.get("max_tokens", 1024),
                        "temperature": kwargs.get("temperature", 0.7),
                    }
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
                
        except Exception as e:
            logger.error(f"Groq error: {e}")
            raise ProviderUnavailableError(f"Groq failed: {e}")


class OpenRouterProvider(BaseLLMProvider):
    """
    OpenRouter — Free tier, no credit card required.
    Single API that routes to the best free model available.

    Free tier: 50 requests/day, 200 req/min (with account).
    Free models include: Llama 3.3 70B, Gemini Flash, Mistral 7B, DeepSeek.

    Sign up (free) at: https://openrouter.ai/
    API key format: sk-or-v1-...
    Docs: https://openrouter.ai/docs
    """

    # Ordered list of free model IDs to try (rotates on failure)
    FREE_MODELS = [
        "meta-llama/llama-3.3-70b-instruct:free",   # Llama 3.3 70B — best quality
        "google/gemini-flash-1.5:free",              # Gemini Flash — very reliable
        "mistralai/mistral-7b-instruct:free",        # Mistral 7B — lightweight fallback
        "deepseek/deepseek-r1:free",                 # DeepSeek R1 — reasoning model
    ]
    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self):
        self.api_key = getattr(settings, "openrouter_api_key", None) or ""

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate(self, prompt: str, **kwargs) -> str:
        if not self.api_key:
            raise ProviderUnavailableError("OpenRouter API key not set")

        for model in self.FREE_MODELS:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(
                        f"{self.BASE_URL}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                            # Recommended by OpenRouter for free-tier routing
                            "HTTP-Referer": "https://github.com/Neil2813/Content-Room",
                            "X-Title": "Content Room",
                        },
                        json={
                            "model": model,
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": kwargs.get("max_tokens", 1024),
                            "temperature": kwargs.get("temperature", 0.7),
                        },
                    )
                    if resp.status_code == 429:
                        logger.warning(f"OpenRouter rate limit hit for model {model}, trying next")
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    text = data["choices"][0]["message"]["content"].strip()
                    if text:
                        logger.info(f"OpenRouter success with model: {model}")
                        return text
            except Exception as e:
                logger.warning(f"OpenRouter model {model} failed: {e}")
                continue

        raise ProviderUnavailableError("All OpenRouter free models failed or daily limit reached")


class CerebrasProvider(BaseLLMProvider):
    """
    Cerebras Inference — Free tier, no credit card required.
    Extremely fast inference (800+ tokens/sec) powered by Cerebras CS-3 chips.

    Free tier: generous daily token limit, Llama 3.1 8B and 70B available.
    Sign up (free) at: https://cloud.cerebras.ai/
    API key format: csk-...
    Docs: https://inference-docs.cerebras.ai/
    """

    BASE_URL = "https://api.cerebras.ai/v1"
    # Models available on free tier
    FREE_MODELS = [
        "llama-3.3-70b",   # Best quality
        "llama3.1-8b",     # Faster, lighter fallback
    ]

    def __init__(self):
        self.api_key = getattr(settings, "cerebras_api_key", None) or ""

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate(self, prompt: str, **kwargs) -> str:
        if not self.api_key:
            raise ProviderUnavailableError("Cerebras API key not set")

        for model in self.FREE_MODELS:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(
                        f"{self.BASE_URL}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model,
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": kwargs.get("max_tokens", 1024),
                            "temperature": kwargs.get("temperature", 0.7),
                        },
                    )
                    if resp.status_code == 429:
                        logger.warning(f"Cerebras rate limit for model {model}, trying next")
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    text = data["choices"][0]["message"]["content"].strip()
                    if text:
                        logger.info(f"Cerebras success with model: {model}")
                        return text
            except Exception as e:
                logger.warning(f"Cerebras model {model} failed: {e}")
                continue

        raise ProviderUnavailableError("Cerebras models failed or rate-limited")



class OllamaProvider(BaseLLMProvider):
    """
    Ollama local provider.
    Completely FREE, runs locally.
    """
    
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model
        self._available = False
        self._check_availability()
    
    def _check_availability(self):
        """Check if Ollama is actually running."""
        try:
            import httpx
            response = httpx.get(f"{self.base_url}/api/tags", timeout=2.0)
            self._available = response.status_code == 200
        except:
            self._available = False
    
    def is_available(self) -> bool:
        return self._available
    
    async def generate(self, prompt: str, **kwargs) -> str:
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                    }
                )
                response.raise_for_status()
                data = response.json()
                return data["response"]
                
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            raise ProviderUnavailableError(f"Ollama failed: {e}")


class SimpleTemplateProvider(BaseLLMProvider):
    """
    Simple template-based provider.
    ULTIMATE FALLBACK - no external API needed.
    Uses templates and randomization for demo purposes.
    """
    
    CAPTION_TEMPLATES = [
        "✨ There's something magical about moments like these... {content} 🌟 What does this make you feel? Drop your thoughts below! 👇 #AestheticVibes #MoodBoard #Trending",
        "🌸 In a world of chaos, find your peace... {content} � Tag someone who needs to see this beauty 💕 #VibezOnly #BeautifulMoments #Aesthetic",
        "� Stop scrolling, you need to see this! {content} ✨ Double tap if this hits different � #InstaVibes #ContentCreator #Viral",
        "� Life is all about these little wonders... {content} 🌿 What's your favorite way to appreciate beauty? 💭 #SlowLiving #Mindful #NatureLovers",
        "⭐ Some things just speak to the soul... {content} 🎨 Save this for when you need a reminder ❤️ #DailyInspiration #AestheticFeed #ContentRoom",
    ]
    
    SUMMARY_TEMPLATES = [
        "This content discusses {topic}. Key points include the main ideas presented.",
        "Summary: The content focuses on {topic} and provides valuable insights.",
        "In brief: {topic} is the central theme with important takeaways.",
    ]
    
    HASHTAGS = [
        "#ContentRoom", "#AI", "#ContentCreation", "#Digital", "#Tech",
        "#Innovation", "#Creative", "#Trending", "#Viral", "#Social",
        "#Marketing", "#Growth", "#Engagement", "#Strategy", "#Success",
    ]
    
    def is_available(self) -> bool:
        return True  # Always available
    
    async def generate(self, prompt: str, **kwargs) -> str:
        prompt_lower = prompt.lower()
        
        # Detect task type from prompt
        if "caption" in prompt_lower:
            # Extract content from prompt
            content = self._extract_content(prompt)
            
            # Determine target length from max_tokens kwarg
            max_tokens = kwargs.get("max_tokens", 256)
            target_chars = max_tokens * 3  # rough estimate
            
            template = random.choice(self.CAPTION_TEMPLATES)
            base_caption = template.format(content=content[:200])
            
            # If target is much larger than template, expand with more content
            if target_chars > 500 and len(base_caption) < target_chars:
                extras = [
                    "\n\nThis is one of those moments that truly stays with you. The kind of experience that makes you pause and appreciate what life has to offer.",
                    "\n\nThere's depth and beauty here that words can barely capture. Every detail tells its own story, and together they create something unforgettable.",
                    "\n\nWhat stands out most is how every element comes together so perfectly. It's the little things that make the biggest impact.",
                    "\n\nIf this resonated with you, share your own experience in the comments. Let's build a community of people who appreciate the extraordinary in the ordinary.",
                    "\n\nRemember: every great story starts with a moment just like this one. Don't let these moments pass you by without soaking them in.",
                ]
                while len(base_caption) < target_chars and extras:
                    base_caption += extras.pop(0)
            
            return base_caption[:target_chars] if target_chars < len(base_caption) else base_caption
        
        elif "summary" in prompt_lower or "summarize" in prompt_lower:
            content = self._extract_content(prompt)
            topic = content[:50] + "..." if len(content) > 50 else content
            template = random.choice(self.SUMMARY_TEMPLATES)
            return template.format(topic=topic)
        
        elif "hashtag" in prompt_lower:
            count = 5
            # Try to extract count from prompt
            for word in prompt.split():
                if word.isdigit():
                    count = int(word)
                    break
            selected = random.sample(self.HASHTAGS, min(count, len(self.HASHTAGS)))
            return "\n".join(selected)
        
        elif "rewrite" in prompt_lower or "tone" in prompt_lower:
            content = self._extract_content(prompt)
            if "professional" in prompt_lower:
                return f"We are pleased to inform you that {content}"
            elif "casual" in prompt_lower:
                return f"Hey! Just wanted to share - {content} 😊"
            elif "engaging" in prompt_lower:
                return f"🔥 You won't believe this: {content}! 🚀"
            return content
        
        elif "moderation" in prompt_lower or "safety" in prompt_lower:
            # Return safe analysis
            return """SAFETY_SCORE: 85
FLAGS: none
EXPLANATION: Content appears to be safe for publication."""
        
        else:
            # Generic response
            return f"Generated response for: {prompt[:100]}..."
    
    def _extract_content(self, prompt: str) -> str:
        """Extract the main content from a prompt."""
        # Look for content after common markers
        markers = ["Content:", "content:", "Text:", "text:", "Original:"]
        for marker in markers:
            if marker in prompt:
                parts = prompt.split(marker)
                if len(parts) > 1:
                    # Get content until next section or end
                    content = parts[1].split("\n\n")[0].strip()
                    return content
        # Return last 200 chars if no marker found
        return prompt[-200:].strip()


# ===========================================
# Main LLM Service with Fallback Chain
# ===========================================

class LLMService:
    """
    LLM Service with automatic fallback chain.

    Priority:
      1. AWS Bedrock   (primary)
      2. Groq Cloud    (free, no CC — https://console.groq.com/)
      3. OpenRouter    (free 50 req/day — https://openrouter.ai/)
      5. Cerebras      (free tier — https://cloud.cerebras.ai/)
      6. Ollama        (local / offline)
      7. Simple Templates (always available, no API)
    """

    def __init__(self):
        self.providers: List[tuple[str, BaseLLMProvider]] = [
            (LLMProvider.AWS_BEDROCK, AWSBedrockProvider()),
            (LLMProvider.GROK,        GrokProvider()),
            (LLMProvider.OPENROUTER,  OpenRouterProvider()),
            (LLMProvider.CEREBRAS,    CerebrasProvider()),
            (LLMProvider.OLLAMA,      OllamaProvider()),
            (LLMProvider.SIMPLE,      SimpleTemplateProvider()),  # Ultimate fallback
        ]

        # Log available providers
        available = [name for name, p in self.providers if p.is_available()]
        logger.info(f"LLM providers available: {available}")
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def generate(
        self,
        prompt: str,
        task: str = "general",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate text using the fallback chain.
        
        Args:
            prompt: The input prompt
            task: Task type for logging
            **kwargs: Additional parameters (max_tokens, temperature, etc.)
        
        Returns:
            Dict with 'text', 'provider', and 'fallback_used'
        """
        errors = []
        fallback_used = False
        
        for i, (name, provider) in enumerate(self.providers):
            if not provider.is_available():
                continue
            
            try:
                logger.info(f"Trying LLM provider: {name} for task: {task}")
                text = await provider.generate(prompt, **kwargs)
                
                return {
                    "text": text,
                    "provider": name,
                    "fallback_used": fallback_used,
                }
                
            except ProviderUnavailableError as e:
                errors.append(f"{name}: {e}")
                logger.warning(f"Provider {name} failed, trying next...")
                fallback_used = True
                continue
        
        # All providers failed (shouldn't happen with SimpleTemplateProvider)
        error_msg = "; ".join(errors)
        logger.error(f"All LLM providers failed: {error_msg}")
        raise AllProvidersFailedError(f"All providers failed: {error_msg}")
    
    async def generate_caption(
        self, 
        content: str, 
        content_type: str = "text",
        max_length: int = 280,
        platform: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a platform-optimized caption for content.
        
        Args:
            content: The content to generate a caption for
            content_type: Type of content (text, image, audio, video)
            max_length: Maximum caption length in characters (up to 3000)
            platform: Target platform (twitter, instagram, linkedin, custom)
        """
        # Clamp max_length to sensible bounds
        max_length = max(50, min(max_length, 3000))
        
        # Calculate appropriate max_tokens based on requested character length
        # Roughly 1 token ≈ 3-4 characters; add generous padding
        estimated_tokens = max(256, int(max_length / 2.5) + 100)
        
        # Platform-specific tone customization
        if platform == "linkedin":
            tone_instructions = """- Tone: Professional, thought-leadership, industry-focused
- Style: Start with an insight or professional perspective
- Language: Clear, authoritative, and value-driven
- Emojis: Minimal (1-2 professional emojis like 💼 📊 🚀)
- Hashtags: Industry-relevant and professional (#Leadership #Innovation #Business)
- Call-to-action: Invite professional discussion or connection"""
        elif platform == "twitter" or platform == "x":
            tone_instructions = """- Tone: Knowledgeable, Reserved, and Insightful
- Style: Concise, intelligent, and thought-provoking
- Language: Sharp, clear, intellectual without being pretentious
- Emojis: Very minimal (0-1 thoughtful emoji)
- Hashtags: Trending topics and knowledge-based tags
- Call-to-action: Spark intelligent conversation or retweets"""
        elif platform == "instagram":
            tone_instructions = """- Tone: Aesthetic, Dreamy, and Visually Evocative
- Style: Start with a mood-setting line or poetic phrase
- Language: Emotional, relatable, and visually descriptive
- Emojis: 3-5 aesthetic emojis spread throughout (✨ 🌸 💫 🌙 🦋)
- Hashtags: Aesthetic and lifestyle tags (#AestheticVibes #InstaDaily #VisualMoodboard)
- Call-to-action: Engage emotions, tag friends, save for later"""
        else:
            # Default/Custom: balanced aesthetic approach
            tone_instructions = """- Tone: Engaging and relatable
- Style: Mix of aesthetic and informative
- Emojis: 2-4 relevant emojis
- Hashtags: Mix of trending and niche tags
- Call-to-action: Encourage engagement"""
        
        # Adjust length guidance based on the requested size
        if max_length >= 1500:
            length_guidance = f"""- You MUST write a LONG, detailed caption that is close to {max_length} characters.
- Write multiple paragraphs with rich detail, storytelling, and emotional depth.
- Include line breaks between paragraphs for readability.
- Aim for AT LEAST {int(max_length * 0.7)} characters. Going under {int(max_length * 0.5)} characters is UNACCEPTABLE."""
        elif max_length >= 500:
            length_guidance = f"""- Write a medium-length caption of approximately {max_length} characters.
- Include 2-3 paragraphs with good detail and engagement hooks.
- Aim for AT LEAST {int(max_length * 0.6)} characters."""
        else:
            length_guidance = f"""- Keep total length under {max_length} characters.
- Be concise but impactful."""
        
        prompt = f"""You are an expert social media copywriter creating a caption for {platform or 'social media'}.

Create a compelling caption for this {content_type} content.

Requirements:
- Target length: {max_length} characters
{length_guidance}
{tone_instructions}

Content: {content}

Write the caption now (no explanations, just the caption):"""
        return await self.generate(prompt, task="caption", max_tokens=estimated_tokens)
    
    async def generate_summary(self, content: str, max_length: int = 150) -> Dict[str, Any]:
        """Generate a summary of content.
        
        Args:
            content: The content to summarize
            max_length: Maximum summary length in characters
        """
        prompt = f"""Summarize the following content concisely.
Focus on the key points and main message.

IMPORTANT: Keep the summary under {max_length} characters.

Content: {content}

Summary:"""
        return await self.generate(prompt, task="summary")
    
    async def generate_hashtags(self, content: str, count: int = 5) -> Dict[str, Any]:
        """Generate hashtags for content."""
        prompt = f"""Generate {count} relevant hashtags for the following content.
Return only the hashtags, each on a new line, starting with #.
Make them trending-friendly and discoverable.

Content: {content}

Hashtags:"""
        result = await self.generate(prompt, task="hashtags")
        
        # Parse hashtags from response
        lines = result["text"].strip().split("\n")
        hashtags = [line.strip() for line in lines if line.strip().startswith("#")]
        
        # If no hashtags parsed, create from content
        if not hashtags:
            words = content.split()[:count]
            hashtags = [f"#{word.strip('.,!?').capitalize()}" for word in words if len(word) > 3]
        
        return {
            **result,
            "hashtags": hashtags[:count]
        }


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create the LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
