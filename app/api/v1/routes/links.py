import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_redis_client, get_current_user
from app.crud.url import CRUDURL
from app.models.user import User
from app.schemas.url import URLCreate, URLResponse
from app.services.redis_service import RedisService
from app.core.config import settings
from app.utils.timer import timer

router = APIRouter(tags=["Links"])
logger = logging.getLogger(__name__)


@router.post(
    "/shorten",
    response_model=URLResponse,
    summary="Create a short URL",
    response_description="The created short URL with optional AI summary",
    responses={401: {"description": "Not authenticated"}},
)
async def create_short_url(
    payload: URLCreate,
    db: AsyncSession = Depends(get_db),
    redis: RedisService = Depends(get_redis_client),
    current_user: User = Depends(get_current_user),
):
    """
    Shorten a long URL. A Base-62 short ID is derived from the DB primary key.

    An AI summary of the destination page is generated asynchronously in the
    background via Groq LLaMA 3.3 70B and stored once ready.
    """
    with timer() as t:
        result = await CRUDURL(redis).create(
            db, str(payload.target_url), owner_id=current_user.id
        )
    logger.info(
        "POST /shorten short_id=%s user_id=%s elapsed_ms=%s",
        result.short_id,
        current_user.id,
        t.elapsed,
    )
    return URLResponse(
        target_url=payload.target_url,
        short_url=f"{settings.API_URL}/{result.short_id}",
        summary=result.summary,
        expires_at=result.expires_at,
    )


@router.get(
    "/links",
    summary="List all your short links",
    response_description="Paginated list of links owned by the current user",
    responses={401: {"description": "Not authenticated"}},
)
async def get_all_links(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    redis: RedisService = Depends(get_redis_client),
    current_user: User = Depends(get_current_user),
):
    """Returns a paginated list of all short links belonging to the authenticated user."""
    with timer() as t:
        response = await CRUDURL(redis).get_all(
            db, page, limit, owner_id=current_user.id
        )
    logger.info(
        "GET /links page=%s limit=%s total=%s user_id=%s elapsed_ms=%s",
        page,
        limit,
        response.get("total"),
        current_user.id,
        t.elapsed,
    )
    return response


@router.get(
    "/links/{short_id}/summary",
    summary="Get AI summary for a link",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Link not found"},
    },
)
async def get_link_summary(
    short_id: str,
    db: AsyncSession = Depends(get_db),
    redis: RedisService = Depends(get_redis_client),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the AI-generated summary for a short link.

    If the background task hasn't completed yet, generates it on-demand synchronously.
    """
    with timer() as t:
        summary = await CRUDURL(redis).get_summary(
            db, short_id, owner_id=current_user.id
        )
    logger.info(
        "GET /links/%s/summary found=%s user_id=%s elapsed_ms=%s",
        short_id,
        bool(summary),
        current_user.id,
        t.elapsed,
    )
    return {"short_id": short_id, "summary": summary}


@router.delete(
    "/links/{id}",
    summary="Delete a short link",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Link not found or not owned by you"},
    },
)
async def delete_url(
    id: int,
    db: AsyncSession = Depends(get_db),
    redis: RedisService = Depends(get_redis_client),
    current_user: User = Depends(get_current_user),
):
    """Permanently deletes a short link. Only the owner can delete their own links."""
    with timer() as t:
        result = await CRUDURL(redis).delete(db, id, owner_id=current_user.id)

    if not result:
        logger.warning(
            "DELETE /links/%s not_found user_id=%s elapsed_ms=%s",
            id,
            current_user.id,
            t.elapsed,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="URL not found"
        )

    logger.info(
        "DELETE /links/%s success user_id=%s elapsed_ms=%s",
        id,
        current_user.id,
        t.elapsed,
    )
    return {"message": "URL deleted successfully"}
