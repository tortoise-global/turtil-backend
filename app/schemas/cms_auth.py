from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime


class CMSSigninRequest(BaseModel):
    """Request schema for combined sign-in flow (sends OTP for both new and existing staff)"""

    email: EmailStr = Field(..., description="College/University email address")


class CMSVerifySigninRequest(BaseModel):
    """Request schema for verifying sign-in OTP (handles both login and registration)"""

    email: EmailStr = Field(..., description="Email address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP")


class CMSProfileSetupRequest(BaseModel):
    """Request schema for profile setup - password, full name, and contact number (step 2)"""

    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=8, description="Password")
    confirmPassword: str = Field(..., min_length=8, description="Password confirmation")
    fullName: str = Field(..., min_length=1, max_length=200, description="Full name (username)")
    contactNumber: str = Field(..., pattern=r"^(\+91)?[6-9]\d{9}$", description="Contact number in Indian format")

    @field_validator("confirmPassword")
    @classmethod
    def passwords_match(cls, v, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v


class CMSCollegeLogoRequest(BaseModel):
    """Request schema for college logo upload (step 2)"""

    logoUrl: Optional[str] = Field(None, description="S3 URL of uploaded college logo")
    skipLogo: bool = Field(False, description="Skip logo upload")


class CMSCollegeDetailsRequest(BaseModel):
    """Request schema for college details (step 3)"""

    name: str = Field(
        ..., min_length=1, max_length=255, description="College/University full name"
    )
    shortName: str = Field(
        ..., min_length=1, max_length=50, description="Short name/code"
    )
    collegeReferenceId: str = Field(
        ..., min_length=1, max_length=100, description="College reference ID"
    )
    phoneNumber: str = Field(
        ...,
        pattern=r"^\+91[6-9]\d{9}$",
        description="College phone number in +91 format",
    )


class CMSAddressDetailsRequest(BaseModel):
    """Request schema for address details (step 5)"""

    area: str = Field(..., min_length=1, max_length=255, description="Area/locality")
    city: str = Field(..., min_length=1, max_length=100, description="City")
    district: str = Field(..., min_length=1, max_length=100, description="District")
    state: str = Field(..., min_length=1, max_length=100, description="State")
    pincode: str = Field(..., pattern=r"^\d{6}$", description="6-digit pincode")
    latitude: Optional[float] = Field(None, description="Latitude coordinates")
    longitude: Optional[float] = Field(None, description="Longitude coordinates")


# Removed CMSLoginRequest - now using combined sign-in flow with OTP


class CMSResetPasswordRequest(BaseModel):
    """Request schema for password reset (invited staff)"""

    newPassword: str = Field(..., min_length=8, description="New password")
    confirmPassword: str = Field(..., min_length=8, description="Password confirmation")

    @field_validator("confirmPassword")
    @classmethod
    def passwords_match(cls, v, info):
        if "newPassword" in info.data and v != info.data["newPassword"]:
            raise ValueError("Passwords do not match")
        return v


class CMSRefreshTokenRequest(BaseModel):
    """Request schema for refreshing access token"""

    refreshToken: str = Field(..., description="JWT refresh token")
    staffId: Optional[int] = Field(
        None, description="Staff ID for validation (optional)"
    )


# Response Schemas


class CMSTokenResponse(BaseModel):
    """Response schema for token-based responses"""

    accessToken: str = Field(..., description="JWT access token")
    refreshToken: str = Field(..., description="JWT refresh token")
    tokenType: str = Field(default="bearer", description="Token type")
    expiresIn: int = Field(..., description="Token expiry in seconds")


class CMSSigninResponse(BaseModel):
    """Response schema for sign-in operations"""

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    attemptsRemaining: Optional[int] = Field(None, description="Remaining OTP attempts")
    canResend: bool = Field(default=True, description="Whether OTP can be resent")
    staffExists: bool = Field(..., description="Whether staff member already exists")


class CMSVerifySigninResponse(BaseModel):
    """Response schema for verify sign-in (returns tokens for existing staff, temp token for new staff)"""

    success: bool = Field(..., description="Verification success status")
    message: str = Field(..., description="Response message")
    staffExists: bool = Field(..., description="Whether staff member already exists")
    # For existing staff (login)
    accessToken: Optional[str] = Field(
        None, description="JWT access token for existing staff"
    )
    refreshToken: Optional[str] = Field(
        None, description="JWT refresh token for existing staff"
    )
    tokenType: Optional[str] = Field(None, description="Token type")
    expiresIn: Optional[int] = Field(None, description="Token expiry in seconds")
    # For password reset flow
    requiresPasswordReset: Optional[bool] = Field(
        None, description="Whether staff must reset password"
    )
    # For new staff (registration)
    nextStep: Optional[str] = Field(
        None, description="Next step in registration for new staff"
    )
    tempToken: Optional[str] = Field(
        None, description="Temporary token for registration steps"
    )


class CMSRegistrationStepResponse(BaseModel):
    """Response schema for registration step completion"""

    success: bool = Field(..., description="Step completion status")
    message: str = Field(..., description="Response message")
    nextStep: Optional[str] = Field(None, description="Next step in registration")
    tempToken: Optional[str] = Field(None, description="Temporary token for next steps")


class StaffProfileResponse(BaseModel):
    """Response schema for staff profile"""

    staffId: int
    uuid: str
    email: str
    fullName: str
    # Note: phoneNumber is now on college, not staff
    cmsRole: str
    collegeId: Optional[int]
    departmentId: Optional[int]
    invitationStatus: str
    mustResetPassword: bool
    isHod: bool
    createdAt: datetime

    class Config:
        from_attributes = True


class CMSRefreshTokenResponse(BaseModel):
    """Response schema for token refresh"""

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    accessToken: str = Field(..., description="New JWT access token")
    tokenType: str = Field(default="bearer", description="Token type")
    expiresIn: int = Field(..., description="Token expiry in seconds")
    staff: StaffProfileResponse = Field(..., description="Updated staff data")


class CMSCollegeProfileResponse(BaseModel):
    """Response schema for CMS college profile"""

    id: int
    uuid: str
    name: str
    shortName: str
    collegeReferenceId: str
    logoUrl: Optional[str]
    fullAddress: str
    principalStaffId: Optional[int]
    createdAt: datetime

    class Config:
        from_attributes = True


class CMSErrorResponse(BaseModel):
    """Response schema for error responses"""

    error: bool = Field(default=True, description="Error indicator")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
    code: Optional[str] = Field(None, description="Error code")


class CMSCheckUserRequest(BaseModel):
    """Request schema for checking user status"""

    email: EmailStr = Field(..., description="Email address to check")


class CMSCheckUserResponse(BaseModel):
    """Response schema for user status check"""

    success: bool = Field(..., description="Response success indicator")
    exists: bool = Field(..., description="Whether user exists")
    hasPassword: bool = Field(..., description="Whether user has set a password")
    requiresOtp: bool = Field(..., description="Whether OTP verification is required")
    message: str = Field(..., description="Status message")


class CMSPasswordLoginRequest(BaseModel):
    """Request schema for password-based login"""

    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Password")


class CMSPasswordLoginResponse(BaseModel):
    """Response schema for password-based login"""

    success: bool = Field(..., description="Login success indicator")
    message: str = Field(..., description="Response message")
    accessToken: Optional[str] = Field(None, description="JWT access token")
    refreshToken: Optional[str] = Field(None, description="JWT refresh token")
    tokenType: str = Field(default="bearer", description="Token type")
    expiresIn: int = Field(..., description="Token expiration time in seconds")


# New separate flow schemas

class CMSLoginRequest(BaseModel):
    """Request schema for separate login flow"""

    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Password")


class CMSLoginResponse(BaseModel):
    """Response schema for separate login flow"""

    success: bool = Field(..., description="Login success indicator")
    message: str = Field(..., description="Response message")
    accessToken: str = Field(..., description="JWT access token")
    refreshToken: str = Field(..., description="JWT refresh token")
    tokenType: str = Field(default="bearer", description="Token type")
    expiresIn: int = Field(..., description="Token expiration time in seconds")


class CMSSignupRequest(BaseModel):
    """Request schema for separate signup flow (initial email)"""

    email: EmailStr = Field(..., description="Email address for registration")


class CMSSignupResponse(BaseModel):
    """Response schema for signup OTP sending"""

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    attemptsRemaining: int = Field(..., description="Remaining OTP attempts")
    canResend: bool = Field(default=True, description="Whether OTP can be resent")


class CMSVerifySignupRequest(BaseModel):
    """Request schema for verifying signup OTP"""

    email: EmailStr = Field(..., description="Email address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP")


class CMSVerifySignupResponse(BaseModel):
    """Response schema for signup OTP verification"""

    success: bool = Field(..., description="Verification success status")
    message: str = Field(..., description="Response message")
    nextStep: str = Field(..., description="Next step in registration process")
    tempToken: Optional[str] = Field(
        None, description="Temporary token for registration steps"
    )


class CMSSetPasswordRequest(BaseModel):
    """Request schema for profile setup in signup flow (step 3) - password, full name, and contact number"""
    
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=8, description="Password")
    fullName: str = Field(..., min_length=1, max_length=200, description="Full name (username)")
    contactNumber: str = Field(..., pattern=r"^(\+91)?[6-9]\d{9}$", description="Contact number in Indian format")


class CMSResetPasswordRequest(BaseModel):
    """Request schema for resetting password with OTP"""
    
    email: EmailStr = Field(..., description="Email address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP")
    newPassword: str = Field(..., min_length=8, description="New password")


class CMSResetPasswordAuthenticatedRequest(BaseModel):
    """Request schema for authenticated password reset"""
    
    newPassword: str = Field(..., min_length=8, description="New password")
    confirmPassword: str = Field(..., min_length=8, description="Password confirmation")

    @field_validator("confirmPassword")
    @classmethod
    def passwords_match(cls, v, info):
        if "newPassword" in info.data and v != info.data["newPassword"]:
            raise ValueError("Passwords do not match")
        return v
