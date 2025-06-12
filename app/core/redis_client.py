import json
import logging
import time
from typing import Any, Dict, Optional, Union

from upstash_redis import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class UpstashRedisClient:
    def __init__(self):
        self.redis: Optional[Redis] = None
        self._initialize_client()

    def _initialize_client(self):
        try:
            if settings.UPSTASH_REDIS_URL and settings.UPSTASH_REDIS_TOKEN:
                self.redis = Redis(
                    url=settings.UPSTASH_REDIS_URL, token=settings.UPSTASH_REDIS_TOKEN
                )
                logger.info("Upstash Redis client initialized successfully")
            else:
                logger.warning(
                    "Upstash Redis credentials not found. Operating without cache."
                )
        except Exception as e:
            logger.error(f"Failed to initialize Upstash Redis client: {e}")
            self.redis = None

    def is_available(self) -> bool:
        if not self.redis:
            return False
        try:
            # Test connection with ping
            result = self.redis.ping()
            return result == "PONG"
        except Exception as e:
            logger.error(f"Redis availability check failed: {e}")
            return False

    # User Cache Methods
    def cache_user(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """Cache user data with TTL for fast authentication."""
        if not self.redis:
            return False

        try:
            key = f"user:{user_id}"
            serialized_data = json.dumps(user_data, default=str)

            result = self.redis.setex(
                key, settings.REDIS_USER_CACHE_TTL, serialized_data
            )

            logger.info(f"Cached user data for user_id: {user_id}")
            return result == "OK"
        except Exception as e:
            logger.error(f"Failed to cache user {user_id}: {e}")
            return False

    def get_cached_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached user data."""
        if not self.redis:
            return None

        try:
            key = f"user:{user_id}"
            cached_data = self.redis.get(key)

            if cached_data:
                user_data = json.loads(cached_data)
                logger.info(f"Retrieved cached user data for user_id: {user_id}")
                return user_data

            logger.info(f"No cached data found for user_id: {user_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve cached user {user_id}: {e}")
            return None

    def invalidate_user_cache(self, user_id: str) -> bool:
        """Remove user from cache."""
        if not self.redis:
            return False

        try:
            key = f"user:{user_id}"
            result = self.redis.delete(key)
            logger.info(f"Invalidated cache for user_id: {user_id}")
            return result > 0
        except Exception as e:
            logger.error(f"Failed to invalidate cache for user {user_id}: {e}")
            return False

    # Blacklist Methods for Immediate Revocation
    def blacklist_user(self, user_id: str, reason: str = "revoked") -> bool:
        """Add user to blacklist for immediate access revocation."""
        if not self.redis:
            return False

        try:
            key = f"blacklist:{user_id}"
            blacklist_data = {
                "user_id": user_id,
                "reason": reason,
                "revoked_at": str(int(time.time())),
            }

            result = self.redis.setex(
                key, settings.REDIS_BLACKLIST_TTL, json.dumps(blacklist_data)
            )

            # Also invalidate user cache
            self.invalidate_user_cache(user_id)

            logger.info(f"Blacklisted user_id: {user_id}, reason: {reason}")
            return result == "OK"
        except Exception as e:
            logger.error(f"Failed to blacklist user {user_id}: {e}")
            return False

    def is_user_blacklisted(self, user_id: str) -> bool:
        """Check if user is blacklisted."""
        if not self.redis:
            return False

        try:
            key = f"blacklist:{user_id}"
            result = self.redis.get(key)

            if result:
                logger.info(f"User {user_id} is blacklisted")
                return True

            return False
        except Exception as e:
            logger.error(f"Failed to check blacklist for user {user_id}: {e}")
            return False

    def remove_from_blacklist(self, user_id: str) -> bool:
        """Remove user from blacklist (restore access)."""
        if not self.redis:
            return False

        try:
            key = f"blacklist:{user_id}"
            result = self.redis.delete(key)
            logger.info(f"Removed user_id {user_id} from blacklist")
            return result > 0
        except Exception as e:
            logger.error(f"Failed to remove user {user_id} from blacklist: {e}")
            return False

    # Token Management
    def cache_token(self, token_id: str, user_id: str, expires_in: int) -> bool:
        """Cache token for fast validation."""
        if not self.redis:
            return False

        try:
            key = f"token:{token_id}"
            token_data = {"user_id": user_id, "created_at": str(int(time.time()))}

            result = self.redis.setex(key, expires_in, json.dumps(token_data))

            logger.info(f"Cached token for user_id: {user_id}")
            return result == "OK"
        except Exception as e:
            logger.error(f"Failed to cache token: {e}")
            return False

    def get_token_data(self, token_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve token data."""
        if not self.redis:
            return None

        try:
            key = f"token:{token_id}"
            cached_data = self.redis.get(key)

            if cached_data:
                return json.loads(cached_data)

            return None
        except Exception as e:
            logger.error(f"Failed to retrieve token data: {e}")
            return None

    def invalidate_token(self, token_id: str) -> bool:
        """Invalidate specific token."""
        if not self.redis:
            return False

        try:
            key = f"token:{token_id}"
            result = self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Failed to invalidate token: {e}")
            return False

    # Bulk Operations
    def invalidate_all_user_tokens(self, user_id: str) -> bool:
        """Invalidate all tokens for a specific user."""
        if not self.redis:
            return False

        try:
            # Get all token keys for the user
            pattern = f"token:*"
            keys = self.redis.keys(pattern)

            deleted_count = 0
            for key in keys:
                try:
                    token_data = self.redis.get(key)
                    if token_data:
                        data = json.loads(token_data)
                        if data.get("user_id") == user_id:
                            self.redis.delete(key)
                            deleted_count += 1
                except Exception:
                    continue

            logger.info(f"Invalidated {deleted_count} tokens for user_id: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to invalidate all tokens for user {user_id}: {e}")
            return False

    # Statistics and Monitoring
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        if not self.redis:
            return {"status": "unavailable"}

        try:
            # Get counts of different key types
            user_keys = len(self.redis.keys("user:*"))
            blacklist_keys = len(self.redis.keys("blacklist:*"))
            token_keys = len(self.redis.keys("token:*"))

            return {
                "status": "connected",
                "cached_users": user_keys,
                "blacklisted_users": blacklist_keys,
                "cached_tokens": token_keys,
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"status": "error", "error": str(e)}


# Global Redis client instance
redis_client = UpstashRedisClient()
