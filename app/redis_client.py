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

    async def scan_keys(self, pattern: str) -> list:
        """Scan for keys matching pattern"""
        try:
            result = await self.client.keys(pattern)
            return result or []
        except Exception as e:
            logger.error(f"Failed to scan keys with pattern {pattern}: {e}")
            return []

    async def delete_keys(self, keys: list) -> int:
        """Delete multiple keys"""
        if not keys:
            return 0
        try:
            result = await self.client.delete(*keys)
            return result or 0
        except Exception as e:
            logger.error(f"Failed to delete keys {keys}: {e}")
            return 0

    async def smembers(self, key: str) -> list:
        """Get all members of a set"""
        try:
            result = await self.client.smembers(key)
            return result or []
        except Exception as e:
            logger.error(f"Failed to get set members for {key}: {e}")
            return []

    async def spop(self, key: str, count: int = 1) -> list:
        """Remove and return random members from set"""
        try:
            if count == 1:
                result = await self.client.spop(key)
                return [result] if result else []
            else:
                result = await self.client.spop(key, count)
                return result or []
        except Exception as e:
            logger.error(f"Failed to pop from set {key}: {e}")
            return []

    async def pipeline(self):
        """Create Redis pipeline for batch operations"""
        try:
            return self.client.pipeline()
        except Exception as e:
            logger.error(f"Failed to create pipeline: {e}")
            return None

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

    @staticmethod
    async def create_session(session_id: str, session_data: dict, ttl: int = None) -> bool:
        """Create session in Redis"""
        ttl = ttl or (30 * 24 * 3600)  # 30 days default
        try:
            data = json.dumps(session_data)
            return await redis_client.setex(f"session:{session_id}", ttl, data)
        except Exception as e:
            logger.error(f"Failed to create session {session_id}: {e}")
            return False

    @staticmethod
    async def get_session(session_id: str) -> Optional[dict]:
        """Get session data from Redis"""
        try:
            data = await redis_client.get(f"session:{session_id}")
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None

    @staticmethod
    async def update_session(session_id: str, session_data: dict, ttl: int = None) -> bool:
        """Update session data in Redis"""
        ttl = ttl or (30 * 24 * 3600)  # 30 days default
        try:
            data = json.dumps(session_data)
            return await redis_client.setex(f"session:{session_id}", ttl, data)
        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {e}")
            return False

    @staticmethod
    async def delete_session(session_id: str) -> bool:
        """Delete session from Redis"""
        try:
            result = await redis_client.delete(f"session:{session_id}")
            return result > 0
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    @staticmethod
    async def add_user_session(staff_id: int, session_id: str) -> bool:
        """Add session to user's session set"""
        try:
            result = await redis_client.sadd(f"user_sessions:{staff_id}", session_id)
            return result > 0
        except Exception as e:
            logger.error(f"Failed to add session to user {staff_id}: {e}")
            return False

    @staticmethod
    async def remove_user_session(staff_id: int, session_id: str) -> bool:
        """Remove session from user's session set"""
        try:
            result = await redis_client.srem(f"user_sessions:{staff_id}", session_id)
            return result > 0
        except Exception as e:
            logger.error(f"Failed to remove session from user {staff_id}: {e}")
            return False

    @staticmethod
    async def get_user_sessions(staff_id: int) -> list:
        """Get all session IDs for a user"""
        try:
            return await redis_client.smembers(f"user_sessions:{staff_id}")
        except Exception as e:
            logger.error(f"Failed to get user sessions for {staff_id}: {e}")
            return []

    @staticmethod
    async def invalidate_all_user_sessions(staff_id: int) -> bool:
        """Invalidate all sessions for a user (password reset)"""
        try:
            # Get all session IDs for user
            session_ids = await redis_client.smembers(f"user_sessions:{staff_id}")
            
            # Delete all session data
            for session_id in session_ids:
                await redis_client.delete(f"session:{session_id}")
            
            # Clear user's session index
            await redis_client.delete(f"user_sessions:{staff_id}")
            
            logger.info(f"Invalidated {len(session_ids)} sessions for staff {staff_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to invalidate all sessions for staff {staff_id}: {e}")
            return False

    @staticmethod
    async def blacklist_refresh_token(token_hash: str, reason: str = "rotated", ttl: int = 3600) -> bool:
        """Add refresh token to blacklist"""
        try:
            import time
            blacklist_data = {
                "invalidated_at": time.time(),
                "reason": reason
            }
            data = json.dumps(blacklist_data)
            return await redis_client.setex(f"blacklist:token:{token_hash}", ttl, data)
        except Exception as e:
            logger.error(f"Failed to blacklist token: {e}")
            return False

    @staticmethod
    async def is_refresh_token_blacklisted(token_hash: str) -> bool:
        """Check if refresh token is blacklisted"""
        try:
            return await redis_client.exists(f"blacklist:token:{token_hash}")
        except Exception as e:
            logger.error(f"Failed to check token blacklist: {e}")
            return False

    @staticmethod
    async def store_password_reset_token(email: str, temp_token: str, ttl: int = 600) -> bool:
        """Store temporary token for password reset (10 minutes)"""
        try:
            import time
            token_data = {
                "temp_token": temp_token,
                "created_at": time.time(),
                "expires_at": time.time() + ttl
            }
            data = json.dumps(token_data)
            return await redis_client.setex(f"reset_token:{email}", ttl, data)
        except Exception as e:
            logger.error(f"Failed to store reset token for {email}: {e}")
            return False

    @staticmethod
    async def get_password_reset_token(email: str) -> Optional[str]:
        """Get temporary token for password reset"""
        try:
            data = await redis_client.get(f"reset_token:{email}")
            if data:
                token_data = json.loads(data)
                return token_data.get("temp_token")
            return None
        except Exception as e:
            logger.error(f"Failed to get reset token for {email}: {e}")
            return None

    @staticmethod
    async def invalidate_password_reset_token(email: str) -> bool:
        """Remove password reset token"""
        try:
            result = await redis_client.delete(f"reset_token:{email}")
            return result > 0
        except Exception as e:
            logger.error(f"Failed to invalidate reset token for {email}: {e}")
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
