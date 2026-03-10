"""
Content Room Backend - Main Application Entry Point

AWS-native AI Content Workflow Engine with resilient fallback architecture.
All features enabled - no authentication required for AI services.
"""
import os
# Disable telemetry and set HuggingFace to offline to fix JSONDecodeErrors during conversion
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
# Uncomment this if you already downloaded the models. 
# It's commented out so Render can download the Detoxify toxicity model on boot.
# os.environ["HF_HUB_OFFLINE"] = "1"

import logging
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from pathlib import Path
import warnings


warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from utils.logging import setup_logging
from middleware.rate_limiter import RateLimitMiddleware, RateLimitConfig


# Setup structured logging
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info("=" * 60)
    logger.info("Content Room Backend Starting...")
    logger.info("=" * 60)
    logger.info(f"AWS Configured: {settings.aws_configured}")
    logger.info(f"LLM Provider: {settings.llm_provider}")
    logger.info(f"Debug Mode: {settings.debug}")
    logger.info("=" * 60)
    
    logger.info("DynamoDB repositories are used for persistence")
    
    # Start background scheduler
    if settings.scheduler_enabled:
        from services.task_scheduler import start_scheduler
        scheduler = start_scheduler()
        logger.info("Background scheduler started")
    
    yield
    
    # Shutdown
    if settings.scheduler_enabled:
        from services.task_scheduler import stop_scheduler
        stop_scheduler()
        logger.info("Background scheduler stopped")
    
    logger.info("Content Room Backend Shutting Down...")


# Create FastAPI application
app = FastAPI(
    title="Content Room API",
    description="AI-powered Content Workflow Engine with AWS + Free Fallback Architecture.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# CORS middleware must be configured before routers are included.
origins = list(
    dict.fromkeys(
        [
            "http://content-room-frontend-125903111660.s3-website.ap-south-1.amazonaws.com",
        ]
        + settings.cors_origins_list
    )
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting Middleware
rate_limit_config = RateLimitConfig(
    requests_per_minute=getattr(settings, 'rate_limit_per_minute', 60),
    burst_size=getattr(settings, 'rate_limit_burst', 10),
)
app.add_middleware(RateLimitMiddleware, config=rate_limit_config)


# Serve uploaded files statically
uploads_path = Path(settings.storage_path)
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")


# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error("Unhandled exception request_id=%s error=%s", request_id, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "request_id": request_id,
            "message": str(exc) if settings.debug else "An unexpected error occurred.",
        },
    )


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response


# Health Check
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "aws_configured": settings.aws_configured,
        "llm_provider": settings.llm_provider,
        "dynamodb_enabled": settings.use_aws_dynamodb,
        "stepfunctions_enabled": settings.enable_stepfunctions_pipeline,
        "scheduler_enabled": settings.scheduler_enabled,
    }


# ===========================================
# ALL ROUTERS ENABLED
# ===========================================

# 1. Auth Router
from routers import auth
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])

# 2. Content Creation Router
from routers import creation
app.include_router(creation.router, prefix="/api/v1/create", tags=["Content Creation"])

# 3. Moderation Router
from routers import moderation
app.include_router(moderation.router, prefix="/api/v1/moderate", tags=["Moderation"])

# 4. Translation Router
from routers import translation
app.include_router(translation.router, prefix="/api/v1/translate", tags=["Translation"])

# 5. Scheduler Router
from routers import scheduler
app.include_router(scheduler.router, prefix="/api/v1/schedule", tags=["Scheduling"])

# 6. Analytics Router
from routers import analytics
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])

# 7. Media Router (NEW)
from routers import media
app.include_router(media.router, prefix="/api/v1/media", tags=["Media"])


# 8. Content Router (My Content pipeline)
from routers import content
app.include_router(content.router, prefix="/api/v1/content", tags=["Content"])

# 9. History Router
from routers import history
app.include_router(history.router, prefix="/api/v1/history", tags=["History"])

# 10. Competitor Analysis Router (NEW)
from routers import competitor
app.include_router(competitor.router, prefix="/api/v1/competitor", tags=["Competitor"])

# 11. Content Calendar Router (NEW)
from routers import calendar
app.include_router(calendar.router, prefix="/api/v1/calendar", tags=["Content Calendar"])

# 12. Intelligence Hub Router (Cultural Emotion, Risk-Reach, DNA, Anti-Cancel, Mental Health, Asset Explosion, Shadowban)
from routers import intelligence
app.include_router(intelligence.router, prefix="/api/v1/intel", tags=["Intelligence Hub"])

# 13. Novel Hub Router (Signal Intelligence, Trend RAG, Multimodal, Auto-Publish, Burnout)
from routers import novel
app.include_router(novel.router, prefix="/api/v1/novel", tags=["Novel Hub"])

# 14. Pre-Flight Pipeline Router (Unified multi-model analysis for Scheduler)
from routers import pipeline
app.include_router(pipeline.router, prefix="/api/v1/pipeline", tags=["Pre-Flight Pipeline"])


@app.get("/", tags=["System"])
async def root():
    return {"message": "Content Room API", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
