import json
import os
import secrets
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application Settings
    PROJECT_NAME: str = "Turtil Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/turtil_db"

    # CORS and Security
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1", "0.0.0.0"]

    # Rate Limiting
    RATE_LIMIT_CALLS: int = 100
    RATE_LIMIT_PERIOD: int = 60

    # OTP Configuration
    OTP_SECRET: str = "123456"
    OTP_EXPIRY_MINUTES: int = 5

    # AWS Configuration (for S3 only)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: Optional[str] = None

    # Upstash Redis Configuration
    UPSTASH_REDIS_URL: Optional[str] = None
    UPSTASH_REDIS_TOKEN: Optional[str] = None
    REDIS_USER_CACHE_TTL: int = 300  # 5 minutes
    REDIS_BLACKLIST_TTL: int = 86400  # 24 hours

    # Gmail SMTP Configuration for sending emails
    GMAIL_EMAIL: Optional[str] = None
    GMAIL_APP_PASSWORD: Optional[str] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Parse JSON strings from environment variables
        cors_origins = os.getenv("CORS_ORIGINS")
        if cors_origins:
            try:
                self.CORS_ORIGINS = json.loads(cors_origins)
            except json.JSONDecodeError:
                pass

        allowed_hosts = os.getenv("ALLOWED_HOSTS")
        if allowed_hosts:
            try:
                self.ALLOWED_HOSTS = json.loads(allowed_hosts)
            except json.JSONDecodeError:
                pass

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
