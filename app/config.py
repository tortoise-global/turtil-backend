from pydantic import Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    # ============================================================================
    # PYTHON APPLICATION CONFIGURATION
    # ============================================================================
    
    # Application Configuration
    project_name: str = Field(
        default="turtil-backend", env="PROJECT_NAME", description="Project name"
    )
    version: str = Field(
        default="1.0.0", env="VERSION", description="Application version"
    )
    environment: str = Field(
        default="dev", env="ENVIRONMENT", description="Environment"
    )
    debug: bool = Field(default=True, env="DEBUG", description="Debug mode")
    log_level: str = Field(default="INFO", env="LOG_LEVEL", description="Log level")
    port: int = Field(default=8000, env="PORT", description="Server port")

    # Database Configuration
    database_url: str = Field(
        ...,
        env="DATABASE_URL",
        description="PostgreSQL database URL (automatically converted to asyncpg format)",
    )

    # Security Configuration
    secret_key: str = Field(..., env="SECRET_KEY", description="JWT secret key")
    algorithm: str = Field(
        default="HS256", env="ALGORITHM", description="JWT algorithm"
    )
    cms_access_token_expire_minutes: int = Field(
        default=30, env="CMS_ACCESS_TOKEN_EXPIRE_MINUTES", description="CMS access token expiration time"
    )
    cms_refresh_token_expire_days: int = Field(
        default=30, env="CMS_REFRESH_TOKEN_EXPIRE_DAYS", description="CMS refresh token expiration time in days"
    )

    # CORS and Host Configuration
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000",
        env="CORS_ORIGINS",
        description="Comma-separated CORS origins",
    )

    allowed_hosts: str = Field(
        default="*,localhost,127.0.0.1,0.0.0.0",
        env="ALLOWED_HOSTS",
        description="Comma-separated allowed hosts",
    )

    @property
    def cors_origins_list(self) -> List[str]:
        return [i.strip() for i in self.cors_origins.split(",") if i.strip()]

    @property
    def allowed_hosts_list(self) -> List[str]:
        return [i.strip() for i in self.allowed_hosts.split(",") if i.strip()]

    # Rate Limiting Configuration
    rate_limit_calls: int = Field(
        default=100, env="RATE_LIMIT_CALLS", description="Rate limit calls per period"
    )
    rate_limit_period: int = Field(
        default=60, env="RATE_LIMIT_PERIOD", description="Rate limit period in seconds"
    )

    # OTP Configuration
    dev_otp: str = Field(
        default="123456", env="DEV_OTP", description="Fixed OTP for development mode"
    )
    

    # Upstash Redis Configuration
    upstash_redis_url: str = Field(
        ..., env="UPSTASH_REDIS_URL", description="Upstash Redis URL"
    )
    upstash_redis_token: str = Field(
        ..., env="UPSTASH_REDIS_TOKEN", description="Upstash Redis token"
    )
    redis_blacklist_ttl: int = Field(
        default=86400, env="REDIS_BLACKLIST_TTL", description="Redis blacklist TTL"
    )

    # ============================================================================
    # AWS SERVICES CONFIGURATION
    # ============================================================================

    # AWS Core Configuration
    aws_access_key_id: str = Field(
        ..., env="AWS_ACCESS_KEY_ID", description="AWS access key ID"
    )
    aws_secret_access_key: str = Field(
        ..., env="AWS_SECRET_ACCESS_KEY", description="AWS secret access key"
    )
    aws_region: str = Field(
        default="ap-south-1", env="AWS_REGION", description="AWS region"
    )


    # Email Configuration (AWS SES)
    aws_ses_from_email: str = Field(
        default="support@turtil.co",
        env="AWS_SES_FROM_EMAIL",
        description="AWS SES from email",
    )
    aws_ses_region: str = Field(
        default="ap-south-1", env="AWS_SES_REGION", description="AWS SES region"
    )


    @property
    def is_development(self) -> bool:
        return self.environment.lower() in ["dev", "local"]
    
    # S3 Bucket Configuration
    s3_bucket_name: str = Field(
        default="turtil-backend-dev", env="S3_BUCKET_NAME", description="S3 bucket name for all storage"
    )

    model_config = ConfigDict(
        env_file=os.getenv("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Allow extra environment variables
    )


# Global settings instance
settings = Settings()


# Development helper to print configuration (without secrets)
def print_config():
    """Print non-sensitive configuration for debugging"""
    config_dict = settings.dict()
    sensitive_keys = {
        "secret_key",
        "database_url",
        "aws_access_key_id",
        "aws_secret_access_key",
        "upstash_redis_token",
    }

    safe_config = {
        k: "***HIDDEN***" if k in sensitive_keys else v for k, v in config_dict.items()
    }

    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="dim")
    table.add_column("Value")

    for key, value in safe_config.items():
        table.add_row(key, str(value))

    console.print(table)
