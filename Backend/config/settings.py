"""
Content Room Backend Configuration

AWS-first configuration with automatic fallback to free alternatives.
Follows 12-factor app principles for environment-based configuration.
"""
from functools import lru_cache
from typing import Optional, List
import os
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Application settings with AWS-first, fallback-ready architecture.

    Priority Chain:
    1. AWS Services (primary)
    2. Groq API        — free tier, no CC  (https://console.groq.com/)
    3. OpenRouter      — free 50 req/day   (https://openrouter.ai/)
    4. Cerebras        — free tier          (https://cloud.cerebras.ai/)
    5. Ollama / local models (offline mode)
    """
    
    # ===========================================
    # AWS Configuration (PRIMARY)
    # ===========================================
    aws_access_key_id: Optional[str] = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(default=None, alias="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    
    # Amazon Bedrock — Primary LLM
    # Claude 3 Sonnet: complex reasoning, agent workflows, cultural rewriting
    bedrock_model_id: str = Field(
        default="anthropic.claude-3-sonnet-20240229-v1:0",
        alias="BEDROCK_MODEL_ID"
    )

    # AWS Service Toggles
    use_aws_bedrock: bool = Field(default=True, alias="USE_AWS_BEDROCK")
    use_aws_rekognition: bool = Field(default=True, alias="USE_AWS_REKOGNITION")
    use_aws_transcribe: bool = Field(default=True, alias="USE_AWS_TRANSCRIBE")
    use_aws_translate: bool = Field(default=True, alias="USE_AWS_TRANSLATE")
    use_aws_comprehend: bool = Field(default=True, alias="USE_AWS_COMPREHEND")
    use_aws_sagemaker: bool = Field(default=True, alias="USE_AWS_SAGEMAKER")
    use_aws_dynamodb: bool = Field(default=False, alias="USE_AWS_DYNAMODB")
    use_aws_personalize: bool = Field(default=False, alias="USE_AWS_PERSONALIZE")
    
    # Amazon S3 (PRIMARY storage) — raw media, generated assets, processed files
    use_aws_s3: bool = Field(default=True, alias="USE_AWS_S3")
    aws_s3_region: str = Field(default="us-east-1", alias="AWS_S3_REGION")
    
    # Intelligence Feature Toggles (graceful fallback if False)
    enable_culture_engine: bool = Field(default=True, alias="ENABLE_CULTURE_ENGINE")
    enable_risk_reach_dial: bool = Field(default=True, alias="ENABLE_RISK_REACH_DIAL")
    enable_dna_fingerprint: bool = Field(default=True, alias="ENABLE_DNA_FINGERPRINT")
    enable_anti_cancel: bool = Field(default=True, alias="ENABLE_ANTI_CANCEL")
    enable_mental_health: bool = Field(default=True, alias="ENABLE_MENTAL_HEALTH")
    enable_asset_explosion: bool = Field(default=True, alias="ENABLE_ASSET_EXPLOSION")
    enable_shadowban_predictor: bool = Field(default=True, alias="ENABLE_SHADOWBAN_PREDICTOR")
    
    # SageMaker Embeddings endpoint (for DNA fingerprinting)
    sagemaker_embedding_endpoint: Optional[str] = Field(default=None, alias="SAGEMAKER_EMBEDDING_ENDPOINT")
    
    # LLM Fallback Chain
    # ===========================================
    grok_api_key: Optional[str] = Field(default=None, alias="GROK_API_KEY")

    # OpenRouter — free 50 req/day, no CC required
    # Sign up at https://openrouter.ai/ and generate a free API key (sk-or-v1-...)
    openrouter_api_key: Optional[str] = Field(default=None, alias="OPENROUTER_API_KEY")

    # Cerebras — free tier, ultra-fast inference
    # Sign up at https://cloud.cerebras.ai/ and generate a free API key (csk-...)
    cerebras_api_key: Optional[str] = Field(default=None, alias="CEREBRAS_API_KEY")

    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3", alias="OLLAMA_MODEL")
    
    # ===========================================
    # Storage (S3 → Firebase → Local)
    # ===========================================
    s3_bucket_name: Optional[str] = Field(default=None, alias="S3_BUCKET_NAME")
    firebase_storage_bucket: Optional[str] = Field(default=None, alias="FIREBASE_STORAGE_BUCKET")
    firebase_credentials_path: Optional[str] = Field(default=None, alias="FIREBASE_CREDENTIALS_PATH")
    storage_path: str = Field(default="./uploads", alias="STORAGE_PATH")
    storage_base_url: str = Field(default="/uploads", alias="STORAGE_BASE_URL")

    @property
    def storage_provider(self) -> str:
        """Determine the best available storage provider.
        Priority: AWS S3 → Firebase → Local
        """
        if self.aws_configured and self.use_aws_s3 and self.s3_bucket_name:
            return "aws_s3"
        if self.firebase_storage_bucket:
            return "firebase"
        return "local"
    
    # ===========================================
    # Task Scheduler
    # ===========================================
    scheduler_enabled: bool = Field(default=True, alias="SCHEDULER_ENABLED")
    scheduler_check_interval: int = Field(default=60, alias="SCHEDULER_CHECK_INTERVAL")
    
    # ===========================================
    # External Services
    # ===========================================
    youtube_api_key: Optional[str] = Field(default=None, alias="YOUTUBE_API_KEY")

    moderation_service_url: str = Field(
        default="http://localhost:8001", 
        alias="MODERATION_SERVICE_URL"
    )
    
    # ===========================================
    # Database (RDS → SQLite fallback)
    # ===========================================
    # Amazon RDS (PostgreSQL) — PRIMARY per 24-hour migration goal.
    # Set AWS_RDS_URL to: postgresql+asyncpg://user:password@<endpoint>:5432/contentos
    aws_rds_url: Optional[str] = Field(default=None, alias="AWS_RDS_URL")
    
    # SQLite fallback for local dev / offline mode
    database_url: str = Field(
        default="sqlite+aiosqlite:///./contentos.db",
        alias="DATABASE_URL"
    )

    @property
    def active_database_url(self) -> str:
        """Return AWS RDS (PostgreSQL) URL if configured, else SQLite fallback."""
        if self.aws_rds_url:
            return self.aws_rds_url
        return self.database_url
    
    # ===========================================
    # Security
    # ===========================================
    secret_key: str = Field(
        default="content-room-dev-secret-key-change-in-production",
        alias="SECRET_KEY"
    )
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=1440, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")
    rate_limit_burst: int = Field(default=10, alias="RATE_LIMIT_BURST")
    
    # ===========================================
    # Server
    # ===========================================
    debug: bool = Field(default=True, alias="DEBUG")
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        alias="CORS_ORIGINS"
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    # ===========================================
    # Computed Properties
    # ===========================================
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def aws_configured(self) -> bool:
        """Check if AWS credentials are available."""
        return bool(self.aws_access_key_id and self.aws_secret_access_key)
    
    @property
    def llm_provider(self) -> str:
        """
        Determine the best available LLM provider.
        Priority: AWS Bedrock (Claude 3 Sonnet) → Grok → OpenRouter → Ollama
        """
        if self.aws_configured and self.use_aws_bedrock:
            return "aws_bedrock"  # Uses bedrock_model_id (Claude 3 Sonnet)
        if self.grok_api_key:
            return "grok"
        if self.openrouter_api_key:
            return "openrouter"
        return "ollama"
    
    @property
    def vision_provider(self) -> str:
        """
        Determine the best available Vision provider.
        Priority: AWS Rekognition → OpenCV (local)
        """
        if self.aws_configured and self.use_aws_rekognition:
            return "aws_rekognition"
        return "opencv"
    
    @property
    def speech_provider(self) -> str:
        """
        Determine the best available Speech provider.
        Priority: AWS Transcribe → Whisper (local)
        """
        if self.aws_configured and self.use_aws_transcribe:
            return "aws_transcribe"
        return "whisper"
    
    @property
    def translation_provider(self) -> str:
        """
        Determine the best available Translation provider.
        Priority: AWS Translate → deep-translator (Google free)
        """
        if self.aws_configured and self.use_aws_translate:
            return "aws_translate"
        return "google_free"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings instance.
    Uses LRU cache to avoid re-parsing environment on every request.
    """
    return Settings()


# Convenience export
settings = get_settings()
