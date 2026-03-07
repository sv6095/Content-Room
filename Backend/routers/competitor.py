from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models.user import User
from models.content import Content, ContentType, ModerationStatus
from routers.auth import get_current_user_optional
from services.competitor_service import CompetitorService

router = APIRouter(tags=["Competitor"])

class CompetitorRequest(BaseModel):
    url: str
    niche: str

class CompetitorResponse(BaseModel):
    analysis: str
    url_found: bool
    source_note: str | None = None
    analysis_structured: dict[str, Any] | None = None

@router.post("/analyze", response_model=CompetitorResponse)
async def analyze_competitor_gaps(
    request: CompetitorRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional)
):
    """
    Analyzes a given competitor's URL (social profile, blog) and returns a gap analysis.
    Uses basic web scraping + LLM to identify opportunities.
    Authentication is optional - history is only saved for logged-in users.
    """
    service = CompetitorService()
    try:
        analysis_payload = await service.analyze_competitor_gaps_payload(request.url, request.niche)
        analysis_result = analysis_payload["full_analysis"]
        
        # Save to history only if user is authenticated
        if current_user:
            content_item = Content(
                user_id=current_user.id,
                content_type="competitor_analysis",
                original_text=f"Analyzed competitor: {request.url} in niche: {request.niche}",
                summary=analysis_result,
                caption=f"Competitor Analysis: {request.url}",
                moderation_status=ModerationStatus.SAFE.value, # Analysis is safe by default
                created_at=datetime.utcnow()
            )
            db.add(content_item)
            await db.commit()
            await db.refresh(content_item)
        
        return CompetitorResponse(
            analysis=analysis_result,
            url_found=True,
            source_note=analysis_payload.get("source_note"),
            analysis_structured=analysis_payload.get("analysis_structured"),
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

