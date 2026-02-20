from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Server
    environment: str = "development"
    port: int = 8000
    host: str = "0.0.0.0"

    # Database
    database_path: str = "data/tracker.db"

    # Uploads
    uploads_path: str = "data/uploads"

    # Logging
    log_level: str = "info"

    # Features
    enable_docs: bool = True

    # API
    api_title: str = "Personal Tracker API"
    api_version: str = "1.0.0"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
