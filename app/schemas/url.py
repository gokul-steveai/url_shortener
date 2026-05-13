from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime


class URLCreate(BaseModel):
    target_url: HttpUrl = Field(..., description="The target URL to be shortened")
    custom_alias: str | None = Field(
        None,
        min_length=4,
        max_length=15,
        description="A custom alias for the shortened URL",
    )


class URLResponse(BaseModel):
    target_url: HttpUrl
    short_url: str
    summary: Optional[str] = None
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True
