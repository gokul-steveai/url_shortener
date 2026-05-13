from typing import Optional
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.redis_service import RedisService
from app.models.url import URL
from app.services.shortener import ShortenerService
from app.services.summarizer import SummarizerService
from fastapi.encoders import jsonable_encoder
from app.utils.pagination import build_paginated_response
from app.utils.timer import timer
import asyncio
import logging

logger = logging.getLogger(__name__)


class CRUDURL:

    def __init__(self, redis_client: RedisService):
        self.redis_client = redis_client

    async def get_by_short_id(self, db: AsyncSession, short_id: str) -> str | None:
        cached = await self.redis_client.get(f"url:{short_id}")
        if cached:
            logger.info("redirect.cache_hit short_id=%s", short_id)
            return cached.decode("utf-8")

        logger.info("redirect.cache_miss short_id=%s — querying DB", short_id)
        query = select(URL).where(URL.short_id == short_id)
        result = await db.execute(query)
        db_url = result.scalars().first()

        if db_url:
            await self.redis_client.set_json(
                f"url:{short_id}", db_url.original_url, ex=86400
            )
            logger.info("redirect.db_hit short_id=%s — cached for 24h", short_id)
            return db_url.original_url

        logger.warning("redirect.not_found short_id=%s", short_id)
        return None

    async def create(self, db: AsyncSession, origin_url: str, owner_id: int) -> URL:
        new_url = URL(original_url=origin_url, short_id="TEMP", owner_id=owner_id)
        db.add(new_url)
        await db.flush()

        short_id = ShortenerService.encode(new_url.id)
        new_url.short_id = short_id
        await db.commit()
        await db.refresh(new_url)
        logger.info(
            "url.created id=%s short_id=%s owner_id=%s", new_url.id, short_id, owner_id
        )

        await self.redis_client.bump_version()
        asyncio.create_task(self._fetch_and_store_summary(origin_url, short_id))
        return new_url

    async def _fetch_and_store_summary(self, origin_url: str, short_id: str) -> None:
        try:
            from app.api.deps import async_session_maker

            with timer() as t:
                summary = await SummarizerService.summarize(origin_url)
            if summary:
                async with async_session_maker() as session:
                    result = await session.execute(
                        select(URL).where(URL.short_id == short_id)
                    )
                    db_url = result.scalars().first()
                    if db_url:
                        db_url.summary = summary
                        await session.commit()
                        logger.info(
                            "summary.stored short_id=%s elapsed_ms=%s",
                            short_id,
                            t.elapsed,
                        )
            else:
                logger.warning(
                    "summary.empty short_id=%s elapsed_ms=%s", short_id, t.elapsed
                )
        except Exception as e:
            logger.error(
                "summary.failed short_id=%s error=%s", short_id, e, exc_info=True
            )

    async def get_summary(
        self, db: AsyncSession, short_id: str, owner_id: int
    ) -> Optional[str]:
        query = select(URL).where(URL.short_id == short_id, URL.owner_id == owner_id)
        result = await db.execute(query)
        db_url = result.scalars().first()

        if not db_url:
            logger.warning(
                "summary.not_found short_id=%s owner_id=%s", short_id, owner_id
            )
            return None

        if db_url.summary:
            logger.info("summary.cache_hit short_id=%s", short_id)
            return db_url.summary

        logger.info("summary.on_demand short_id=%s", short_id)
        with timer() as t:
            summary = await SummarizerService.summarize(db_url.original_url)
        if summary:
            db_url.summary = summary
            await db.commit()
            logger.info(
                "summary.fetched short_id=%s elapsed_ms=%s", short_id, t.elapsed
            )
            return summary

        logger.warning(
            "summary.unavailable short_id=%s elapsed_ms=%s", short_id, t.elapsed
        )
        return None

    async def get_all(
        self, db: AsyncSession, page: int = 1, limit: int = 20, owner_id: int = None
    ) -> list[dict]:
        count_q = select(func.count(URL.id)).where(URL.owner_id == owner_id)
        total = (await db.execute(count_q)).scalar()

        cached = await self.redis_client.get_paginated_links(
            page, limit, owner_id=owner_id
        )
        if cached:
            return build_paginated_response(cached, total, page, limit)

        logger.info(
            "db.query.links page=%s limit=%s owner_id=%s", page, limit, owner_id
        )
        query = (
            select(URL)
            .where(URL.owner_id == owner_id)
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await db.execute(query)
        links = result.scalars().all()
        await self.redis_client.set_paginated_links(
            page, limit, links, len(links), owner_id=owner_id
        )
        logger.info("db.query.links.done count=%s total=%s", len(links), total)
        return build_paginated_response(jsonable_encoder(links), total, page, limit)

    async def get_and_increment_clicks(
        self, db: AsyncSession, short_id: str
    ) -> Optional[str]:
        query = (
            update(URL)
            .where(URL.short_id == short_id)
            .values(clicks=URL.clicks + 1)
            .returning(URL.original_url)
        )
        result = await db.execute(query)
        await db.commit()
        target_url = result.scalar_one_or_none()

        if target_url:
            logger.info("click.recorded short_id=%s", short_id)
            await self.redis_client.invalidate(f"link:obj:{short_id}")
            await self.redis_client.bump_version()
        else:
            logger.warning("click.not_found short_id=%s", short_id)

        return target_url

    async def delete(self, db: AsyncSession, id: int, owner_id: int):
        query = delete(URL).where(URL.id == id, URL.owner_id == owner_id)
        result = await db.execute(query)
        await db.commit()

        if result.rowcount > 0:
            logger.info("url.deleted id=%s owner_id=%s", id, owner_id)
            await self.redis_client.invalidate(f"link:object:{id}")
            await self.redis_client.bump_version()
            return True

        logger.warning("url.delete_not_found id=%s owner_id=%s", id, owner_id)
        return False
