import json
import secrets
from datetime import datetime, timezone, timedelta
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
    def _get_session_key(cls, cms_user_id: int) -> str:
        """Generate Redis key for CMS user session storage"""
        return f"{cls.SESSION_PREFIX}:{cms_user_id}"
    
    @classmethod
    def generate_otp(cls) -> str:
        """Generate a 6-digit OTP"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(cls.OTP_LENGTH)])
    
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
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Store with TTL
            await redis_client.setex(
                key, 
                cls.OTP_EXPIRY_SECONDS, 
                json.dumps(otp_data)
            )
            return True
            
        except Exception as e:
            print(f"Error storing OTP: {e}")
            return False
    
    @classmethod
    async def verify_otp(cls, email: str, provided_otp: str) -> Dict[str, Any]:
        """
        Verify OTP and track attempts
        Returns: {"valid": bool, "attempts": int, "exceeded": bool, "expired": bool}
        """
        try:
            key = cls._get_otp_key(email)
            otp_data_str = await redis_client.get(key)
            
            if not otp_data_str:
                return {"valid": False, "attempts": 0, "exceeded": False, "expired": True}
            
            otp_data = json.loads(otp_data_str)
            current_attempts = otp_data.get("attempts", 0)
            
            # Check if max attempts exceeded
            if current_attempts >= cls.MAX_ATTEMPTS:
                return {"valid": False, "attempts": current_attempts, "exceeded": True, "expired": False}
            
            # Increment attempts
            otp_data["attempts"] = current_attempts + 1
            
            # Check OTP validity
            is_valid = otp_data["otp"] == provided_otp
            
            if is_valid:
                # Clear OTP on successful verification
                await redis_client.delete(key)
                return {"valid": True, "attempts": otp_data["attempts"], "exceeded": False, "expired": False}
            else:
                # Update attempts in Redis
                ttl = await redis_client.ttl(key)
                if ttl > 0:
                    await redis_client.setex(key, ttl, json.dumps(otp_data))
                
                return {
                    "valid": False, 
                    "attempts": otp_data["attempts"], 
                    "exceeded": otp_data["attempts"] >= cls.MAX_ATTEMPTS,
                    "expired": False
                }
                
        except Exception as e:
            print(f"Error verifying OTP: {e}")
            return {"valid": False, "attempts": 0, "exceeded": False, "expired": True}
    
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
    async def store_user_session(cls, cms_user_id: int, session_data: Dict[str, Any]) -> bool:
        """
        Store user session data in Redis
        """
        try:
            key = cls._get_session_key(cms_user_id)
            session_data["lastActivity"] = datetime.now(timezone.utc).isoformat()
            
            # Store with 30-day TTL (refresh token lifetime)
            await redis_client.setex(
                key,
                settings.cms_refresh_token_expire_days * 24 * 3600,  # 30 days in seconds
                json.dumps(session_data, default=str)
            )
            return True
            
        except Exception as e:
            print(f"Error storing user session: {e}")
            return False
    
    @classmethod
    async def get_user_session(cls, cms_user_id: int) -> Optional[Dict[str, Any]]:
        """Get user session data from Redis"""
        try:
            key = cls._get_session_key(cms_user_id)
            session_data_str = await redis_client.get(key)
            
            if not session_data_str:
                return None
            
            return json.loads(session_data_str)
            
        except Exception as e:
            print(f"Error getting user session: {e}")
            return None
    
    @classmethod
    async def update_user_permissions(cls, cms_user_id: int, permissions: Dict[str, Dict[str, bool]]) -> bool:
        """
        Update user permissions in Redis session for real-time access
        """
        try:
            session_data = await cls.get_user_session(cms_user_id)
            if not session_data:
                return False
            
            session_data["permissions"] = permissions
            session_data["lastActivity"] = datetime.now(timezone.utc).isoformat()
            
            return await cls.store_user_session(cms_user_id, session_data)
            
        except Exception as e:
            print(f"Error updating user permissions: {e}")
            return False
    
    @classmethod
    async def clear_user_session(cls, cms_user_id: int) -> bool:
        """Clear user session from Redis (logout)"""
        try:
            key = cls._get_session_key(cms_user_id)
            await redis_client.delete(key)
            return True
        except Exception as e:
            print(f"Error clearing user session: {e}")
            return False
    
    @classmethod
    async def refresh_session_activity(cls, cms_user_id: int) -> bool:
        """Update last activity timestamp in user session"""
        try:
            session_data = await cls.get_user_session(cms_user_id)
            if not session_data:
                return False
            
            session_data["lastActivity"] = datetime.now(timezone.utc).isoformat()
            return await cls.store_user_session(cms_user_id, session_data)
            
        except Exception as e:
            print(f"Error refreshing session activity: {e}")
            return False