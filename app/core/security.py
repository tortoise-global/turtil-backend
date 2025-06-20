from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app.config import settings
import secrets
import string
import logging

logger = logging.getLogger(__name__)

# Password hashing with Argon2 (more secure than bcrypt)
argon2_hasher = PasswordHasher()

# Fallback to bcrypt for compatibility
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityManager:
    """Centralized security management for authentication and authorization"""

    @staticmethod
    def hash_password(password: str, use_argon2: bool = True) -> str:
        """
        Hash a password using Argon2 (preferred) or bcrypt (fallback).
        Argon2 is more secure and recommended for new applications.
        """
        try:
            if use_argon2:
                return argon2_hasher.hash(password)
            else:
                return bcrypt_context.hash(password)
        except Exception as e:
            logger.error(f"Error hashing password: {e}")
            # Fallback to bcrypt if Argon2 fails
            return bcrypt_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        Supports both Argon2 and bcrypt hashes for migration compatibility.
        """
        try:
            # Try Argon2 first (starts with $argon2)
            if hashed_password.startswith("$argon2"):
                argon2_hasher.verify(hashed_password, plain_password)
                return True
            else:
                # Fall back to bcrypt
                return bcrypt_context.verify(plain_password, hashed_password)
        except (VerifyMismatchError, ValueError):
            return False
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False

    @staticmethod
    def create_access_token(
        data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token"""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=settings.access_token_expire_minutes
            )

        to_encode.update(
            {"exp": expire, "iat": datetime.now(timezone.utc), "type": "access"}
        )

        try:
            encoded_jwt = jwt.encode(
                to_encode, settings.secret_key, algorithm=settings.algorithm
            )
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error creating access token: {e}")
            raise

    @staticmethod
    def create_refresh_token(
        data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT refresh token (longer expiration)"""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            # Refresh tokens last 7 days by default
            expire = datetime.now(timezone.utc) + timedelta(days=7)

        to_encode.update(
            {"exp": expire, "iat": datetime.now(timezone.utc), "type": "refresh"}
        )

        try:
            encoded_jwt = jwt.encode(
                to_encode, settings.secret_key, algorithm=settings.algorithm
            )
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error creating refresh token: {e}")
            raise

    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
        """
        Verify and decode JWT token.
        Returns payload if valid, None if invalid.
        """
        try:
            payload = jwt.decode(
                token, settings.secret_key, algorithms=[settings.algorithm]
            )

            # Check token type
            if payload.get("type") != token_type:
                logger.warning(
                    f"Invalid token type. Expected {token_type}, got {payload.get('type')}"
                )
                return None

            # Check expiration
            exp = payload.get("exp")
            if exp is None:
                logger.warning("Token missing expiration")
                return None

            if datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(
                timezone.utc
            ):
                logger.warning("Token has expired")
                return None

            return payload

        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error verifying token: {e}")
            return None

    @staticmethod
    def generate_otp(length: int = 6) -> str:
        """Generate a random OTP code"""
        digits = string.digits
        return "".join(secrets.choice(digits) for _ in range(length))

    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate a secure random token for various uses"""
        return secrets.token_urlsafe(length)

    @staticmethod
    def is_password_strong(password: str) -> tuple[bool, list[str]]:
        """
        Check if password meets security requirements.
        Returns (is_strong, list_of_issues)
        """
        issues = []

        if len(password) < 8:
            issues.append("Password must be at least 8 characters long")

        if not any(c.isupper() for c in password):
            issues.append("Password must contain at least one uppercase letter")

        if not any(c.islower() for c in password):
            issues.append("Password must contain at least one lowercase letter")

        if not any(c.isdigit() for c in password):
            issues.append("Password must contain at least one digit")

        special_chars = '!@#$%^&*(),.?":{}|<>'
        if not any(c in special_chars for c in password):
            issues.append("Password must contain at least one special character")

        return len(issues) == 0, issues


# Convenience functions for backward compatibility
def hash_password(password: str) -> str:
    """Hash password using the security manager"""
    return SecurityManager.hash_password(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password using the security manager"""
    return SecurityManager.verify_password(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create access token using the security manager"""
    return SecurityManager.create_access_token(data, expires_delta)


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create refresh token using the security manager"""
    return SecurityManager.create_refresh_token(data, expires_delta)


def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    """Verify token using the security manager"""
    return SecurityManager.verify_token(token, token_type)


def generate_otp(length: int = 6) -> str:
    """Generate OTP using the security manager"""
    return SecurityManager.generate_otp(length)


# Password strength validator for API
def validate_password_strength(password: str) -> bool:
    """Simple password strength validation"""
    is_strong, _ = SecurityManager.is_password_strong(password)
    return is_strong


# Token blacklist utilities (using Redis)
async def blacklist_token(token: str, ttl: Optional[int] = None) -> bool:
    """Add token to blacklist"""
    from app.redis_client import CacheManager

    ttl = ttl or settings.access_token_expire_minutes * 60
    return await CacheManager.blacklist_token(token, ttl)


async def is_token_blacklisted(token: str) -> bool:
    """Check if token is blacklisted"""
    from app.redis_client import CacheManager

    return await CacheManager.is_token_blacklisted(token)
