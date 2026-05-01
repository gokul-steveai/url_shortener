from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from app.models.url import URL
from app.services.shortener import ShortenerService

class CRUDURL:
    
    def __init__(self, redis_client: Redis):
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
            await self.redis_client.set(f"url:{short_id}", db_url.original_url, ex=86400)
            return db_url.original_url
        
        return None
    
    async def create(self, db:AsyncSession, origin_url: str) -> URL:
        # Create a new URL in the database to get the new id
        new_url = URL(original_url=origin_url, short_id='TEMP')
        db.add(new_url)

        await db.flush()

        # Encode the new id and update the short_id
        short_id = ShortenerService.encode(new_url.id)
        new_url.short_id = short_id

        await db.commit()
        await db.refresh(new_url)

        return new_url
    