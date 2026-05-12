import hashlib
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

TOKEN_TYPE = Literal["access", "refresh"]
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _normalize(password: str) -> str:
    """SHA-256 pre-hash keeps input under bcrypt's 72-byte limit."""
    return hashlib.sha256(password.encode()).hexdigest()


def hash_password(password: str) -> str:
    return pwd_context.hash(_normalize(password))


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(_normalize(plain), hashed)


def _create_token(
    subject: str,
    expires_delta: timedelta,
    token_type: TOKEN_TYPE,
) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {"sub": subject, "exp": expire, "type": token_type}
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def create_access_token(user_id: int) -> str:
    return _create_token(
        str(user_id),
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "access",
    )


def create_refresh_token(user_id: int) -> str:
    return _create_token(
        str(user_id),
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "refresh",
    )


def decode_token(token: str, expected_type: TOKEN_TYPE) -> Optional[int]:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != expected_type:
            return None
        sub = payload.get("sub")
        return int(sub) if sub else None
    except JWTError:
        return None
