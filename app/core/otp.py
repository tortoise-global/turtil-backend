import random
import secrets
from typing import Optional
from datetime import datetime, timedelta
import json

from app.redis_client import redis_client
from app.config import settings


class OTPManager:
    """OTP management using Upstash Redis for storage and expiration"""

    @staticmethod
    def generate_otp() -> str:
        """Generate a 6-digit OTP"""
        return str(random.randint(100000, 999999))

    @staticmethod
    def generate_signup_token() -> str:
        """Generate a secure signup token"""
        return secrets.token_urlsafe(32)

    @staticmethod
    async def store_signup_otp(
        email: str,
        otp: str,
        signup_data: dict,
        signup_token: str,
        expiry_minutes: Optional[int] = None,
    ) -> bool:
        """
        Store signup OTP and staff data in Redis with expiration

        Args:
            email: Staff's email address
            otp: Generated OTP
            signup_data: Staff registration data (full_name, password)
            signup_token: Unique signup token
            expiry_minutes: OTP expiration time (defaults to config value)
        """
        try:
            expiry = expiry_minutes or settings.otp_expiry_minutes

            # Store OTP data
            otp_data = {
                "otp": otp,
                "email": email,
                "signup_token": signup_token,
                "signup_data": signup_data,  # Contains: full_name, password
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(minutes=expiry)).isoformat(),
            }

            # Store in Redis with expiration (in seconds)
            expiry_seconds = expiry * 60

            # Use multiple keys for different lookup patterns
            otp_key = f"signup_otp:{email}"
            token_key = f"signup_token:{signup_token}"

            # Store same data under both keys
            await redis_client.setex(otp_key, expiry_seconds, json.dumps(otp_data))
            await redis_client.setex(token_key, expiry_seconds, json.dumps(otp_data))

            return True

        except Exception as e:
            print(f"Error storing signup OTP: {e}")
            return False

    @staticmethod
    async def verify_signup_otp(email: str, otp: str) -> Optional[dict]:
        """
        Verify signup OTP and return signup data if valid

        Returns:
            dict: Signup data if OTP is valid, None otherwise
        """
        try:
            otp_key = f"signup_otp:{email}"
            stored_data = await redis_client.get(otp_key)

            if not stored_data:
                return None

            otp_data = json.loads(stored_data)

            # Check if OTP matches
            if otp_data.get("otp") != otp:
                return None

            # Check if not expired (Redis should handle this, but double-check)
            expires_at = datetime.fromisoformat(otp_data.get("expires_at"))
            if datetime.now() > expires_at:
                return None

            # Return signup data for staff creation
            return {
                "email": otp_data.get("email"),
                "signup_token": otp_data.get("signup_token"),
                "signup_data": otp_data.get("signup_data"),
                "verified_at": datetime.now().isoformat(),
            }

        except Exception as e:
            print(f"Error verifying signup OTP: {e}")
            return None

    @staticmethod
    async def cleanup_signup_otp(email: str, signup_token: str) -> bool:
        """
        Clean up OTP data after successful signup

        Args:
            email: Staff's email
            signup_token: Signup token to clean up
        """
        try:
            otp_key = f"signup_otp:{email}"
            token_key = f"signup_token:{signup_token}"

            # Delete both keys
            await redis_client.delete(otp_key)
            await redis_client.delete(token_key)

            return True

        except Exception as e:
            print(f"Error cleaning up signup OTP: {e}")
            return False

    @staticmethod
    async def store_login_otp(
        email: str, otp: str, expiry_minutes: Optional[int] = None
    ) -> bool:
        """
        Store login OTP in Redis (for future login OTP feature)

        Args:
            email: Staff's email address
            otp: Generated OTP
            expiry_minutes: OTP expiration time
        """
        try:
            expiry = expiry_minutes or settings.otp_expiry_minutes

            otp_data = {
                "otp": otp,
                "email": email,
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(minutes=expiry)).isoformat(),
                "type": "login",
            }

            expiry_seconds = expiry * 60
            otp_key = f"login_otp:{email}"

            await redis_client.setex(otp_key, expiry_seconds, json.dumps(otp_data))
            return True

        except Exception as e:
            print(f"Error storing login OTP: {e}")
            return False

    @staticmethod
    async def verify_login_otp(email: str, otp: str) -> bool:
        """
        Verify login OTP

        Args:
            email: Staff's email
            otp: OTP to verify

        Returns:
            bool: True if OTP is valid
        """
        try:
            otp_key = f"login_otp:{email}"
            stored_data = await redis_client.get(otp_key)

            if not stored_data:
                return False

            otp_data = json.loads(stored_data)

            # Check OTP match
            if otp_data.get("otp") != otp:
                return False

            # Clean up after successful verification
            await redis_client.delete(otp_key)

            return True

        except Exception as e:
            print(f"Error verifying login OTP: {e}")
            return False

    @staticmethod
    async def get_signup_data_by_token(signup_token: str) -> Optional[dict]:
        """
        Get signup data by token (useful for debugging or admin operations)

        Args:
            signup_token: The signup token

        Returns:
            dict: Signup data if token exists
        """
        try:
            token_key = f"signup_token:{signup_token}"
            stored_data = await redis_client.get(token_key)

            if not stored_data:
                return None

            return json.loads(stored_data)

        except Exception as e:
            print(f"Error getting signup data by token: {e}")
            return None


# Global OTP manager instance
otp_manager = OTPManager()
