from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models.user import User
from models.content import Content, ModerationStatus
from routers.auth import get_current_user_optional
from services.calendar_service import CalendarService

router = APIRouter(tags=["Content Calendar"])

class CalendarRequest(BaseModel):
    month: str
    year: int
    niche: str
    goals: str
    content_formats: list[str]
    posts_per_month: int

class CalendarResponse(BaseModel):
    calendar_markdown: str

@router.post("/generate", response_model=CalendarResponse)
async def generate_calendar(
    request: CalendarRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional)
):
    """
    Generates a monthly content calendar based on niche and Indian festivals.
    Authentication is optional - history is only saved for logged-in users.
    """
    service = CalendarService()
    try:
        # Validate month
        valid_months = ["January", "February", "March", "April", "May", "June", 
                        "July", "August", "September", "October", "November", "December"]
        if request.month not in valid_months:
            raise HTTPException(status_code=400, detail="Invalid month. Use full English name (e.g. January).")
            
        allowed_formats = {"reel", "video", "live", "blog", "story"}
        cleaned_formats = [fmt.strip().lower() for fmt in request.content_formats if fmt and fmt.strip()]
        if not cleaned_formats:
            raise HTTPException(status_code=400, detail="Please select at least one content format.")
        invalid_formats = [fmt for fmt in cleaned_formats if fmt not in allowed_formats]
        if invalid_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid content formats: {', '.join(invalid_formats)}. Allowed: reel, video, live, blog, story."
            )

        if request.posts_per_month < 1 or request.posts_per_month > 120:
            raise HTTPException(status_code=400, detail="posts_per_month must be between 1 and 120.")

        calendar_text = await service.generate_calendar(
            request.month,
            request.year,
            request.niche,
            request.goals,
            cleaned_formats,
            request.posts_per_month,
        )
        
        # Save to history only if user is authenticated
        if current_user:
            content_item = Content(
                user_id=current_user.id,
                content_type="content_calendar",
                original_text=(
                    f"Generated calendar for {request.month} {request.year}. "
                    f"Niche: {request.niche}. Goals: {request.goals}. "
                    f"Formats: {', '.join(cleaned_formats)}. Posts/month: {request.posts_per_month}"
                ),
                summary=calendar_text,
                caption=f"Content Calendar: {request.month} {request.year}",
                moderation_status=ModerationStatus.SAFE.value,
                created_at=datetime.utcnow()
            )
            db.add(content_item)
            await db.commit()
            await db.refresh(content_item)
        
        return CalendarResponse(calendar_markdown=calendar_text)
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

