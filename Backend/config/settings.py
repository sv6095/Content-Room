"""
Content Room Backend Configuration

AWS-first configuration with automatic fallback to free alternatives.
Follows 12-factor app principles for environment-based configuration.
"""
from functools import lru_cache
from typing import Optional, List
import os
from pydantic_settings import BaseSettings
from pydantic import Field, AliasChoices


class Settings(BaseSettings):
    """
    Application settings with AWS-first, fallback-ready architecture.

    Priority Chain:
    1. AWS Services (primary)
    2. Groq API        — free tier, no CC  (https://console.groq.com/)
    """
    
    # ===========================================
    # AWS Configuration (PRIMARY)
    # ===========================================
    aws_region: str = Field(default="ap-south-1", alias="AWS_REGION")
    
    # Amazon Bedrock — Primary LLM (Nova family)
    # Supports task-aware routing across Micro, Lite, and Nova 2 Lite.
    bedrock_model_id_micro: str = Field(
        default="us.amazon.nova-micro-v1:0",
        alias="BEDROCK_MODEL_ID_MICRO"
    )
    bedrock_model_id_lite: str = Field(
        default="us.amazon.nova-lite-v1:0",
        alias="BEDROCK_MODEL_ID_LITE"
    )
    bedrock_model_id: str = Field(
        default="us.amazon.nova-lite-v1:0",
        validation_alias=AliasChoices("BEDROCK_MODEL_ID", "BEDROCK_MODEL_ID_LITE")
    )
    bedrock_model_id_reasoning: str = Field(
        default="us.amazon.nova-2-lite-v1:0",
        alias="BEDROCK_MODEL_ID_REASONING"
    )

    # AWS Service Toggles
    use_aws_bedrock: bool = Field(default=True, alias="USE_AWS_BEDROCK")
    use_aws_rekognition: bool = Field(default=True, alias="USE_AWS_REKOGNITION")
    use_aws_transcribe: bool = Field(default=True, alias="USE_AWS_TRANSCRIBE")
    use_aws_translate: bool = Field(default=True, alias="USE_AWS_TRANSLATE")
    use_aws_comprehend: bool = Field(default=True, alias="USE_AWS_COMPREHEND")
    use_aws_sagemaker: bool = Field(default=True, alias="USE_AWS_SAGEMAKER")
    use_aws_dynamodb: bool = Field(default=True, alias="USE_AWS_DYNAMODB")
    use_aws_personalize: bool = Field(default=False, alias="USE_AWS_PERSONALIZE")
    use_aws_mediaconvert: bool = Field(default=True, alias="USE_AWS_MEDIACONVERT")
    use_aws_nova_reel: bool = Field(default=True, alias="USE_AWS_NOVA_REEL")
    use_aws_titan_image: bool = Field(default=True, alias="USE_AWS_TITAN_IMAGE")
    use_aws_nova_canvas: bool = Field(default=True, alias="USE_AWS_NOVA_CANVAS")
    
    # Amazon S3 (PRIMARY storage) — raw media, generated assets, processed files
    use_aws_s3: bool = Field(default=True, alias="USE_AWS_S3")
    aws_s3_region: str = Field(default="ap-south-1", alias="AWS_S3_REGION")
    mediaconvert_endpoint: Optional[str] = Field(default=None, alias="MEDIACONVERT_ENDPOINT")
    mediaconvert_role_arn: Optional[str] = Field(default=None, alias="MEDIACONVERT_ROLE_ARN")
    mediaconvert_output_bucket: Optional[str] = Field(default=None, alias="MEDIACONVERT_OUTPUT_BUCKET")
    nova_reel_model_id: str = Field(default="us.amazon.nova-reel-v1:0", alias="NOVA_REEL_MODEL_ID")
    nova_reel_output_s3_uri: Optional[str] = Field(default=None, alias="NOVA_REEL_OUTPUT_S3_URI")
    titan_image_model_id: str = Field(default="amazon.titan-image-generator-v2:0", alias="TITAN_IMAGE_MODEL_ID")
    nova_canvas_model_id: str = Field(default="us.amazon.nova-canvas-v1:0", alias="NOVA_CANVAS_MODEL_ID")
    
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
    grok_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("GROK_API_KEY", "GROQ_API_KEY"),
    )
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")
    llm_user_budget_usd: float = Field(default=20.0, alias="LLM_USER_BUDGET_USD")
    llm_global_budget_usd: float = Field(default=180.0, alias="LLM_GLOBAL_BUDGET_USD")
    llm_cost_per_1k_input_tokens_bedrock: float = Field(default=0.0008, alias="LLM_COST_PER_1K_INPUT_TOKENS_BEDROCK")
    llm_cost_per_1k_output_tokens_bedrock: float = Field(default=0.0032, alias="LLM_COST_PER_1K_OUTPUT_TOKENS_BEDROCK")
    llm_cost_per_1k_input_tokens_groq: float = Field(default=0.0006, alias="LLM_COST_PER_1K_INPUT_TOKENS_GROQ")
    llm_cost_per_1k_output_tokens_groq: float = Field(default=0.0018, alias="LLM_COST_PER_1K_OUTPUT_TOKENS_GROQ")

    # ===========================================
    # Storage (S3 → Firebase → Local)
    # ===========================================
    s3_bucket_name: Optional[str] = Field(default=None, alias="S3_BUCKET_NAME")
    frontend_bucket_name: Optional[str] = Field(default=None, alias="FRONTEND_BUCKET_NAME")
    frontend_website_url: Optional[str] = Field(default=None, alias="FRONTEND_WEBSITE_URL")
    firebase_storage_bucket: Optional[str] = Field(default=None, alias="FIREBASE_STORAGE_BUCKET")
    firebase_credentials_path: Optional[str] = Field(default=None, alias="FIREBASE_CREDENTIALS_PATH")
    storage_path: str = Field(default="./uploads", alias="STORAGE_PATH")
    storage_base_url: str = Field(default="/uploads", alias="STORAGE_BASE_URL")
    media_private_only: bool = Field(default=True, alias="MEDIA_PRIVATE_ONLY")

    # DynamoDB table names (pre-created resources)
    users_table_name: str = Field(default="ContentRoom-Users", alias="USERS_TABLE")
    content_table_name: str = Field(default="ContentRoom-Content", alias="CONTENT_TABLE")
    analysis_table_name: str = Field(default="ContentRoom-Analysis", alias="ANALYSIS_TABLE")
    ai_cache_table_name: str = Field(default="ContentRoom-AICache", alias="AI_CACHE_TABLE")
    moderation_cache_table_name: str = Field(default="ContentRoom-ModerationCache", alias="MODERATION_CACHE_TABLE")
    users_email_index_name: str = Field(default="EmailIndex", alias="USERS_EMAIL_INDEX")
    content_user_index_name: str = Field(default="UserIdIndex", alias="CONTENT_USER_INDEX")
    analysis_user_index_name: str = Field(default="UserIdIndex", alias="ANALYSIS_USER_INDEX")
    ai_cache_key_attr: str = Field(default="prompt_hash", alias="AI_CACHE_KEY_ATTR")
    moderation_cache_key_attr: str = Field(default="image_hash", alias="MODERATION_CACHE_KEY_ATTR")

    # Step Functions orchestration
    stepfunctions_preflight_arn: Optional[str] = Field(default=None, alias="STEPFUNCTIONS_PREFLIGHT_ARN")
    enable_stepfunctions_pipeline: bool = Field(default=True, alias="ENABLE_STEPFUNCTIONS_PIPELINE")

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
        default="https://moderation-service.example.com",
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
        default="https://example.com",
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
        """Check if AWS execution environment is available."""
        # IAM role credentials in Lambda do not require explicit key env vars.
        return bool(self.aws_region)
    
    @property
    def llm_provider(self) -> str:
        """
        Determine the best available LLM provider.
        Priority: AWS Bedrock (Nova family) → Groq
        """
        if self.use_aws_bedrock:
            return "aws_bedrock"
        if self.grok_api_key:
            return "grok"
        return "none"
    
    @property
    def vision_provider(self) -> str:
        """
        Determine the best available Vision provider.
        Priority: AWS Rekognition → simple fallback
        """
        if self.aws_configured and self.use_aws_rekognition:
            return "aws_rekognition"
        return "simple_fallback"
    
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
