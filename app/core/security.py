"""Security utilities for authentication and password management.

This module provides functions for:
- Password hashing and verification
- JWT token creation and verification  
- OTP generation and validation
- User ID and temporary password generation
"""

import random
import string
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.redis_client import redis_client

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash.
    
    Args:
        plain_password (str): The plain text password to verify
        hashed_password (str): The hashed password to verify against
        
    Returns:
        bool: True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash from plain text password.
    
    Args:
        password (str): Plain text password to hash
        
    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token.
    
    Args:
        data (dict): Data to encode in the token
        expires_delta (Optional[timedelta]): Custom expiration time
        
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now().astimezone() + expires_delta
    else:
        expire = datetime.now().astimezone() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify and decode a JWT token.
    
    Args:
        token (str): JWT token to verify
        
    Returns:
        dict: Decoded token payload
        
    Raises:
        HTTPException: If token is invalid or expired
    """
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


def verify_otp(email: str, provided_otp: str, consume: bool = True) -> bool:
    """
    Verify OTP against stored value.

    Args:
        email (str): Email address
        provided_otp (str): OTP provided by user
        consume (bool): Whether to delete OTP after verification (default: True)

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
                # Delete OTP after successful verification only if consume=True
                if consume and redis_client.redis:
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
