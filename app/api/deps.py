from fastapi import Depends
from redis.asyncio import Redis
from app.services.redis_service import RedisService
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# 1. Create a singleton-style Redis client (usually in main.py or a config file)
redis_client = Redis(host="localhost", port=6379, db=0)


# 2. Define the dependency
async def get_redis_client():
    return RedisService(redis_client)

"""
Create dependency for database session
"""
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql", "postgresql+asyncpg"),
    echo=False,  # Set to True for debugging SQL logs
    pool_size=20,  # Maintain a pool of 20 connections
    max_overflow=10,  # Allow 10 extra connections during traffic spikes
)

# Create the Async Session Maker
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,  # Tells the maker to produce Async sessions
    expire_on_commit=False,  # Prevents errors when accessing data after commit
    autoflush=False,  # Prevents errors when accessing data before commit
)


# Dependency to get the database session
async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
