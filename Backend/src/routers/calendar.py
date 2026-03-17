from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from tenacity import RetryError
from routers.auth import CurrentUser, get_current_user_optional
from services.calendar_service import CalendarService
from services.llm_service import AllProvidersFailedError
from services.dynamo_repositories import get_content_repo

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
    current_user: CurrentUser | None = Depends(get_current_user_optional)
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
            user_id=current_user.id if current_user else None,
        )
        
        # Save to history only if user is authenticated
        if current_user:
            get_content_repo().create_content(
                {
                    "user_id": current_user.id,
                    "record_type": "content",
                    "status": "generated",
                    "content_type": "content_calendar",
                    "original_text": (
                    f"Generated calendar for {request.month} {request.year}. "
                    f"Niche: {request.niche}. Goals: {request.goals}. "
                    f"Formats: {', '.join(cleaned_formats)}. Posts/month: {request.posts_per_month}"
                    ),
                    "summary": calendar_text,
                    "caption": f"Content Calendar: {request.month} {request.year}",
                    "moderation_status": "safe",
                    "created_at": datetime.utcnow().isoformat(),
                }
            )
        
        return CalendarResponse(calendar_markdown=calendar_text)
    except HTTPException:
        raise
    except RetryError as e:
        root_error = e.last_attempt.exception() if e.last_attempt else e
        if isinstance(root_error, AllProvidersFailedError):
            raise HTTPException(
                status_code=503,
                detail=(
                    "Calendar generation failed because no AI provider was available. "
                    "Check Bedrock model access/region or configure a valid GROQ/GROK API key."
                ),
            )
        raise HTTPException(status_code=500, detail=str(root_error))
    except AllProvidersFailedError:
        raise HTTPException(
            status_code=503,
            detail=(
                "Calendar generation failed because no AI provider was available. "
                "Check Bedrock model access/region or configure a valid GROQ/GROK API key."
            ),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

