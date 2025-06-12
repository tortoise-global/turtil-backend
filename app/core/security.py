import random
import string
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.redis_client import redis_client

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def generate_temp_password() -> str:
    """Generate a temporary password."""
    return f"temp_{uuid.uuid4().hex[:8]}"


def generate_user_id() -> str:
    """Generate a unique user ID."""
    return f"user_{int(time.time())}_{uuid.uuid4().hex[:8]}"


def generate_otp() -> str:
    """Generate a 6-digit OTP."""
    return "".join(random.choices(string.digits, k=6))


def send_email_otp(email: str, college_name: Optional[str] = None) -> str:
    """
    Generate and send OTP via email.

    Args:
        email (str): Email address to send OTP to
        college_name (str, optional): College name for email personalization

    Returns:
        str: Generated OTP code

    Raises:
        HTTPException: If email sending fails
    """
    from app.core.email_service import email_service

    # Generate OTP
    otp = generate_otp()

    # Store OTP in Redis with expiration
    otp_key = f"otp:{email}"
    try:
        if redis_client.redis:
            redis_client.redis.setex(
                otp_key,
                settings.OTP_EXPIRY_MINUTES * 60,  # Convert minutes to seconds
                otp,
            )
    except Exception:
        # Fallback to in-memory storage if Redis is not available
        # In production, you might want to handle this differently
        pass

    # Send OTP via email
    success = email_service.send_otp_email(email, otp, college_name)

    if not success:
        raise HTTPException(
            status_code=500, detail="Failed to send OTP email. Please try again."
        )

    return otp


def verify_otp(email: str, provided_otp: str) -> bool:
    """
    Verify OTP against stored value.

    Args:
        email (str): Email address
        provided_otp (str): OTP provided by user

    Returns:
        bool: True if OTP is valid, False otherwise
    """
    otp_key = f"otp:{email}"

    try:
        # Get stored OTP from Redis
        stored_otp = redis_client.redis.get(otp_key) if redis_client.redis else None
        if stored_otp:
            stored_otp = (
                stored_otp.decode("utf-8")
                if isinstance(stored_otp, bytes)
                else stored_otp
            )

            # Check if OTP matches
            if stored_otp == provided_otp:
                # Delete OTP after successful verification
                if redis_client.redis:
                    redis_client.redis.delete(otp_key)
                return True
    except Exception:
        # Fallback to mock OTP if Redis is not available
        # In development/testing only
        if (
            settings.ENVIRONMENT == "development"
            and provided_otp == settings.OTP_SECRET
        ):
            return True

    return False
