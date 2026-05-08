from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.url import URLCreate, URLResponse
from app.crud.url import CRUDURL
from app.api.deps import get_db, get_redis_client
import redis.asyncio as redis
from app.core.config import settings
from app.models.url import URL

router = APIRouter()


@router.post("/shorten", response_model=URLResponse)
async def create_short_url(
    payload: URLCreate,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """
    Takes a long URL and returns a shortened version.
    """
    crud = CRUDURL(redis_client)
    result = await crud.create(db, str(payload.target_url))

    if result:
        # Return the existing short URL
        return URLResponse(
            target_url=payload.target_url,
            short_url=f"{settings.API_URL}/{result.short_id}",
            expires_at=result.expires_at,
        )


@router.get("/links")
async def get_all_links(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    # Query all links from the database
    crud = CRUDURL(redis_client)
    response = await crud.get_all(db, page, limit)

    # Return as a list of dictionaries
    return response


@router.get("/{short_id}")
async def redirect_url(
    short_id: str,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """
    Redirects to the original URL from a short ID.
    """
    crud = CRUDURL(redis_client)

    # Increment clicks and get the URL
    original_url = await crud.get_and_increment_clicks(db, short_id)

    if not original_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short URL not found",
        )

    # Redirect to the original URL
    return RedirectResponse(
        url=original_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT
    )
