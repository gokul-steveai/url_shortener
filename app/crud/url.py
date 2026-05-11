from typing import Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.redis_service import RedisService
from app.models.url import URL
from app.services.shortener import ShortenerService
from fastapi.encoders import jsonable_encoder
from app.utils.pagination import build_paginated_response


class CRUDURL:

    def __init__(self, redis_client: RedisService):
        self.redis_client = redis_client

    async def get_by_short_id(self, db: AsyncSession, short_id: str) -> str | None:
        cached = await self.redis_client.get(f"url:{short_id}")

        if cached:
            # Return the value from Redis
            return cached.decode("utf-8")

        query = select(URL).where(URL.short_id == short_id)
        result = await db.execute(query)

        db_url = result.scalars().first()

        if db_url:
            # Set the value in Redis with an expiration of 24 hours
            await self.redis_client.set_json(
                f"url:{short_id}", db_url.original_url, ex=86400
            )
            return db_url.original_url

        return None

    async def create(self, db: AsyncSession, origin_url: str) -> URL:
        # Create a new URL in the database to get the new id
        new_url = URL(original_url=origin_url, short_id="TEMP")
        db.add(new_url)

        await db.flush()

        # Encode the new id and update the short_id
        short_id = ShortenerService.encode(new_url.id)
        new_url.short_id = short_id

        await db.commit()
        await db.refresh(new_url)

        # Invalidate the cache for all links
        await self.redis_client.bump_version()

        return new_url

    async def get_all(
        self, db: AsyncSession, page: int = 1, limit: int = 20
    ) -> list[dict]:
        total = select(func.count(URL.id))
        total = await db.execute(total)
        total = total.scalar()

        # Check if the links are cached
        cached = await self.redis_client.get_paginated_links(page, limit)

        if cached:
            return build_paginated_response(
                jsonable_encoder(cached), total, page, limit
            )

        query = select(URL).offset((page - 1) * limit).limit(limit)
        result = await db.execute(query)
        links = result.scalars().all()

        # Cache the links for 1 hour
        await self.redis_client.set_paginated_links(page, limit, links, len(links))

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
            await self.redis_client.invalidate(f"link:obj:{short_id}")
            await self.redis_client.bump_version()

        return target_url

    async def delete(self, db: AsyncSession, id: int):
        query = delete(URL).where(URL.id == id)
        result = await db.execute(query)
        await db.commit()

        if result.rowcount > 0:
            # 3. Clean up Redis
            await self.redis_client.invalidate(
                f"link:object:{id}"
            )  # Matches your RedisService key pattern
            await self.redis_client.bump_version()  # Clear paginated lists
            return True

        return False
