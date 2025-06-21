from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
from app.core.utils import CamelCaseModel


# Authentication request schemas


class SignupInitRequest(CamelCaseModel):
    """Signup initialization request schema - sends OTP"""

    email: EmailStr = Field(..., description="Staff email address")
    password: str = Field(
        ..., min_length=8, description="Staff password (min 8 characters)"
    )
    full_name: str = Field(
        ..., min_length=1, max_length=200, description="Staff full name"
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class SignupVerifyRequest(CamelCaseModel):
    """Signup verification request schema - verifies OTP and creates staff"""

    email: EmailStr = Field(..., description="Staff email address")
    otp: str = Field(
        ..., min_length=6, max_length=6, description="6-digit OTP from email"
    )
    signup_token: Optional[str] = Field(
        None, description="Signup token for additional security"
    )


class StaffRegisterRequest(CamelCaseModel):
    """Legacy staff registration request schema (for backward compatibility)"""

    email: EmailStr = Field(..., description="Staff email address")
    password: str = Field(
        ..., min_length=8, description="Staff password (min 8 characters)"
    )
    full_name: str = Field(
        ..., min_length=1, max_length=200, description="Staff full name"
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class StaffLoginRequest(CamelCaseModel):
    """Staff login request schema"""

    email: EmailStr = Field(..., description="Staff email address")
    password: str = Field(..., description="Staff password")


class PasswordResetRequest(CamelCaseModel):
    """Password reset request schema"""

    email: EmailStr = Field(..., description="Email address to send reset link")


class PasswordResetConfirm(CamelCaseModel):
    """Password reset confirmation schema"""

    email: EmailStr = Field(..., description="Email address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP")
    new_password: str = Field(..., min_length=8, description="New password")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v):
        """Validate new password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class ChangePasswordRequest(CamelCaseModel):
    """Change password request schema"""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v):
        """Validate new password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class RefreshTokenRequest(CamelCaseModel):
    """Refresh token request schema"""

    refresh_token: str = Field(..., description="Refresh token")


# Authentication response schemas


class TokenResponse(CamelCaseModel):
    """Token response schema"""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    staff: "StaffResponse" = Field(..., description="Staff information")


class StaffResponse(CamelCaseModel):
    """Staff response schema for API responses"""

    id: int = Field(..., description="Staff ID")
    uuid: str = Field(..., description="Staff UUID")
    email: str = Field(..., description="Staff email")
    full_name: str = Field(..., description="Staff full name")
    is_active: bool = Field(..., description="Staff active status")
    is_verified: bool = Field(..., description="Email verification status")
    is_superstaff: bool = Field(..., description="Superstaff status")
    email_verified_at: Optional[datetime] = Field(
        None, description="Email verification timestamp"
    )
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    login_count: int = Field(..., description="Total login count")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class AuthResponse(CamelCaseModel):
    """Generic authentication response"""

    message: str = Field(..., description="Response message")
    success: bool = Field(..., description="Operation success status")
    staff: Optional[StaffResponse] = Field(None, description="Staff information")


class LoginResponse(CamelCaseModel):
    """Login response schema"""

    message: str = Field(..., description="Login response message")
    success: bool = Field(..., description="Login success status")
    tokens: TokenResponse = Field(..., description="Authentication tokens")


class LogoutResponse(CamelCaseModel):
    """Logout response schema"""

    message: str = Field(..., description="Logout response message")
    success: bool = Field(..., description="Logout success status")


class SignupInitResponse(CamelCaseModel):
    """Signup initialization response schema"""

    message: str = Field(..., description="Signup initialization message")
    success: bool = Field(..., description="Operation success status")
    signup_token: str = Field(..., description="Signup token for verification")
    expires_in_minutes: int = Field(..., description="OTP expiration time in minutes")


class SignupVerifyResponse(CamelCaseModel):
    """Signup verification response schema"""

    message: str = Field(..., description="Signup completion message")
    success: bool = Field(..., description="Operation success status")
    staff: StaffResponse = Field(..., description="Created staff information")
    tokens: TokenResponse = Field(..., description="Authentication tokens")


# Token payload schemas


class TokenPayload(BaseModel):
    """JWT token payload schema"""

    sub: str = Field(..., description="Subject (staff UUID)")
    email: str = Field(..., description="Staff email")
    full_name: str = Field(..., description="Staff full name")
    is_verified: bool = Field(..., description="Email verification status")
    is_superstaff: bool = Field(..., description="Superstaff status")
    exp: int = Field(..., description="Token expiration timestamp")
    iat: int = Field(..., description="Token issued at timestamp")
    type: str = Field(..., description="Token type (access/refresh)")


# Update forward references
TokenResponse.model_rebuild()
