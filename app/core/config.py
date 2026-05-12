from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "URL Shortener"
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    API_URL: str = "http://localhost:8000"
    GROQ_API_KEY: str | None = None
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "dev"

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Email (SMTP) — for password reset
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAILS_FROM: str = "noreply@boltlink.io"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
