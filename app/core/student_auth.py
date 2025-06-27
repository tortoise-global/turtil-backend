"""
Student Authentication Manager
JWT token creation and validation for student mobile app
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Union
from fastapi import HTTPException, status
from jose import JWTError, jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import settings
from app.models.student import Student
import logging

logger = logging.getLogger(__name__)


class StudentAuthManager:
    """
    Student authentication manager with single-device session support
    Separate from CMS auth with different JWT secrets and token structures
    """

    def __init__(self):
        self.password_hasher = PasswordHasher()
        # Use separate JWT secret for student tokens
        self.student_secret_key = f"{settings.secret_key}_STUDENT"
        self.algorithm = settings.algorithm
        self.access_token_expire_minutes = 30  # Shorter for mobile
        self.refresh_token_expire_days = 30

    def get_password_hash(self, password: str) -> str:
        """Hash password using Argon2"""
        try:
            return self.password_hasher.hash(password)
        except Exception as e:
            logger.error(f"Password hashing failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process password"
            )

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash using Argon2"""
        try:
            self.password_hasher.verify(hashed_password, plain_password)
            return True
        except VerifyMismatchError:
            return False
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False

    def create_student_access_token(
        self, 
        student: Student, 
        session_id: str = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token for student with session tracking"""
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)

        # Create token payload with student-specific data
        to_encode = {
            "type": "access",
            "sub": str(student.student_id),
            "email": student.email,
            "fullName": student.full_name,
            "collegeId": str(student.college_id) if student.college_id else None,
            "sectionId": str(student.section_id) if student.section_id else None,
            "registrationCompleted": student.registration_completed,
            "canAccessApp": student.can_access_app(),
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }

        # Add session ID if provided (for session validation)
        if session_id:
            to_encode["session_id"] = session_id

        try:
            encoded_jwt = jwt.encode(to_encode, self.student_secret_key, algorithm=self.algorithm)
            logger.debug(f"Created access token for student {student.student_id}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"Failed to create access token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create access token"
            )

    def create_student_refresh_token(
        self,
        student: Student,
        session_id: str = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT refresh token for student session management"""
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)

        # Minimal payload for refresh token
        to_encode = {
            "type": "refresh",
            "sub": str(student.student_id),
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }

        # Add session ID for session tracking
        if session_id:
            to_encode["session_id"] = session_id

        try:
            encoded_jwt = jwt.encode(to_encode, self.student_secret_key, algorithm=self.algorithm)
            logger.debug(f"Created refresh token for student {student.student_id}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"Failed to create refresh token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create refresh token"
            )

    def decode_student_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate student JWT token"""
        try:
            payload = jwt.decode(token, self.student_secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except JWTError as e:
            logger.warning(f"JWT decode error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )

    def validate_access_token(self, token: str) -> Dict[str, Any]:
        """Validate student access token and return payload"""
        payload = self.decode_student_token(token)
        
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        return payload

    def validate_refresh_token(self, token: str) -> Dict[str, Any]:
        """Validate student refresh token and return payload"""
        payload = self.decode_student_token(token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        return payload

    def generate_secure_temp_token(self) -> str:
        """Generate cryptographically secure temporary token for multi-step flows"""
        return secrets.token_urlsafe(32)

    def hash_token(self, token: str) -> str:
        """Create SHA256 hash of token for secure storage"""
        return hashlib.sha256(token.encode()).hexdigest()

    def authenticate_student(self, email: str, password: str, student: Student) -> bool:
        """Authenticate student with email and password"""
        if not student:
            return False
        
        if student.email.lower() != email.lower():
            return False
        
        if not student.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is not active"
            )
        
        if not student.is_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email not verified. Please complete registration first."
            )
        
        return self.verify_password(password, student.hashed_password)

    def get_token_expires_in(self) -> int:
        """Get access token expiration time in seconds"""
        return self.access_token_expire_minutes * 60

    def extract_student_id_from_token(self, token: str) -> Optional[str]:
        """Extract student ID from token without full validation (for session management)"""
        try:
            # Decode without verification to get student ID
            payload = jwt.decode(token, key="", options={"verify_signature": False})
            return payload.get("sub")
        except Exception as e:
            logger.warning(f"Failed to extract student ID from token: {e}")
            return None

    def create_password_reset_token(self, student: Student) -> str:
        """Create temporary token for password reset flow"""
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)  # 15 minutes for password reset
        
        to_encode = {
            "type": "password_reset",
            "sub": str(student.student_id),
            "email": student.email,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.student_secret_key, algorithm=self.algorithm)
            return encoded_jwt
        except Exception as e:
            logger.error(f"Failed to create password reset token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create password reset token"
            )

    def validate_password_reset_token(self, token: str) -> Dict[str, Any]:
        """Validate password reset token"""
        payload = self.decode_student_token(token)
        
        if payload.get("type") != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type for password reset"
            )
        
        return payload


# Global student auth manager instance
student_auth = StudentAuthManager()