"""
Signup Schemas
All signup-related request/response schemas for account creation
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from app.core.utils import CamelCaseModel


# Request Schemas

class SignupRequest(CamelCaseModel):
    """Request schema for user registration (send OTP)"""
    email: EmailStr = Field(..., description="Email address for registration")


class VerifyOTPRequest(CamelCaseModel):
    """Request schema for OTP verification"""
    email: EmailStr = Field(..., description="Email address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP")


class SetupProfileRequest(CamelCaseModel):
    """Request schema for profile setup after OTP verification"""
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=8, description="Password")
    confirm_password: str = Field(..., min_length=8, description="Password confirmation")
    full_name: str = Field(..., min_length=1, max_length=200, description="Full name")
    contact_number: str = Field(..., pattern=r"^(\+91)?[6-9]\d{9}$", description="Contact number in Indian format")

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v


class ForgotPasswordRequest(CamelCaseModel):
    """Request schema for forgot password (send OTP)"""
    email: EmailStr = Field(..., description="Email address")


class ResetPasswordRequest(CamelCaseModel):
    """Request schema for password reset with OTP verification"""
    email: EmailStr = Field(..., description="Email address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., min_length=8, description="Password confirmation")

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class ChangePasswordRequest(CamelCaseModel):
    """Request schema for changing password for authenticated users"""
    current_password: str = Field(..., min_length=1, description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., min_length=8, description="Password confirmation")

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


# Response Schemas

class OTPResponse(CamelCaseModel):
    """Response schema for OTP sending"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Status message")
    email: str = Field(..., description="Email where OTP was sent")
    expires_in: int = Field(..., description="OTP expiry time in seconds")


class TempTokenResponse(CamelCaseModel):
    """Response schema for temporary token (after OTP verification)"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Status message")
    temp_token: str = Field(..., description="Temporary token for next step")
    expires_in: int = Field(..., description="Token expiry time in seconds")


class ProfileSetupResponse(CamelCaseModel):
    """Response schema for profile setup completion"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Status message")
    user_id: str = Field(..., description="User UUID")
    requires_college_setup: bool = Field(True, description="Whether college setup is required")


class PasswordResetResponse(CamelCaseModel):
    """Response schema for password reset completion"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Status message")


class SignupResponse(CamelCaseModel):
    """Generic response schema for signup operations"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Status message")
    attempts_remaining: int = Field(..., description="Attempts remaining")


class VerifySignupResponse(CamelCaseModel):
    """Response schema for OTP verification during signup"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Status message")
    next_step: str = Field(..., description="Next step in signup process")
    temp_token: str = Field(..., description="Temporary token for profile setup")


class ForgotPasswordResponse(CamelCaseModel):
    """Response schema for forgot password request"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Status message")
    attempts_remaining: int = Field(..., description="Attempts remaining")
    staff_exists: bool = Field(..., description="Whether staff exists for email")