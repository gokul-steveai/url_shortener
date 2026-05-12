import logging

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.url import URL
from app.models.user import User
from app.utils.timer import timer

router = APIRouter(tags=["System Endpoints"])
logger = logging.getLogger(__name__)


@router.get(
    "/stats",
    summary="Get aggregate stats for current user",
    responses={401: {"description": "Not authenticated"}},
)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns total link count and total click count for the authenticated user."""
    with timer() as t:
        result = await db.execute(
            select(func.count(URL.id), func.coalesce(func.sum(URL.clicks), 0)).where(
                URL.owner_id == current_user.id
            )
        )
    total_links, total_clicks = result.one()
    logger.info(
        "GET /stats total_links=%s total_clicks=%s user_id=%s elapsed_ms=%s",
        total_links,
        total_clicks,
        current_user.id,
        t.elapsed,
    )
    return {"total_links": total_links, "total_clicks": int(total_clicks)}


@router.get("/health", summary="Health check")
async def health_check():
    """Returns service status. Used by load balancers."""
    return {"status": "healthy"}
