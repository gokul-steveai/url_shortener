import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings
from app.models.user import User, UserRole
from app.services.auth import decode_token
from app.services.redis_service import RedisService

logger = logging.getLogger(__name__)

# 1. Create a singleton-style Redis client (usually in main.py or a config file)
redis_client = Redis(host="localhost", port=6379, db=0)
_bearer = HTTPBearer()


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


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    from app.crud.user import CRUDUser

    user_id = decode_token(credentials.credentials, expected_type="access")
    if not user_id:
        logger.warning("auth.invalid_token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )

    user = await CRUDUser.get_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.ADMIN:
        logger.warning(
            "auth.forbidden user_id=%s role=%s", current_user.id, current_user.role
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return current_user
