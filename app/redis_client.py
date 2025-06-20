import json
from typing import Optional, Dict
from app.config import settings
import logging
from upstash_redis.asyncio import Redis

logger = logging.getLogger(__name__)


class UpstashRedisClient:
    """
    Upstash Redis client wrapper using official upstash-redis package.
    Provides a consistent interface for serverless Redis operations.
    """

    def __init__(self, url: str = None, token: str = None):
        self.url = url or settings.upstash_redis_url
        self.token = token or settings.upstash_redis_token
        self.client = Redis(url=self.url, token=self.token)

    async def get(self, key: str) -> Optional[str]:
        """Get a value by key"""
        return await self.client.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set a value with optional expiration (in seconds)"""
        if ex:
            result = await self.client.setex(key, ex, value)
        else:
            result = await self.client.set(key, value)
        return result == "OK"

    async def delete(self, key: str) -> int:
        """Delete a key, returns number of deleted keys"""
        result = await self.client.delete(key)
        return result or 0

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        result = await self.client.exists(key)
        return result == 1

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for a key"""
        result = await self.client.expire(key, seconds)
        return result == 1

    async def ttl(self, key: str) -> int:
        """Get time to live for a key"""
        result = await self.client.ttl(key)
        return result or -1

    async def incr(self, key: str) -> int:
        """Increment a key's value"""
        result = await self.client.incr(key)
        return result or 0

    async def decr(self, key: str) -> int:
        """Decrement a key's value"""
        result = await self.client.decr(key)
        return result or 0

    async def setex(self, key: str, seconds: int, value: str) -> bool:
        """Set key with expiration"""
        result = await self.client.setex(key, seconds, value)
        return result == "OK"

    async def hset(self, key: str, field: str, value: str) -> int:
        """Set field in hash"""
        result = await self.client.hset(key, field, value)
        return result or 0

    async def hget(self, key: str, field: str) -> Optional[str]:
        """Get field from hash"""
        return await self.client.hget(key, field)

    async def hgetall(self, key: str) -> Dict[str, str]:
        """Get all fields from hash"""
        result = await self.client.hgetall(key)
        return result or {}

    async def hdel(self, key: str, field: str) -> int:
        """Delete field from hash"""
        result = await self.client.hdel(key, field)
        return result or 0

    async def sadd(self, key: str, *members: str) -> int:
        """Add members to set"""
        result = await self.client.sadd(key, *members)
        return result or 0

    async def srem(self, key: str, *members: str) -> int:
        """Remove members from set"""
        result = await self.client.srem(key, *members)
        return result or 0

    async def sismember(self, key: str, member: str) -> bool:
        """Check if member is in set"""
        result = await self.client.sismember(key, member)
        return result == 1

    async def ping(self) -> bool:
        """Ping Redis server"""
        try:
            result = await self.client.ping()
            return result == "PONG"
        except Exception:
            return False

    async def close(self):
        """Close the Redis client"""
        # Official upstash-redis client handles connection management
        pass


# Global Redis client instance
redis_client = UpstashRedisClient()


# Cache utilities
class CacheManager:
    """High-level cache management utilities"""

    @staticmethod
    async def cache_staff(staff_id: str, staff_data: dict, ttl: int = None) -> bool:
        """Cache staff data"""
        ttl = ttl or settings.redis_staff_cache_ttl
        try:
            data = json.dumps(staff_data)
            return await redis_client.setex(f"staff:{staff_id}", ttl, data)
        except Exception as e:
            logger.error(f"Failed to cache staff {staff_id}: {e}")
            return False

    @staticmethod
    async def get_cached_staff(staff_id: str) -> Optional[dict]:
        """Get cached staff data"""
        try:
            data = await redis_client.get(f"staff:{staff_id}")
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Failed to get cached staff {staff_id}: {e}")
            return None

    @staticmethod
    async def invalidate_staff_cache(staff_id: str) -> bool:
        """Remove staff from cache"""
        try:
            result = await redis_client.delete(f"staff:{staff_id}")
            return result > 0
        except Exception as e:
            logger.error(f"Failed to invalidate staff cache {staff_id}: {e}")
            return False

    @staticmethod
    async def blacklist_token(token: str, ttl: int = None) -> bool:
        """Add token to blacklist"""
        ttl = ttl or settings.redis_blacklist_ttl
        try:
            return await redis_client.setex(f"blacklist:{token}", ttl, "1")
        except Exception as e:
            logger.error(f"Failed to blacklist token: {e}")
            return False

    @staticmethod
    async def is_token_blacklisted(token: str) -> bool:
        """Check if token is blacklisted"""
        try:
            return await redis_client.exists(f"blacklist:{token}")
        except Exception as e:
            logger.error(f"Failed to check token blacklist: {e}")
            return False

    @staticmethod
    async def cache_otp(email: str, otp: str, ttl: int = 300) -> bool:
        """Cache OTP for email verification"""
        try:
            return await redis_client.setex(f"otp:{email}", ttl, otp)
        except Exception as e:
            logger.error(f"Failed to cache OTP for {email}: {e}")
            return False

    @staticmethod
    async def get_cached_otp(email: str) -> Optional[str]:
        """Get cached OTP for email"""
        try:
            return await redis_client.get(f"otp:{email}")
        except Exception as e:
            logger.error(f"Failed to get cached OTP for {email}: {e}")
            return None

    @staticmethod
    async def invalidate_otp(email: str) -> bool:
        """Remove OTP from cache"""
        try:
            result = await redis_client.delete(f"otp:{email}")
            return result > 0
        except Exception as e:
            logger.error(f"Failed to invalidate OTP for {email}: {e}")
            return False


# Health check for Redis
async def check_redis_health() -> dict:
    """Check Redis health and return status"""
    try:
        is_healthy = await redis_client.ping()
        return {
            "redis": {
                "status": "healthy" if is_healthy else "unhealthy",
                "url": settings.upstash_redis_url,
                "type": "upstash_http",
            }
        }
    except Exception as e:
        return {"redis": {"status": "error", "error": str(e)}}


# Dependency for FastAPI
async def get_redis() -> UpstashRedisClient:
    """Dependency to get Redis client"""
    return redis_client


# Cleanup function
async def close_redis():
    """Close Redis client connections"""
    try:
        await redis_client.close()
        logger.info("Redis client closed")
    except Exception as e:
        logger.error(f"Error closing Redis client: {e}")
