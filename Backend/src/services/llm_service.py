"""
LLM Service for Content Room

AWS Bedrock-first with automatic fallback chain:
1. AWS Bedrock (nova)  — PRIMARY
2. Groq Cloud                  — FREE tier (no CC), ultra-fast Llama 3.3 70B
                                  https://console.groq.com/

Each provider is tried in order until one succeeds.
"""
import logging
import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from enum import Enum

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from services.dynamo_repositories import get_users_repo, get_analysis_repo, get_ai_cache_repo

logger = logging.getLogger(__name__)

LANGUAGE_LABELS = {
    "en": "English",
    "hi": "Hindi",
    "te": "Telugu",
    "ta": "Tamil",
    "bn": "Bengali",
    "kn": "Kannada",
    "ml": "Malayalam",
    "gu": "Gujarati",
    "or": "Odia",
}


def _normalize_language_label(language: Optional[str]) -> Optional[str]:
    if not language:
        return None
    raw = language.strip()
    if not raw:
        return None
    code = raw.lower()
    if code in LANGUAGE_LABELS:
        return LANGUAGE_LABELS[code]
    return raw


class LLMProvider(str, Enum):
    """Available LLM providers."""
    AWS_BEDROCK = "aws_bedrock"
    GROK = "grok"


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
    AWS Bedrock provider using Amazon Nova models.
    Primary provider with task-aware model routing.
    """
    
    def __init__(self):
        self.client = None
        if self.is_available():
            try:
                import importlib
                boto3 = importlib.import_module("boto3")
                self.client = boto3.client(
                    'bedrock-runtime',
                    # Force Bedrock runtime to N. Virginia for Nova Gen 2 path.
                    region_name='us-east-1',
                )
                logger.info("AWS Bedrock provider initialized in us-east-1")
            except Exception as e:
                logger.warning(f"Failed to initialize AWS Bedrock: {e}")
    
    def is_available(self) -> bool:
        return settings.aws_configured and settings.use_aws_bedrock

    @staticmethod
    def _is_nova_model(model_id: str) -> bool:
        # Handles both regional inference profile IDs and direct model IDs.
        # Examples:
        # - us.amazon.nova-lite-v1:0
        # - amazon.nova-lite-v1:0
        mid = (model_id or "")
        return "amazon.nova" in mid or ":inference-profile/" in mid

    def _expand_model_candidates(self, model_id: str) -> List[str]:
        """
        Use configured model IDs as-is.
        Supports explicit inference profile IDs/ARNs and direct Nova IDs.
        """
        if not model_id:
            return []
        return [model_id.strip()]
    
    async def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        if not self.client:
            raise ProviderUnavailableError("AWS Bedrock not configured")

        import json
        primary_model = model or settings.bedrock_model_id
        fallback_models = [
            primary_model,
            settings.bedrock_model_id_lite,
            settings.bedrock_model_id_micro,
            settings.bedrock_model_id_reasoning,
        ]
        # Keep order, expand model/profile variants, drop duplicates/empties.
        candidate_models: List[str] = []
        for model_id in fallback_models:
            for expanded in self._expand_model_candidates(model_id):
                if expanded not in candidate_models:
                    candidate_models.append(expanded)

        max_tokens = kwargs.get("max_tokens", 1024)
        task = kwargs.get("task", "general")
        errors: List[str] = []

        for chosen_model in candidate_models:
            try:
                if not self._is_nova_model(chosen_model):
                    raise ProviderUnavailableError(
                        f"Unsupported Bedrock model '{chosen_model}'. Expected Amazon Nova model ID."
                    )

                body = json.dumps(
                    {
                        "messages": [
                            {
                                "role": "user",
                                "content": [{"text": prompt}],
                            }
                        ],
                        "inferenceConfig": {
                            "maxTokens": max_tokens,
                            "temperature": kwargs.get("temperature", 0.7),
                        },
                    }
                )

                response = self.client.invoke_model(
                    modelId=chosen_model,
                    body=body,
                    contentType="application/json",
                    accept="application/json"
                )

                result = json.loads(response["body"].read())
                text = result.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")

                if not text or not text.strip():
                    raise ProviderUnavailableError("AWS Bedrock returned empty output")

                logger.info(f"AWS Bedrock success with model '{chosen_model}' for task '{task}'")
                return text
            except Exception as e:
                if "on-demand throughput" in str(e).lower():
                    logger.warning(
                        "Bedrock model '%s' requires an inference profile ID/ARN. "
                        "Consider setting BEDROCK_MODEL_ID* to APAC/US/EU profile IDs or profile ARN.",
                        chosen_model,
                    )
                errors.append(f"{chosen_model}: {e}")
                logger.warning(f"AWS Bedrock model '{chosen_model}' failed for task '{task}', trying next")
                continue

        err = "; ".join(errors)
        logger.error(f"AWS Bedrock failed across model chain: {err}")
        raise ProviderUnavailableError(f"AWS Bedrock failed: {err}")


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
    
    async def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        if not self.api_key:
            raise ProviderUnavailableError("Groq API key not configured")
        
        try:
            selected_model = model or kwargs.get("grok_model") or settings.groq_model
            # trust_env=False avoids broken proxy/env settings causing "failed to fetch".
            async with httpx.AsyncClient(timeout=120.0, trust_env=False) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": selected_model,
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


# ===========================================
# Main LLM Service with Fallback Chain
# ===========================================

class LLMService:
    """
    LLM Service with automatic fallback chain.

    Priority:
      1. AWS Bedrock   (primary)
      2. Groq Cloud    (free, no CC — https://console.groq.com/)
    """

    def __init__(self):
        self.providers: List[tuple[str, BaseLLMProvider]] = [
            (LLMProvider.AWS_BEDROCK, AWSBedrockProvider()),
            (LLMProvider.GROK,        GrokProvider()),
        ]

        # Log available providers
        available = [name for name, p in self.providers if p.is_available()]
        logger.info(f"LLM providers available: {available}")

    _REASONING_TASK_PREFIXES = (
        "calendar_",
        "dna_",
        "anti_cancel",
        "mental_health",
        "shadowban",
        "pipeline_shadowban",
        "signal_intel",
        "rag_",
        "burnout_",
    )
    _MICRO_TASKS = {"caption", "summary", "hashtags", "moderation"}

    def _select_bedrock_model(self, task: str, max_tokens: int) -> str:
        """
        Task-aware Nova model routing:
        - Micro: low-latency simple generation
        - Lite: balanced default
        - Nova 2 Lite: deeper reasoning / longer-context workflows
        """
        if task in self._MICRO_TASKS and max_tokens <= 512:
            return settings.bedrock_model_id_micro
        if task.startswith(self._REASONING_TASK_PREFIXES) or max_tokens >= 800:
            return settings.bedrock_model_id_reasoning
        return settings.bedrock_model_id

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        # Practical heuristic: ~4 chars/token for mixed English content.
        return max(1, int(len(text or "") / 4))

    def _estimate_cost_usd(self, provider: str, input_tokens: int, output_tokens: int) -> float:
        if provider == LLMProvider.AWS_BEDROCK:
            in_rate = settings.llm_cost_per_1k_input_tokens_bedrock
            out_rate = settings.llm_cost_per_1k_output_tokens_bedrock
        else:
            in_rate = settings.llm_cost_per_1k_input_tokens_groq
            out_rate = settings.llm_cost_per_1k_output_tokens_groq
        return (input_tokens / 1000.0) * in_rate + (output_tokens / 1000.0) * out_rate

    @staticmethod
    def _json_safe(value: Any) -> Any:
        if isinstance(value, dict):
            return {str(k): LLMService._json_safe(v) for k, v in sorted(value.items(), key=lambda i: str(i[0]))}
        if isinstance(value, (list, tuple)):
            return [LLMService._json_safe(v) for v in value]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)

    def _cache_enabled_for_request(self, task: str, kwargs: Dict[str, Any]) -> bool:
        if not settings.llm_cache_enabled:
            return False
        if kwargs.get("cache", True) is False:
            return False
        # Skip caching for explicitly streaming-like tasks if introduced later.
        if task in {"streaming"}:
            return False
        return True

    def _build_cache_prompt(
        self,
        *,
        prompt: str,
        task: str,
        kwargs: Dict[str, Any],
    ) -> str:
        user_scope = None
        if settings.llm_cache_user_scoped:
            user_id = kwargs.get("user_id")
            user_scope = str(user_id) if user_id else "anonymous"
        cache_input = {
            "task": task,
            "prompt": prompt,
            "user_scope": user_scope,
            "params": self._json_safe(
                {
                    k: v
                    for k, v in kwargs.items()
                    if k
                    not in {
                        "user_id",
                        "cache",
                        "cache_ttl_days",
                    }
                }
            ),
        }
        return json.dumps(cache_input, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    def _read_cache(
        self,
        *,
        prompt: str,
        task: str,
        kwargs: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if not self._cache_enabled_for_request(task, kwargs):
            return None
        try:
            cache_prompt = self._build_cache_prompt(prompt=prompt, task=task, kwargs=kwargs)
            cached_item = get_ai_cache_repo().get(cache_prompt, task)
            if not cached_item:
                return None
            raw_response = cached_item.get("response")
            if not raw_response:
                return None
            parsed = json.loads(raw_response)
            text = parsed.get("text")
            if not text:
                return None
            return {
                "text": text,
                "provider": parsed.get("provider", "cache"),
                "model": parsed.get("model"),
                "fallback_used": bool(parsed.get("fallback_used", False)),
                "cached": True,
            }
        except Exception as exc:
            logger.warning("LLM cache read failed for task '%s': %s", task, exc)
            return None

    def _write_cache(
        self,
        *,
        prompt: str,
        task: str,
        kwargs: Dict[str, Any],
        result: Dict[str, Any],
    ) -> None:
        if not self._cache_enabled_for_request(task, kwargs):
            return
        try:
            cache_prompt = self._build_cache_prompt(prompt=prompt, task=task, kwargs=kwargs)
            ttl_days = int(kwargs.get("cache_ttl_days") or settings.llm_cache_ttl_days)
            cache_payload = {
                "text": result.get("text"),
                "provider": result.get("provider"),
                "model": result.get("model"),
                "fallback_used": bool(result.get("fallback_used", False)),
            }
            get_ai_cache_repo().put(
                cache_prompt,
                task,
                json.dumps(cache_payload, ensure_ascii=False),
                ttl_days=max(1, ttl_days),
            )
        except Exception as exc:
            logger.warning("LLM cache write failed for task '%s': %s", task, exc)

    def _enforce_budgets(self, user_id: Optional[str]) -> None:
        global_usage = get_analysis_repo().get_global_llm_usage()
        if float(global_usage.get("llm_total_cost_usd", 0.0)) >= float(settings.llm_global_budget_usd):
            raise AllProvidersFailedError("Usage exceeded: global LLM budget limit reached")

        if user_id:
            user_usage = get_users_repo().get_llm_usage(user_id)
            if float(user_usage.get("llm_total_cost_usd", 0.0)) >= float(settings.llm_user_budget_usd):
                raise AllProvidersFailedError("Usage exceeded: user LLM budget limit reached")

    def _record_cost_usage(
        self,
        *,
        user_id: Optional[str],
        provider: str,
        model: Optional[str],
        task: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        cost_usd = self._estimate_cost_usd(provider, input_tokens, output_tokens)
        get_analysis_repo().increment_global_llm_usage(cost_usd, input_tokens, output_tokens)
        if user_id:
            get_users_repo().increment_llm_usage(user_id, cost_usd, input_tokens, output_tokens)
        logger.info(
            "llm_cost_event provider=%s model=%s task=%s user_id=%s input_tokens_est=%s output_tokens_est=%s cost_usd=%.6f",
            provider,
            model or "",
            task,
            user_id or "anonymous",
            input_tokens,
            output_tokens,
            cost_usd,
        )
        return cost_usd

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
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
        user_id = kwargs.get("user_id")

        cached = self._read_cache(prompt=prompt, task=task, kwargs=kwargs)
        if cached:
            logger.info("LLM cache hit for task '%s'", task)
            return cached

        # Budget guard before executing provider calls.
        self._enforce_budgets(str(user_id) if user_id else None)
        
        for i, (name, provider) in enumerate(self.providers):
            if not provider.is_available():
                continue
            
            try:
                logger.info(f"Trying LLM provider: {name} for task: {task}")
                provider_kwargs = dict(kwargs)
                if name == LLMProvider.AWS_BEDROCK and "model" not in provider_kwargs:
                    provider_kwargs["model"] = self._select_bedrock_model(
                        task=task,
                        max_tokens=int(provider_kwargs.get("max_tokens", 1024)),
                    )
                text = await provider.generate(prompt, task=task, **provider_kwargs)
                input_tokens_est = self._estimate_tokens(prompt)
                output_tokens_est = self._estimate_tokens(text)
                self._record_cost_usage(
                    user_id=str(user_id) if user_id else None,
                    provider=name,
                    model=provider_kwargs.get("model"),
                    task=task,
                    input_tokens=input_tokens_est,
                    output_tokens=output_tokens_est,
                )

                result = {
                    "text": text,
                    "provider": name,
                    "model": provider_kwargs.get("model"),
                    "fallback_used": fallback_used,
                }
                self._write_cache(prompt=prompt, task=task, kwargs=kwargs, result=result)
                return result
                
            except ProviderUnavailableError as e:
                errors.append(f"{name}: {e}")
                logger.warning(f"Provider {name} failed, trying next...")
                fallback_used = True
                continue
        
        # All providers failed
        error_msg = "; ".join(errors)
        logger.error(f"All LLM providers failed: {error_msg}")
        raise AllProvidersFailedError(f"All providers failed: {error_msg}")
    
    async def generate_caption(
        self, 
        content: str, 
        content_type: str = "text",
        max_length: int = 280,
        platform: Optional[str] = None,
        language: Optional[str] = None,
        model: Optional[str] = None,
        user_id: Optional[str] = None,
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

        language_label = _normalize_language_label(language)
        language_instruction = (
            f"- Output language: {language_label}. Keep the full caption in this language."
            if language_label and language_label.lower() != "english"
            else "- Output language: English."
        )
        
        prompt = f"""You are an expert social media copywriter creating a caption for {platform or 'social media'}.

Create a compelling caption for this {content_type} content.

Requirements:
- Target length: {max_length} characters
{length_guidance}
{tone_instructions}
{language_instruction}

Content: {content}

Write the caption now (no explanations, just the caption):"""
        return await self.generate(
            prompt,
            task="caption",
            max_tokens=estimated_tokens,
            model=model,
            user_id=user_id,
        )
    
    async def generate_summary(
        self,
        content: str,
        max_length: int = 150,
        language: Optional[str] = None,
        model: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a summary of content.
        
        Args:
            content: The content to summarize
            max_length: Maximum summary length in characters
        """
        language_label = _normalize_language_label(language)
        language_instruction = (
            f"Write the summary in {language_label}."
            if language_label and language_label.lower() != "english"
            else "Write the summary in English."
        )
        prompt = f"""Summarize the following content concisely.
Focus on the key points and main message.

IMPORTANT: Keep the summary under {max_length} characters.
{language_instruction}

Content: {content}

Summary:"""
        return await self.generate(prompt, task="summary", model=model, user_id=user_id)
    
    async def generate_hashtags(
        self,
        content: str,
        count: int = 5,
        language: Optional[str] = None,
        model: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate hashtags for content."""
        language_label = _normalize_language_label(language)
        language_instruction = (
            f"Generate hashtags appropriate for {language_label} audience/context."
            if language_label and language_label.lower() != "english"
            else "Generate hashtags appropriate for English audience/context."
        )
        prompt = f"""Generate {count} relevant hashtags for the following content.
Return only the hashtags, each on a new line, starting with #.
Make them trending-friendly and discoverable.
{language_instruction}

Content: {content}

Hashtags:"""
        result = await self.generate(prompt, task="hashtags", model=model, user_id=user_id)
        
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
