"""Advanced configuration management for production environments.

This module provides secure, environment-aware configuration management.
"""

import json
import os
import secrets
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseSettings, Field, validator
from pydantic.env_settings import SettingsSourceCallable

from app.core.exceptions import ConfigurationError


class DatabaseConfig(BaseSettings):
    """Database configuration settings."""

    url: str = Field(..., env="DATABASE_URL")
    pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT")
    pool_recycle: int = Field(default=3600, env="DB_POOL_RECYCLE")
    echo: bool = Field(default=False, env="DB_ECHO")

    @validator("url")
    def validate_database_url(cls, v):
        """Validate database URL format."""
        if not v.startswith(("postgresql://", "postgresql+psycopg2://", "sqlite:///")):
            raise ValueError("DATABASE_URL must be a valid PostgreSQL or SQLite URL")
        return v


class RedisConfig(BaseSettings):
    """Redis configuration settings."""

    url: str = Field(default="redis://localhost:6379", env="UPSTASH_REDIS_URL")
    token: Optional[str] = Field(default=None, env="UPSTASH_REDIS_TOKEN")
    user_cache_ttl: int = Field(default=300, env="REDIS_USER_CACHE_TTL")
    blacklist_ttl: int = Field(default=86400, env="REDIS_BLACKLIST_TTL")
    max_connections: int = Field(default=10, env="REDIS_MAX_CONNECTIONS")
    socket_timeout: float = Field(default=5.0, env="REDIS_SOCKET_TIMEOUT")


class SecurityConfig(BaseSettings):
    """Security configuration settings."""

    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # Password requirements
    min_password_length: int = Field(default=8, env="MIN_PASSWORD_LENGTH")
    require_special_chars: bool = Field(default=True, env="REQUIRE_SPECIAL_CHARS")
    require_numbers: bool = Field(default=True, env="REQUIRE_NUMBERS")
    require_uppercase: bool = Field(default=True, env="REQUIRE_UPPERCASE")

    # Rate limiting
    rate_limit_calls: int = Field(default=100, env="RATE_LIMIT_CALLS")
    rate_limit_period: int = Field(default=60, env="RATE_LIMIT_PERIOD")

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000"], env="CORS_ORIGINS"
    )
    allowed_hosts: List[str] = Field(
        default=["localhost", "127.0.0.1"], env="ALLOWED_HOSTS"
    )

    @validator("secret_key")
    def validate_secret_key(cls, v):
        """Validate secret key strength."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v

    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return json.loads(v)
        return v

    @validator("allowed_hosts", pre=True)
    def parse_allowed_hosts(cls, v):
        """Parse allowed hosts from string or list."""
        if isinstance(v, str):
            return json.loads(v)
        return v


class EmailConfig(BaseSettings):
    """Email configuration settings."""

    smtp_host: str = Field(default="smtp.gmail.com", env="GMAIL_SMTP_HOST")
    smtp_port: int = Field(default=587, env="GMAIL_SMTP_PORT")
    smtp_user: str = Field(..., env="GMAIL_EMAIL")
    smtp_password: str = Field(..., env="GMAIL_APP_PASSWORD")
    from_name: str = Field(default="Turtil CMS", env="EMAIL_FROM_NAME")

    @validator("smtp_password")
    def validate_smtp_password(cls, v):
        """Validate SMTP password is provided."""
        if not v or len(v) < 8:
            raise ValueError("Gmail app password must be provided and valid")
        return v


class StorageConfig(BaseSettings):
    """File storage configuration settings."""

    aws_access_key_id: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(
        default=None, env="AWS_SECRET_ACCESS_KEY"
    )
    aws_region: str = Field(default="us-east-1", env="AWS_REGION")
    s3_bucket_name: Optional[str] = Field(default=None, env="S3_BUCKET_NAME")

    # Local storage fallback
    upload_dir: str = Field(default="uploads", env="UPLOAD_DIR")
    max_file_size: int = Field(default=10485760, env="MAX_FILE_SIZE")  # 10MB
    allowed_extensions: List[str] = Field(
        default=[".jpg", ".jpeg", ".png", ".gif", ".pdf", ".doc", ".docx"],
        env="ALLOWED_EXTENSIONS",
    )

    @validator("allowed_extensions", pre=True)
    def parse_allowed_extensions(cls, v):
        """Parse allowed extensions from string or list."""
        if isinstance(v, str):
            return v.split(",")
        return v


class MonitoringConfig(BaseSettings):
    """Monitoring and logging configuration."""

    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    enable_request_logging: bool = Field(default=True, env="ENABLE_REQUEST_LOGGING")
    enable_sql_logging: bool = Field(default=False, env="ENABLE_SQL_LOGGING")

    # Performance thresholds
    slow_query_threshold: float = Field(default=1.0, env="SLOW_QUERY_THRESHOLD")
    slow_request_threshold: float = Field(default=2.0, env="SLOW_REQUEST_THRESHOLD")

    # Health check settings
    health_check_interval: int = Field(default=60, env="HEALTH_CHECK_INTERVAL")

    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {valid_levels}")
        return v.upper()


class AdvancedSettings(BaseSettings):
    """Advanced application configuration."""

    # Application metadata
    project_name: str = Field(default="Turtil Backend", env="PROJECT_NAME")
    version: str = Field(default="1.0.0", env="VERSION")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")

    # Feature flags
    enable_registration: bool = Field(default=True, env="ENABLE_REGISTRATION")
    enable_password_reset: bool = Field(default=True, env="ENABLE_PASSWORD_RESET")
    enable_email_verification: bool = Field(
        default=True, env="ENABLE_EMAIL_VERIFICATION"
    )
    enable_maintenance_mode: bool = Field(default=False, env="ENABLE_MAINTENANCE_MODE")

    # OTP settings
    otp_secret: str = Field(default="123456", env="OTP_SECRET")
    otp_expiry_minutes: int = Field(default=5, env="OTP_EXPIRY_MINUTES")

    # Nested configurations
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    security: SecurityConfig = SecurityConfig()
    email: EmailConfig = EmailConfig()
    storage: StorageConfig = StorageConfig()
    monitoring: MonitoringConfig = MonitoringConfig()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        allow_mutation = False

    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment setting."""
        valid_envs = ["development", "testing", "staging", "production"]
        if v not in valid_envs:
            raise ValueError(f"ENVIRONMENT must be one of: {valid_envs}")
        return v

    @validator("debug")
    def validate_debug_in_production(cls, v, values):
        """Ensure debug is disabled in production."""
        if values.get("environment") == "production" and v:
            raise ValueError("DEBUG must be False in production environment")
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"

    @property
    def database_url(self) -> str:
        """Get database URL."""
        return self.database.url

    @property
    def redis_url(self) -> str:
        """Get Redis URL."""
        return self.redis.url


def load_config_from_file(file_path: str) -> Dict[str, Any]:
    """Load configuration from JSON file.

    Args:
        file_path: Path to configuration file

    Returns:
        Configuration dictionary

    Raises:
        ConfigurationError: If file cannot be loaded
    """
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        raise ConfigurationError(
            config_key=file_path, message=f"Configuration file not found: {file_path}"
        )
    except json.JSONDecodeError as e:
        raise ConfigurationError(
            config_key=file_path, message=f"Invalid JSON in configuration file: {e}"
        )


def validate_required_env_vars():
    """Validate that all required environment variables are set.

    Raises:
        ConfigurationError: If required variables are missing
    """
    required_vars = [
        "DATABASE_URL",
        "SECRET_KEY",
        "GMAIL_EMAIL",
        "GMAIL_APP_PASSWORD",
    ]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        raise ConfigurationError(
            config_key="environment_variables",
            message=f"Missing required environment variables: {', '.join(missing_vars)}",
        )


def generate_secret_key() -> str:
    """Generate a secure secret key.

    Returns:
        Secure random string
    """
    return secrets.token_urlsafe(32)


def create_env_template(file_path: str = ".env.template"):
    """Create an environment template file.

    Args:
        file_path: Path for the template file
    """
    template = """# Turtil Backend Configuration Template

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/turtil_db

# Security
SECRET_KEY=your-super-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application Settings
PROJECT_NAME=Turtil Backend
VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# CORS Settings
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]
ALLOWED_HOSTS=["localhost", "127.0.0.1", "0.0.0.0"]

# Rate Limiting
RATE_LIMIT_CALLS=100
RATE_LIMIT_PERIOD=60

# OTP Configuration
OTP_SECRET=123456
OTP_EXPIRY_MINUTES=5

# Redis Configuration
UPSTASH_REDIS_URL=redis://localhost:6379
UPSTASH_REDIS_TOKEN=your-redis-token
REDIS_USER_CACHE_TTL=300
REDIS_BLACKLIST_TTL=86400

# Email Configuration
GMAIL_EMAIL=your-email@gmail.com
GMAIL_APP_PASSWORD=your-gmail-app-password

# AWS Configuration (Optional)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-s3-bucket

# Feature Flags
ENABLE_REGISTRATION=true
ENABLE_PASSWORD_RESET=true
ENABLE_EMAIL_VERIFICATION=true
ENABLE_MAINTENANCE_MODE=false

# Monitoring
ENABLE_REQUEST_LOGGING=true
ENABLE_SQL_LOGGING=false
SLOW_QUERY_THRESHOLD=1.0
SLOW_REQUEST_THRESHOLD=2.0
"""

    with open(file_path, "w") as f:
        f.write(template)


# Global settings instance
try:
    settings = AdvancedSettings()
    validate_required_env_vars()
except Exception as e:
    print(f"Configuration error: {e}")
    print("Creating environment template...")
    create_env_template()
    raise ConfigurationError(
        config_key="initialization",
        message="Configuration initialization failed. Please check your environment variables.",
    )
