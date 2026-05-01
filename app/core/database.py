from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Create the Async Engine
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
