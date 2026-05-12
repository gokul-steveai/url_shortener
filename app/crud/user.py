import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.auth import hash_password, verify_password

logger = logging.getLogger(__name__)


class CRUDUser:

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalars().first()

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalars().first()

    @staticmethod
    async def create(db: AsyncSession, email: str, password: str) -> User:
        user = User(email=email, hashed_password=hash_password(password))
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info("user.created id=%s email=%s", user.id, email)
        return user

    @staticmethod
    async def authenticate(db: AsyncSession, email: str, password: str) -> Optional[User]:
        user = await CRUDUser.get_by_email(db, email)
        if not user or not verify_password(password, user.hashed_password):
            logger.warning("auth.failed email=%s", email)
            return None
        if not user.is_active:
            logger.warning("auth.inactive email=%s", email)
            return None
        logger.info("auth.success user_id=%s", user.id)
        return user

    @staticmethod
    async def set_reset_token(db: AsyncSession, user: User) -> str:
        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(reset_token=token, reset_token_expires_at=expires)
        )
        await db.commit()
        logger.info("auth.reset_token_issued user_id=%s", user.id)
        return token

    @staticmethod
    async def get_by_reset_token(db: AsyncSession, token: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.reset_token == token))
        user = result.scalars().first()
        if not user:
            return None
        if not user.reset_token_expires_at:
            return None
        expires = user.reset_token_expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            logger.warning("auth.reset_token_expired user_id=%s", user.id)
            return None
        return user

    @staticmethod
    async def reset_password(db: AsyncSession, user: User, new_password: str) -> None:
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(
                hashed_password=hash_password(new_password),
                reset_token=None,
                reset_token_expires_at=None,
            )
        )
        await db.commit()
        logger.info("auth.password_reset user_id=%s", user.id)
