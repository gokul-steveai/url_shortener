import asyncio
import orjson
from typing import Any, Optional, Callable, Awaitable
import logging

from fastapi.encoders import jsonable_encoder
from redis.asyncio.client import Redis
from app.utils.pagination import build_paginated_response

logger = logging.getLogger(__name__)


class RedisService:
    # Use class constants for standard configuration
    TTL_OBJ = 3600
    TTL_IDX = 600
    VERSION_KEY = "links:version"

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def get_json(self, key: str) -> Optional[Any]:
        """Generic JSON fetch with auto-cleanup of corrupted data."""
        data = await self.redis.get(key)
        if not data:
            logger.debug("cache.miss key=%s", key)
            return None
        try:
            result = orjson.loads(data)
            logger.debug("cache.hit key=%s", key)
            return result
        except orjson.JSONDecodeError:
            logger.warning("cache.corrupt key=%s — deleting", key)
            await self.redis.delete(key)
            return None

    async def set_json(self, key: str, value: Any, ex: int = TTL_OBJ):
        """Standardized JSON storage using orjson for speed."""
        await self.redis.set(key, orjson.dumps(jsonable_encoder(value)), ex=ex)

    async def _get_v_key(self, page: int, limit: int, owner_id: int = None) -> str:
        """Centralized key generation logic — namespaced per user."""
        v = await self.redis.get(self.VERSION_KEY) or b"1"
        ns = f"u{owner_id}:" if owner_id else ""
        return f"links:{ns}v{v.decode()}:p:{page}:l:{limit}"

    async def bump_version(self):
        """Instantly invalidates all paginated caches."""
        new_v = await self.redis.incr(self.VERSION_KEY)
        logger.info("cache.version_bump new_version=%s", new_v)

    async def get_paginated_links(
        self, page: int, limit: int, owner_id: int = None
    ) -> Optional[dict]:
        """Fetch index and hydrated objects using MGET."""
        key = await self._get_v_key(page, limit, owner_id=owner_id)
        idx = await self.get_json(key)

        if not idx or "ids" not in idx:
            logger.info("cache.miss.paginated page=%s limit=%s", page, limit)
            return None

        if not idx["ids"]:
            return build_paginated_response([], 0, page, limit)

        obj_keys = [f"link:obj:{lid}" for lid in idx["ids"]]
        raw_objs = await self.redis.mget(*obj_keys)

        if any(o is None for o in raw_objs):
            logger.info("cache.miss.partial page=%s — falling back to DB", page)
            return None

        links = [orjson.loads(o) for o in raw_objs]
        logger.info(
            "cache.hit.paginated page=%s limit=%s count=%s", page, limit, len(links)
        )
        return links

    async def set_paginated_links(
        self, page: int, limit: int, links: list, total: int, owner_id: int = None
    ):
        """Pipelined storage for both index and objects."""
        key = await self._get_v_key(page, limit, owner_id=owner_id)
        pipe = self.redis.pipeline()

        link_ids = []
        for link in links:
            lid = link.id if hasattr(link, "id") else link["id"]
            link_ids.append(lid)
            pipe.set(
                f"link:obj:{lid}", orjson.dumps(jsonable_encoder(link)), ex=self.TTL_OBJ
            )

        pipe.set(key, orjson.dumps({"ids": link_ids, "total": total}), ex=self.TTL_IDX)
        await pipe.execute()

    # --- Staff-Level Cache Aside ---

    async def get_or_set(
        self, page: int, limit: int, fetcher: Callable[[], Awaitable[tuple]]
    ):
        """Clean implementation of Cache-Aside with Stampede Protection."""
        # 1. Hot path
        cached = await self.get_paginated_links(page, limit)
        if cached:
            return cached

        # 2. Synchronized fetch (Stampede Protection)
        lock_key = f"lock:{await self._get_v_key(page, limit)}"
        if await self.redis.set(lock_key, "1", ex=10, nx=True):
            try:
                # Double-check inside lock
                cached = await self.get_paginated_links(page, limit)
                if cached:
                    return cached

                links, total = await fetcher()
                await self.set_paginated_links(page, limit, links, total)
                return build_paginated_response(
                    jsonable_encoder(links), total, page, limit
                )
            finally:
                await self.redis.delete(lock_key)

        # 3. Wait/Retry for others
        await asyncio.sleep(0.1)
        return await self.get_paginated_links(page, limit) or build_paginated_response(
            *(await fetcher()), page, limit
        )

    async def invalidate(self, key: str):
        await self.redis.delete(key)
        logger.info("cache.invalidate key=%s", key)
