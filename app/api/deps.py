from typing import Generator, Optional
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.core.auth import auth
from app.models.user import User
from app.redis_client import get_redis, UpstashRedisClient
import logging

logger = logging.getLogger(__name__)

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current user from JWT token using custom auth system.
    Returns None if no valid token is provided.
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    
    try:
        # Use custom auth manager to get user from token
        user = await auth.get_user_by_token(db, token)
        
        if not user:
            logger.warning("Invalid token or user not found")
            return None
        
        return user
        
    except Exception as e:
        logger.error(f"Error getting user from token: {e}")
        return None


async def get_current_user(
    current_user: User = Depends(get_current_user_from_token)
) -> User:
    """
    Get current authenticated user.
    Raises HTTPException if no valid authentication is provided.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return current_user


async def get_current_verified_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current authenticated and verified user.
    Raises HTTPException if user is not email verified.
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email address first.",
        )
    
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_verified_user)
) -> User:
    """
    Get current authenticated superuser.
    Raises HTTPException if user is not a superuser.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Superuser access required.",
        )
    
    return current_user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current authenticated and active user.
    Raises HTTPException if user is inactive.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )
    
    return current_user


# Optional authentication - returns None if no valid token
async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if valid token is provided, None otherwise.
    Useful for endpoints that work for both authenticated and anonymous users.
    """
    try:
        return await get_current_user_from_token(credentials, db)
    except Exception:
        return None


# Redis dependency
async def get_redis_client() -> UpstashRedisClient:
    """Get Redis client instance"""
    return await get_redis()


# Common query parameters
class CommonQueryParams:
    """Common query parameters for list endpoints"""
    
    def __init__(
        self,
        page: int = 1,
        size: int = 10,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ):
        self.page = max(1, page)  # Ensure page is at least 1
        self.size = min(max(1, size), 100)  # Ensure size is between 1 and 100
        self.search = search
        self.sort_by = sort_by
        self.sort_order = sort_order.lower() if sort_order.lower() in ["asc", "desc"] else "desc"
        
    @property
    def offset(self) -> int:
        """Calculate offset for database queries"""
        return (self.page - 1) * self.size


# Pagination helper
class PaginationParams:
    """Pagination parameters"""
    
    def __init__(self, page: int = 1, size: int = 10):
        self.page = max(1, page)
        self.size = min(max(1, size), 100)
        
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


# Rate limiting dependency
async def check_rate_limit(
    current_user: Optional[User] = Depends(get_optional_current_user),
    redis: UpstashRedisClient = Depends(get_redis_client)
) -> None:
    """
    Check rate limits for API endpoints.
    Different limits for authenticated vs anonymous users.
    """
    from app.config import settings
    import time
    
    # Determine rate limit key
    if current_user:
        rate_limit_key = f"rate_limit:user:{current_user.uuid}"
        max_calls = settings.rate_limit_calls * 2  # Higher limit for authenticated users
    else:
        # For anonymous users, use IP-based limiting (would need IP extraction)
        rate_limit_key = "rate_limit:anonymous"
        max_calls = settings.rate_limit_calls
    
    # Check current count
    try:
        current_count = await redis.get(rate_limit_key)
        current_count = int(current_count) if current_count else 0
        
        if current_count >= max_calls:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
            )
        
        # Increment counter
        if current_count == 0:
            # First request in the period, set with expiration
            await redis.setex(rate_limit_key, settings.rate_limit_period, "1")
        else:
            # Increment existing counter
            await redis.incr(rate_limit_key)
            
    except Exception as e:
        logger.error(f"Rate limiting error: {e}")
        # Don't block requests if rate limiting fails
        pass


# Health check dependencies
async def check_system_health() -> dict:
    """Check overall system health"""
    from app.database import DatabaseManager
    from app.redis_client import check_redis_health
    from app.core.aws import check_aws_health
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {}
    }
    
    try:
        # Check database
        db_health = await DatabaseManager.health_check()
        health_status["services"].update(db_health)
        
        # Check Redis
        redis_health = await check_redis_health()
        health_status["services"].update(redis_health)
        
        # Check AWS services
        aws_health = await check_aws_health()
        health_status["services"].update(aws_health)
        
        # Determine overall status
        unhealthy_services = [
            service for service_name, service in health_status["services"].items()
            for service in (service if isinstance(service, list) else [service])
            if isinstance(service, dict) and service.get("status") != "healthy"
        ]
        
        if unhealthy_services:
            health_status["status"] = "degraded"
            
    except Exception as e:
        logger.error(f"Health check error: {e}")
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)
    
    return health_status