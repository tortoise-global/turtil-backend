import json
import secrets
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.redis_client import redis_client
from app.config import settings


class CMSOTPManager:
    """Redis-based OTP management for CMS authentication"""

    OTP_PREFIX = "cms_otp"
    SESSION_PREFIX = "cms_session"
    OTP_LENGTH = 6
    OTP_EXPIRY_SECONDS = 300  # 5 minutes
    MAX_ATTEMPTS = 3

    @classmethod
    def _get_otp_key(cls, email: str) -> str:
        """Generate Redis key for OTP storage"""
        return f"{cls.OTP_PREFIX}:{email.lower()}"

    @classmethod
    def _get_session_key(cls, staff_id: int) -> str:
        """Generate Redis key for CMS staff session storage"""
        return f"{cls.SESSION_PREFIX}:{staff_id}"

    @classmethod
    def generate_otp(cls) -> str:
        """Generate a 6-digit OTP"""
        # Use fixed OTP in development mode
        if settings.is_development:
            return settings.dev_otp
        return "".join([str(secrets.randbelow(10)) for _ in range(cls.OTP_LENGTH)])

    @classmethod
    async def store_otp(cls, email: str, otp: str) -> bool:
        """
        Store OTP in Redis with expiry and attempt tracking
        """
        try:
            key = cls._get_otp_key(email)
            otp_data = {
                "otp": otp,
                "attempts": 0,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            # Store with TTL
            await redis_client.setex(key, cls.OTP_EXPIRY_SECONDS, json.dumps(otp_data))
            return True

        except Exception as e:
            print(f"Error storing OTP: {e}")
            return False

    @classmethod
    async def verify_otp(cls, email: str, provided_otp: str) -> Dict[str, Any]:
        """
        Verify OTP and track attempts
        Returns: {"valid": bool, "attempts": int, "exceeded": bool, "expired": bool, "verified": bool}
        """
        try:
            key = cls._get_otp_key(email)
            otp_data_str = await redis_client.get(key)

            if not otp_data_str:
                return {
                    "valid": False,
                    "attempts": 0,
                    "exceeded": False,
                    "expired": True,
                    "verified": False,
                }

            otp_data = json.loads(otp_data_str)
            current_attempts = otp_data.get("attempts", 0)

            # Check if max attempts exceeded
            if current_attempts >= cls.MAX_ATTEMPTS:
                return {
                    "valid": False,
                    "attempts": current_attempts,
                    "exceeded": True,
                    "expired": False,
                    "verified": otp_data.get("verified", False),
                }

            # Increment attempts
            otp_data["attempts"] = current_attempts + 1

            # Check OTP validity
            is_valid = otp_data["otp"] == provided_otp

            if is_valid:
                # Mark OTP as verified but don't clear it
                otp_data["verified"] = True
                otp_data["verified_at"] = datetime.now(timezone.utc).isoformat()
                
                # Update OTP in Redis with remaining TTL
                ttl = await redis_client.ttl(key)
                if ttl > 0:
                    await redis_client.setex(key, ttl, json.dumps(otp_data))
                
                return {
                    "valid": True,
                    "attempts": otp_data["attempts"],
                    "exceeded": False,
                    "expired": False,
                    "verified": True,
                }
            else:
                # Update attempts in Redis
                ttl = await redis_client.ttl(key)
                if ttl > 0:
                    await redis_client.setex(key, ttl, json.dumps(otp_data))

                return {
                    "valid": False,
                    "attempts": otp_data["attempts"],
                    "exceeded": otp_data["attempts"] >= cls.MAX_ATTEMPTS,
                    "expired": False,
                    "verified": otp_data.get("verified", False),
                }

        except Exception as e:
            print(f"Error verifying OTP: {e}")
            return {"valid": False, "attempts": 0, "exceeded": False, "expired": True, "verified": False}

    @classmethod
    async def clear_otp(cls, email: str) -> bool:
        """Clear OTP from Redis"""
        try:
            key = cls._get_otp_key(email)
            await redis_client.delete(key)
            return True
        except Exception as e:
            print(f"Error clearing OTP: {e}")
            return False

    @classmethod
    async def get_otp_attempts(cls, email: str) -> int:
        """Get current OTP attempt count"""
        try:
            key = cls._get_otp_key(email)
            otp_data_str = await redis_client.get(key)

            if not otp_data_str:
                return 0

            otp_data = json.loads(otp_data_str)
            return otp_data.get("attempts", 0)

        except Exception as e:
            print(f"Error getting OTP attempts: {e}")
            return 0

    @classmethod
    async def get_otp_status(cls, email: str) -> Dict[str, Any]:
        """Get OTP status including verification state"""
        try:
            key = cls._get_otp_key(email)
            otp_data_str = await redis_client.get(key)

            if not otp_data_str:
                return {
                    "exists": False,
                    "verified": False,
                    "expired": True,
                    "attempts": 0,
                    "exceeded": False,
                }

            otp_data = json.loads(otp_data_str)
            current_attempts = otp_data.get("attempts", 0)

            return {
                "exists": True,
                "verified": otp_data.get("verified", False),
                "expired": False,
                "attempts": current_attempts,
                "exceeded": current_attempts >= cls.MAX_ATTEMPTS,
                "created_at": otp_data.get("created_at"),
                "verified_at": otp_data.get("verified_at"),
            }

        except Exception as e:
            print(f"Error getting OTP status: {e}")
            return {
                "exists": False,
                "verified": False,
                "expired": True,
                "attempts": 0,
                "exceeded": False,
            }

    @classmethod
    async def is_otp_verified(cls, email: str) -> bool:
        """Check if OTP is verified and still valid"""
        try:
            status = await cls.get_otp_status(email)
            return status["exists"] and status["verified"] and not status["expired"]
        except Exception as e:
            print(f"Error checking OTP verification: {e}")
            return False

    @classmethod
    async def mark_otp_verified(cls, email: str) -> bool:
        """Mark OTP as verified without clearing it"""
        try:
            key = cls._get_otp_key(email)
            otp_data_str = await redis_client.get(key)

            if not otp_data_str:
                return False

            otp_data = json.loads(otp_data_str)
            otp_data["verified"] = True
            otp_data["verified_at"] = datetime.now(timezone.utc).isoformat()

            # Update OTP in Redis with remaining TTL
            ttl = await redis_client.ttl(key)
            if ttl > 0:
                await redis_client.setex(key, ttl, json.dumps(otp_data))
                return True
            return False

        except Exception as e:
            print(f"Error marking OTP as verified: {e}")
            return False

    @classmethod
    async def expire_otp(cls, email: str) -> bool:
        """Manually expire OTP (used after password setup)"""
        try:
            key = cls._get_otp_key(email)
            await redis_client.delete(key)
            return True
        except Exception as e:
            print(f"Error expiring OTP: {e}")
            return False

    @classmethod
    async def store_staff_session(
        cls, staff_id: int, session_data: Dict[str, Any]
    ) -> bool:
        """
        Store staff session data in Redis
        """
        try:
            key = cls._get_session_key(staff_id)
            session_data["lastActivity"] = datetime.now(timezone.utc).isoformat()

            # Store with 30-day TTL (refresh token lifetime)
            await redis_client.setex(
                key,
                settings.cms_refresh_token_expire_days
                * 24
                * 3600,  # 30 days in seconds
                json.dumps(session_data, default=str),
            )
            return True

        except Exception as e:
            print(f"Error storing staff session: {e}")
            return False

    @classmethod
    async def get_staff_session(cls, staff_id: int) -> Optional[Dict[str, Any]]:
        """Get staff session data from Redis"""
        try:
            key = cls._get_session_key(staff_id)
            session_data_str = await redis_client.get(key)

            if not session_data_str:
                return None

            return json.loads(session_data_str)

        except Exception as e:
            print(f"Error getting staff session: {e}")
            return None

    @classmethod
    async def update_staff_permissions(
        cls, staff_id: int, permissions: Dict[str, Dict[str, bool]]
    ) -> bool:
        """
        Update staff permissions in Redis session for real-time access
        """
        try:
            session_data = await cls.get_staff_session(staff_id)
            if not session_data:
                return False

            session_data["permissions"] = permissions
            session_data["lastActivity"] = datetime.now(timezone.utc).isoformat()

            return await cls.store_staff_session(staff_id, session_data)

        except Exception as e:
            print(f"Error updating staff permissions: {e}")
            return False

    @classmethod
    async def clear_staff_session(cls, staff_id: int) -> bool:
        """Clear staff session from Redis (logout)"""
        try:
            key = cls._get_session_key(staff_id)
            await redis_client.delete(key)
            return True
        except Exception as e:
            print(f"Error clearing staff session: {e}")
            return False

    @classmethod
    async def refresh_session_activity(cls, staff_id: int) -> bool:
        """Update last activity timestamp in staff session"""
        try:
            session_data = await cls.get_staff_session(staff_id)
            if not session_data:
                return False

            session_data["lastActivity"] = datetime.now(timezone.utc).isoformat()
            return await cls.store_staff_session(staff_id, session_data)

        except Exception as e:
            print(f"Error refreshing session activity: {e}")
            return False

    @classmethod
    async def store_blacklist_entry(
        cls, key: str, data: Dict[str, Any], ttl_seconds: int
    ) -> bool:
        """Store blacklist entry in Redis with TTL"""
        try:
            await redis_client.setex(key, ttl_seconds, json.dumps(data, default=str))
            return True
        except Exception as e:
            print(f"Error storing blacklist entry: {e}")
            return False

    @classmethod
    async def is_blacklisted(cls, key: str) -> bool:
        """Check if a key exists in Redis blacklist"""
        try:
            result = await redis_client.get(key)
            return result is not None
        except Exception as e:
            print(f"Error checking blacklist: {e}")
            return False
