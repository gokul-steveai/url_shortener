import asyncio
import orjson
from typing import Any, Optional

from fastapi.encoders import jsonable_encoder

from redis.asyncio.client import Redis

from logging import getLogger

logger = getLogger(__name__)


class RedisService:
    DEFAULT_OBJECT_TTL = 3600
    DEFAULT_INDEX_TTL = 600
    VERSION_KEY = "links:version"

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def get_json(self, key: str) -> Optional[Any]:
        """
        Fetch and deserialize JSON data from Redis.
        Auto-cleans corrupted cache entries.
        """
        data = await self.redis.get(key)

        if data is None:
            logger.debug(f"Cache miss for key: {key}")
            return None

        try:
            logger.debug(f"Cache hit for key: {key}")
            return orjson.loads(data)
        except orjson.JSONDecodeError:
            logger.debug(f"Corrupted cache entry for key: {key}")
            await self.redis.delete(key)
            return None

    async def set_json(
        self,
        key: str,
        value: Any,
        expire: int = DEFAULT_OBJECT_TTL,
    ):
        """
        Serialize and store JSON data in Redis.
        """
        serialized = orjson.dumps(jsonable_encoder(value))

        # Set the key with expiration
        await self.redis.set(
            key,
            serialized,
            ex=expire,
        )

    async def invalidate(self, key: str):
        """
        Delete specific cache key.
        """
        await self.redis.delete(key)

    # =========================================================
    # Versioning
    # =========================================================

    async def get_cache_version(self) -> int:
        """
        Get current pagination cache version.
        """
        version = await self.redis.get(self.VERSION_KEY)

        if version is None:
            # Initialize cache version
            await self.redis.set(self.VERSION_KEY, 1)
            return 1

        return int(version)

    async def bump_cache_version(self):
        """
        Invalidate all paginated caches instantly.
        """
        await self.redis.incr(self.VERSION_KEY)

    # =========================================================
    # Distributed Lock (Cache Stampede Protection)
    # =========================================================

    async def acquire_lock(
        self,
        lock_key: str,
        expire: int = 10,
    ) -> bool:
        """
        Acquire distributed lock.
        """
        return await self.redis.set(
            lock_key,
            "1",
            ex=expire,
            nx=True,
        )

    async def release_lock(self, lock_key: str):
        """
        Release distributed lock.
        """
        await self.redis.delete(lock_key)

    # =========================================================
    # Pagination Cache
    # =========================================================

    async def get_paginated_links(
        self,
        page: int,
        limit: int,
    ) -> Optional[dict]:
        """
        Fetch paginated links from cache.

        Returns:
        {
            "links": [...],
            "total": 100
        }
        """

        version = await self.get_cache_version()

        index_key = f"links:v{version}:page:{page}:limit:{limit}"

        cached_index = await self.get_json(index_key)

        if cached_index is None:
            return None

        if "ids" not in cached_index:
            return None

        link_ids = cached_index["ids"]

        if not link_ids:
            return {
                "links": [],
                "total": cached_index.get("total", 0),
            }

        object_keys = [f"link:object:{link_id}" for link_id in link_ids]

        raw_objects = await self.redis.mget(*object_keys)

        # Partial cache miss detection
        if len(raw_objects) != len(link_ids) or any(obj is None for obj in raw_objects):
            return None

        try:
            links = [orjson.loads(obj) for obj in raw_objects]
        except orjson.JSONDecodeError:
            return None

        return {
            "links": links,
            "total": cached_index["total"],
        }

    async def set_paginated_links(
        self,
        page: int,
        limit: int,
        links: list,
        total: int,
    ):
        """
        Store paginated links efficiently using pipeline.
        """

        version = await self.get_cache_version()

        index_key = f"links:v{version}:page:{page}:limit:{limit}"

        pipe = self.redis.pipeline()

        link_ids = []

        for link in links:
            link_id = link.id if hasattr(link, "id") else link["id"]

            link_ids.append(link_id)

            object_key = f"link:object:{link_id}"

            pipe.set(
                object_key,
                orjson.dumps(jsonable_encoder(link)),
                ex=self.DEFAULT_OBJECT_TTL,
            )

        pipe.set(
            index_key,
            orjson.dumps(
                {
                    "ids": link_ids,
                    "total": total,
                }
            ),
            ex=self.DEFAULT_INDEX_TTL,
        )

        await pipe.execute()

    # =========================================================
    # Cache-Aside Helper
    # =========================================================

    async def get_or_set_paginated_links(
        self,
        page: int,
        limit: int,
        fetch_func,
    ):
        """
        Cache-aside pattern with stampede protection.

        fetch_func must return:
        (
            links,
            total
        )
        """

        cached = await self.get_paginated_links(
            page,
            limit,
        )

        if cached is not None:
            # Return the value from Redis
            logger.debug("Returning cached links")
            return cached

        version = await self.get_cache_version()

        lock_key = f"lock:links:v{version}:page:{page}:limit:{limit}"

        acquired = await self.acquire_lock(lock_key)

        if acquired:
            try:
                # Double-check after lock acquisition
                cached = await self.get_paginated_links(
                    page,
                    limit,
                )

                if cached is not None:
                    return cached

                links, total = await fetch_func()

                # Set the value in Redis
                await self.set_paginated_links(
                    page=page,
                    limit=limit,
                    links=links,
                    total=total,
                )

                return {
                    "links": jsonable_encoder(links),
                    "total": total,
                }

            finally:
                await self.release_lock(lock_key)

        # Wait briefly for first request to populate cache
        await asyncio.sleep(0.1)

        cached = await self.get_paginated_links(
            page,
            limit,
        )

        if cached is not None:
            return cached

        # Fallback to DB
        links, total = await fetch_func()

        return {
            "links": jsonable_encoder(links),
            "total": total,
        }
