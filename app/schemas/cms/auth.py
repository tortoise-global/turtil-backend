"""Authentication and user management schemas.

This module contains Pydantic models for authentication including:
- Login and token models
- Email verification models
- Password management models
- User creation and response models
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    """Request model for user login."""

    userName: str
    password: str


class ChangePasswordRequest(BaseModel):
    """Request model for changing user password."""

    email: str
    oldPassword: str
    newPassword: str


class Token(BaseModel):
    """JWT token response model."""

    access_token: str = Field(..., alias="accessToken")
    token_type: str = Field(..., alias="tokenType")
    cms_user_id: str = Field(..., alias="cmsUserId")
    role: Optional[str] = None
    profile_completed: bool = Field(False, alias="profileCompleted")

    model_config = ConfigDict(populate_by_name=True)


class EmailResponse(BaseModel):
    """Response model for email operations."""

    message: str
    success: bool


class VerifyResponse(BaseModel):
    """Response model for verification operations."""

    message: str
    success: bool
    verified: bool


from app.schemas.cms.users import CMSUserCreate, CMSUserResponse, CMSUserUpdate

CMSUserCreate = CMSUserCreate
CMSUserUpdate = CMSUserUpdate
CMSUserResponse = CMSUserResponse


class FetchCMSUserResponse(CMSUserResponse):
    """Response model for fetching CMS users."""


class SendSignupOTPRequest(BaseModel):
    """Request model for sending signup OTP."""

    email: EmailStr


class VerifySignupOTPRequest(BaseModel):
    """Request model for verifying signup OTP."""

    email: EmailStr
    otp: int


class CompleteSignupRequest(BaseModel):
    """Request model for completing signup with password."""

    email: EmailStr
    otp: int
    password: str


class CompleteSignupResponse(BaseModel):
    """Response model for signup completion."""

    message: str
    success: bool
    user_id: str = Field(..., alias="userId")


class CompleteProfileRequest(BaseModel):
    """Request model for completing user profile."""

    full_name: str = Field(..., alias="fullName")
    phone: Optional[str] = None
    college_id: str = Field(..., alias="collegeId")
    role: str = "student"
    department_id: Optional[str] = Field(None, alias="departmentId")
    branch_id: Optional[str] = Field(None, alias="branchId")
    degree_id: Optional[str] = Field(None, alias="degreeId")

    model_config = ConfigDict(populate_by_name=True)


class CompleteProfileResponse(BaseModel):
    """Response model for profile completion."""

    message: str
    profile_completed: bool = Field(..., alias="profileCompleted")

    model_config = ConfigDict(populate_by_name=True)


class AuthStatusResponse(BaseModel):
    """Response model for authentication status."""

    user_id: str = Field(..., alias="userId")
    username: str
    email: str
    role: str
    college_id: str = Field(..., alias="collegeId")
    is_active: bool = Field(..., alias="isActive")
    last_login: Optional[int] = Field(None, alias="lastLogin")
    token_valid: bool = Field(..., alias="tokenValid")

    model_config = ConfigDict(populate_by_name=True)


class LogoutResponse(BaseModel):
    """Response model for logout."""

    message: str
    user_id: str = Field(..., alias="userId")

    model_config = ConfigDict(populate_by_name=True)


class AdminActionResponse(BaseModel):
    """Response model for admin actions."""

    message: str
    user_id: str = Field(..., alias="userId")
    revoked_at: Optional[int] = Field(None, alias="revokedAt")
    restored_at: Optional[int] = Field(None, alias="restoredAt")
    reason: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class CacheStatsResponse(BaseModel):
    """Response model for cache statistics."""

    cache_available: bool = Field(..., alias="cacheAvailable")
    total_keys: Optional[int] = Field(None, alias="totalKeys")
    memory_usage: Optional[str] = Field(None, alias="memoryUsage")
    hit_rate: Optional[float] = Field(None, alias="hitRate")

    model_config = ConfigDict(populate_by_name=True)
