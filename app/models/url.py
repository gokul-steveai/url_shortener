from sqlalchemy import BigInteger, Column, DateTime, String, Text
from datetime import datetime, timezone
from app.models.base import Base


class URL(Base):
    __tablename__ = "urls"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    original_url = Column(String(2048), index=True, nullable=False)
    short_id = Column(String(10), index=True, unique=True, nullable=False)
    clicks = Column(BigInteger, default=0, nullable=False)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
