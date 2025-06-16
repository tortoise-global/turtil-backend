"""Application configuration settings.

This module provides production-ready configuration management with enhanced security
and environment-specific settings.
"""

import os
from typing import List, Optional

try:
    from app.core.config_manager import AdvancedSettings

    # Use advanced configuration system
    _advanced_settings = AdvancedSettings()

    class Settings:
        """Production-ready settings with advanced configuration."""

        # Application Settings
        PROJECT_NAME = _advanced_settings.project_name
        VERSION = _advanced_settings.version
        API_V1_STR = "/api/v1"
        ENVIRONMENT = _advanced_settings.environment
        DEBUG = _advanced_settings.debug
        LOG_LEVEL = _advanced_settings.monitoring.log_level

        # Security
        SECRET_KEY = _advanced_settings.security.secret_key
        ALGORITHM = _advanced_settings.security.algorithm
        ACCESS_TOKEN_EXPIRE_MINUTES = (
            _advanced_settings.security.access_token_expire_minutes
        )

        # Database
        DATABASE_URL = _advanced_settings.database.url

        # CORS and Security
        CORS_ORIGINS = _advanced_settings.security.cors_origins
        ALLOWED_HOSTS = _advanced_settings.security.allowed_hosts

        # Rate Limiting
        RATE_LIMIT_CALLS = _advanced_settings.security.rate_limit_calls
        RATE_LIMIT_PERIOD = _advanced_settings.security.rate_limit_period

        # OTP Configuration
        OTP_SECRET = _advanced_settings.otp_secret
        OTP_EXPIRY_MINUTES = _advanced_settings.otp_expiry_minutes

        # AWS Configuration
        AWS_ACCESS_KEY_ID = _advanced_settings.storage.aws_access_key_id
        AWS_SECRET_ACCESS_KEY = _advanced_settings.storage.aws_secret_access_key
        AWS_REGION = _advanced_settings.storage.aws_region
        S3_BUCKET_NAME = _advanced_settings.storage.s3_bucket_name

        # Redis Configuration
        UPSTASH_REDIS_URL = _advanced_settings.redis.url
        UPSTASH_REDIS_TOKEN = _advanced_settings.redis.token
        REDIS_USER_CACHE_TTL = _advanced_settings.redis.user_cache_ttl
        REDIS_BLACKLIST_TTL = _advanced_settings.redis.blacklist_ttl

        # Email Configuration
        GMAIL_EMAIL = _advanced_settings.email.smtp_user
        GMAIL_APP_PASSWORD = _advanced_settings.email.smtp_password

        # Feature Flags
        ENABLE_REGISTRATION = _advanced_settings.enable_registration
        ENABLE_PASSWORD_RESET = _advanced_settings.enable_password_reset
        ENABLE_EMAIL_VERIFICATION = _advanced_settings.enable_email_verification
        ENABLE_MAINTENANCE_MODE = _advanced_settings.enable_maintenance_mode

        @property
        def is_production(self) -> bool:
            """Check if running in production."""
            return self.ENVIRONMENT == "production"

        @property
        def is_development(self) -> bool:
            """Check if running in development."""
            return self.ENVIRONMENT == "development"

        @property
        def advanced(self):
            """Access to advanced configuration features."""
            return _advanced_settings

    settings = Settings()

except ImportError:
    # Fallback to simple configuration if advanced config is not available
    import secrets

    class FallbackSettings:
        """Fallback settings for basic operation."""

        PROJECT_NAME = os.getenv("PROJECT_NAME", "Turtil Backend")
        VERSION = os.getenv("VERSION", "1.0.0")
        API_V1_STR = "/api/v1"
        ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        DEBUG = os.getenv("DEBUG", "true").lower() == "true"
        LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

        SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
        ALGORITHM = os.getenv("ALGORITHM", "HS256")
        ACCESS_TOKEN_EXPIRE_MINUTES = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        )

        DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./db/turtil.db")

        CORS_ORIGINS = ["http://localhost:3000", "http://localhost:8080"]
        ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

        RATE_LIMIT_CALLS = int(os.getenv("RATE_LIMIT_CALLS", "100"))
        RATE_LIMIT_PERIOD = int(os.getenv("RATE_LIMIT_PERIOD", "60"))

        OTP_SECRET = os.getenv("OTP_SECRET", "123456")
        OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES", "5"))

        AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
        AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
        AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
        S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

        UPSTASH_REDIS_URL = os.getenv("UPSTASH_REDIS_URL", "http://localhost:8079")
        UPSTASH_REDIS_TOKEN = os.getenv("UPSTASH_REDIS_TOKEN", "example_token")
        REDIS_USER_CACHE_TTL = int(os.getenv("REDIS_USER_CACHE_TTL", "300"))
        REDIS_BLACKLIST_TTL = int(os.getenv("REDIS_BLACKLIST_TTL", "86400"))

        GMAIL_EMAIL = os.getenv("GMAIL_EMAIL")
        GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

        ENABLE_REGISTRATION = True
        ENABLE_PASSWORD_RESET = True
        ENABLE_EMAIL_VERIFICATION = True
        ENABLE_MAINTENANCE_MODE = False

        @property
        def is_production(self) -> bool:
            return self.ENVIRONMENT == "production"

        @property
        def is_development(self) -> bool:
            return self.ENVIRONMENT == "development"

    settings = FallbackSettings()
    print(
        "Warning: Using fallback configuration. Advanced features may not be available."
    )
