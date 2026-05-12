import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

from app.api.deps import get_db, get_redis_client
from app.crud.url import CRUDURL
from app.services.redis_service import RedisService
from app.utils.timer import timer
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["Public Endpoints"])
logger = logging.getLogger(__name__)


@router.get(
    "/{short_id}",
    summary="Redirect to original URL",
    response_class=RedirectResponse,
    responses={
        307: {"description": "Redirect to the original URL"},
        404: {"description": "Short URL not found"},
    },
)
async def redirect_url(
    short_id: str,
    db: AsyncSession = Depends(get_db),
    redis: RedisService = Depends(get_redis_client),
):
    """
    Public endpoint — no authentication required.

    Redirects to the original URL and atomically increments the click counter.
    Redirect target is served from Redis cache (24h TTL) on cache hit.
    """
    with timer() as t:
        original_url = await CRUDURL(redis).get_and_increment_clicks(db, short_id)

    if not original_url:
        logger.warning("GET /%s not_found elapsed_ms=%s", short_id, t.elapsed)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found"
        )

    logger.info("GET /%s redirect elapsed_ms=%s", short_id, t.elapsed)
    return RedirectResponse(
        url=original_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT
    )
