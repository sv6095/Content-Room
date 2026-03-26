from datetime import datetime
import json
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from tenacity import RetryError
from routers.auth import CurrentUser, get_current_user_optional
from services.calendar_service import CalendarService
from services.llm_service import AllProvidersFailedError
from services.dynamo_repositories import get_content_repo, get_ai_cache_repo

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


class CachedCalendarItem(BaseModel):
    content_id: str
    month: str | None = None
    year: int | None = None
    niche: str | None = None
    goals: str | None = None
    content_formats: list[str] = []
    posts_per_month: int | None = None
    calendar_markdown: str
    created_at: str


class CachedCalendarListResponse(BaseModel):
    items: list[CachedCalendarItem]


def _calendar_exact_cache_key(
    *,
    user_id: str | None,
    month: str,
    year: int,
    niche: str,
    goals: str,
    content_formats: list[str],
    posts_per_month: int,
) -> str:
    return json.dumps(
        {
            "type": "calendar_generation",
            "user_id": user_id or "anonymous",
            "month": month,
            "year": year,
            "niche": niche.strip().lower(),
            "goals": goals.strip(),
            "content_formats": sorted(content_formats),
            "posts_per_month": posts_per_month,
        },
        sort_keys=True,
        ensure_ascii=False,
    )


def _calendar_view_cache_key(
    *,
    user_id: str,
    month: str,
    year: int,
    niche: str,
) -> str:
    return json.dumps(
        {
            "type": "calendar_view",
            "user_id": user_id,
            "month": month,
            "year": year,
            "niche": niche.strip().lower(),
        },
        sort_keys=True,
        ensure_ascii=False,
    )

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

        user_id = current_user.id if current_user else None
        exact_cache_key = _calendar_exact_cache_key(
            user_id=user_id,
            month=request.month,
            year=request.year,
            niche=request.niche,
            goals=request.goals,
            content_formats=cleaned_formats,
            posts_per_month=request.posts_per_month,
        )
        cache_repo = get_ai_cache_repo()
        cache_hit = False
        calendar_text = ""
        cached_item = cache_repo.get(exact_cache_key, "calendar_generation")
        if cached_item and cached_item.get("response"):
            try:
                cached_payload = json.loads(cached_item["response"])
                if isinstance(cached_payload, dict) and isinstance(cached_payload.get("calendar_markdown"), str):
                    calendar_text = cached_payload["calendar_markdown"]
                    cache_hit = True
            except Exception:
                cache_hit = False

        if not cache_hit:
            calendar_text = await service.generate_calendar(
                request.month,
                request.year,
                request.niche,
                request.goals,
                cleaned_formats,
                request.posts_per_month,
                user_id=user_id,
            )
            cache_repo.put(
                exact_cache_key,
                "calendar_generation",
                json.dumps(
                    {
                        "calendar_markdown": calendar_text,
                        "month": request.month,
                        "year": request.year,
                        "niche": request.niche,
                        "goals": request.goals,
                        "content_formats": cleaned_formats,
                        "posts_per_month": request.posts_per_month,
                        "created_at": datetime.utcnow().isoformat(),
                    },
                    ensure_ascii=False,
                ),
                ttl_days=30,
            )
        
        # Always save to history when authenticated so the calendar is mapped to the user,
        # even if we served the content from AI cache.
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
                    "calendar_month": request.month,
                    "calendar_year": request.year,
                    "calendar_niche": request.niche,
                    "calendar_goals": request.goals,
                    "calendar_formats": cleaned_formats,
                    "calendar_posts_per_month": request.posts_per_month,
                    "cache_type": "calendar_generation",
                    "moderation_status": "safe",
                    "created_at": datetime.utcnow().isoformat(),
                }
            )
        # Maintain quick "Your Calendars" fallback cache by month/year/niche.
        if current_user:
            view_cache_key = _calendar_view_cache_key(
                user_id=current_user.id,
                month=request.month,
                year=request.year,
                niche=request.niche,
            )
            cache_repo.put(
                view_cache_key,
                "calendar_view",
                json.dumps(
                    {
                        "calendar_markdown": calendar_text,
                        "month": request.month,
                        "year": request.year,
                        "niche": request.niche,
                        "goals": request.goals,
                        "content_formats": cleaned_formats,
                        "posts_per_month": request.posts_per_month,
                        "created_at": datetime.utcnow().isoformat(),
                    },
                    ensure_ascii=False,
                ),
                ttl_days=30,
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


@router.get("/cached", response_model=CachedCalendarListResponse)
async def get_cached_calendars(
    month: str | None = Query(default=None),
    year: int | None = Query(default=None),
    niche: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """
    Return cached/generated calendars for the authenticated user.
    Falls back to empty list when unauthenticated.
    """
    if not current_user:
        return CachedCalendarListResponse(items=[])

    content_items = get_content_repo().list_for_user(current_user.id, record_type="content")
    month_norm = (month or "").strip().lower()
    niche_norm = (niche or "").strip().lower()

    filtered: list[CachedCalendarItem] = []
    for item in content_items:
        if item.get("content_type") != "content_calendar":
            continue
        markdown = (item.get("summary") or "").strip()
        if not markdown:
            continue

        item_month = item.get("calendar_month")
        item_year = item.get("calendar_year")
        item_niche = item.get("calendar_niche")

        if month_norm and str(item_month or "").strip().lower() != month_norm:
            continue
        if year is not None:
            try:
                if int(item_year or 0) != int(year):
                    continue
            except Exception:
                continue
        if niche_norm and niche_norm not in str(item_niche or "").strip().lower():
            continue

        formats = item.get("calendar_formats")
        safe_formats = formats if isinstance(formats, list) else []
        created_at = item.get("created_at") or ""
        parsed_year: int | None = None
        try:
            parsed_year = int(item_year) if item_year is not None else None
        except Exception:
            parsed_year = None
        parsed_posts_per_month: int | None = None
        try:
            parsed_posts_per_month = (
                int(item.get("calendar_posts_per_month"))
                if item.get("calendar_posts_per_month") is not None
                else None
            )
        except Exception:
            parsed_posts_per_month = None

        filtered.append(
            CachedCalendarItem(
                content_id=item.get("content_id", ""),
                month=item_month,
                year=parsed_year,
                niche=item_niche,
                goals=item.get("calendar_goals"),
                content_formats=[str(fmt) for fmt in safe_formats],
                posts_per_month=parsed_posts_per_month,
                calendar_markdown=markdown,
                created_at=created_at,
            )
        )

    filtered.sort(key=lambda x: x.created_at, reverse=True)
    if filtered:
        return CachedCalendarListResponse(items=filtered[:limit])

    # Fallback to AI cache for exact month/year/niche when no history item exists.
    if month and year is not None and niche:
        try:
            view_cache_key = _calendar_view_cache_key(
                user_id=current_user.id,
                month=month,
                year=year,
                niche=niche,
            )
            cached_item = get_ai_cache_repo().get(view_cache_key, "calendar_view")
            if cached_item and cached_item.get("response"):
                payload = json.loads(cached_item["response"])
                markdown = str(payload.get("calendar_markdown", "")).strip()
                if markdown:
                    return CachedCalendarListResponse(
                        items=[
                            CachedCalendarItem(
                                content_id=f"cache_{month}_{year}_{current_user.id}",
                                month=payload.get("month") or month,
                                year=int(payload.get("year")) if payload.get("year") is not None else year,
                                niche=payload.get("niche") or niche,
                                goals=payload.get("goals"),
                                content_formats=[
                                    str(fmt) for fmt in (payload.get("content_formats") or []) if fmt
                                ],
                                posts_per_month=(
                                    int(payload.get("posts_per_month"))
                                    if payload.get("posts_per_month") is not None
                                    else None
                                ),
                                calendar_markdown=markdown,
                                created_at=payload.get("created_at") or datetime.utcnow().isoformat(),
                            )
                        ]
                    )
        except Exception:
            pass

    return CachedCalendarListResponse(items=[])

