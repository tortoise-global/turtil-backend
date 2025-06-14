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
    Password: str


class ChangePasswordRequest(BaseModel):
    """Request model for changing user password."""

    email: str
    oldPassword: str
    newPassword: str


class Token(BaseModel):
    """JWT token response model."""

    access_token: str = Field(..., alias="accessToken")
    token_type: str = Field(..., alias="tokenType")
    cmsUserId: str
    role: Optional[str] = None
    profile_completed: bool = False

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
    user_id: str


class CompleteProfileRequest(BaseModel):
    """Request model for completing user profile."""

    full_name: str
    phone: Optional[str] = None
    college_id: str
    role: str = "student"
    department_id: Optional[str] = None
    branch_id: Optional[str] = None
    degree_id: Optional[str] = None
