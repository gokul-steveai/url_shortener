from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.url import URLCreate, URLResponse
from app.crud.url import CRUDURL
from app.core.database import get_db
import redis.asyncio as redis
from app.core.config import settings

router = APIRouter()


# Dependency to get redis client
async def get_redis_client():
    client = redis.from_url("redis://localhost:6379/0")

    try:
        yield client
    finally:
        await client.close()


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
            short_url=f"{settings.BASE_URL}/{result.short_id}",
            expires_at=result.expires_at,
        )


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

    # Try to get the URL from Redis or Database
    original_url = await crud.get_by_short_id(db, short_id)

    if not original_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short URL not found",
        )

    # Redirect to the original URL
    return RedirectResponse(
        url=original_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT
    )
