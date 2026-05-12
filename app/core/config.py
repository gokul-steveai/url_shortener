from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "URL Shortener"
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    API_URL: str = "http://localhost:8000"
    GROQ_API_KEY: str | None = None
    LOG_LEVEL: str = "INFO"   # DEBUG | INFO | WARNING | ERROR
    LOG_FORMAT: str = "dev"   # dev | json

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()