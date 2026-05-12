import time
import logging

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
logger = logging.getLogger(__name__)


@router.post("/shorten", response_model=URLResponse)
async def create_short_url(
    payload: URLCreate,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    t0 = time.perf_counter()
    crud = CRUDURL(redis_client)
    result = await crud.create(db, str(payload.target_url))
    elapsed = round((time.perf_counter() - t0) * 1000)
    logger.info("POST /shorten short_id=%s elapsed_ms=%s", result.short_id, elapsed)
    return URLResponse(
        target_url=payload.target_url,
        short_url=f"{settings.API_URL}/{result.short_id}",
        summary=result.summary,
        expires_at=result.expires_at,
    )


@router.get("/links")
async def get_all_links(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    t0 = time.perf_counter()
    crud = CRUDURL(redis_client)
    response = await crud.get_all(db, page, limit)
    elapsed = round((time.perf_counter() - t0) * 1000)
    logger.info("GET /links page=%s limit=%s total=%s elapsed_ms=%s", page, limit, response.get("total"), elapsed)
    return response


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Live aggregate stats for the dashboard."""
    t0 = time.perf_counter()
    result = await db.execute(
        select(func.count(URL.id), func.coalesce(func.sum(URL.clicks), 0))
    )
    total_links, total_clicks = result.one()
    elapsed = round((time.perf_counter() - t0) * 1000)
    logger.info("GET /stats total_links=%s total_clicks=%s elapsed_ms=%s", total_links, total_clicks, elapsed)
    return {"total_links": total_links, "total_clicks": int(total_clicks)}


@router.get("/links/{short_id}/summary")
async def get_link_summary(
    short_id: str,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    t0 = time.perf_counter()
    crud = CRUDURL(redis_client)
    summary = await crud.get_summary(db, short_id)
    elapsed = round((time.perf_counter() - t0) * 1000)
    logger.info("GET /links/%s/summary found=%s elapsed_ms=%s", short_id, bool(summary), elapsed)
    return {"short_id": short_id, "summary": summary}


@router.get("/{short_id}")
async def redirect_url(
    short_id: str,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    t0 = time.perf_counter()
    crud = CRUDURL(redis_client)
    original_url = await crud.get_and_increment_clicks(db, short_id)
    elapsed = round((time.perf_counter() - t0) * 1000)

    if not original_url:
        logger.warning("GET /%s not_found elapsed_ms=%s", short_id, elapsed)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found")

    logger.info("GET /%s redirect elapsed_ms=%s", short_id, elapsed)
    return RedirectResponse(url=original_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.delete("/links/{id}")
async def delete_url(
    id: int,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    t0 = time.perf_counter()
    crud = CRUDURL(redis_client)
    result = await crud.delete(db, id)
    elapsed = round((time.perf_counter() - t0) * 1000)

    if not result:
        logger.warning("DELETE /links/%s not_found elapsed_ms=%s", id, elapsed)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")

    logger.info("DELETE /links/%s success elapsed_ms=%s", id, elapsed)
    return {"message": "URL deleted successfully", "status_code": status.HTTP_200_OK}