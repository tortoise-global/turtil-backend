from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime


class CMSSigninRequest(BaseModel):
    """Request schema for combined sign-in flow (sends OTP for both new and existing users)"""
    email: EmailStr = Field(..., description="College/University email address")


class CMSVerifySigninRequest(BaseModel):
    """Request schema for verifying sign-in OTP (handles both login and registration)"""
    email: EmailStr = Field(..., description="Email address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP")


class CMSPasswordSetupRequest(BaseModel):
    """Request schema for password setup (step 2)"""
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=8, description="Password")
    confirmPassword: str = Field(..., min_length=8, description="Password confirmation")
    
    @validator('confirmPassword')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v


class CMSPersonalDetailsRequest(BaseModel):
    """Request schema for personal details (step 3)"""
    firstName: str = Field(..., min_length=1, max_length=100, description="First name")
    lastName: str = Field(..., min_length=1, max_length=100, description="Last name")
    phoneNumber: str = Field(..., pattern=r'^\+91[6-9]\d{9}$', description="Phone number in +91 format")
    marketingConsent: bool = Field(default=False, description="Marketing consent")
    termsAccepted: bool = Field(..., description="Terms of service acceptance")
    
    @validator('termsAccepted')
    def terms_must_be_accepted(cls, v):
        if not v:
            raise ValueError('Terms of service must be accepted')
        return v


class CMSCollegeLogoUploadRequest(BaseModel):
    """Request schema for college logo upload (step 3.5)"""
    skip: bool = Field(default=False, description="Skip logo upload")
    

class CMSCollegeDetailsRequest(BaseModel):
    """Request schema for college details (step 4)"""
    name: str = Field(..., min_length=1, max_length=255, description="College/University full name")
    shortName: str = Field(..., min_length=1, max_length=50, description="Short name/code")
    collegeReferenceId: str = Field(..., min_length=1, max_length=100, description="College reference ID")


class CMSAddressDetailsRequest(BaseModel):
    """Request schema for address details (step 5)"""
    area: str = Field(..., min_length=1, max_length=255, description="Area/locality")
    city: str = Field(..., min_length=1, max_length=100, description="City")
    district: str = Field(..., min_length=1, max_length=100, description="District")
    state: str = Field(..., min_length=1, max_length=100, description="State")
    pincode: str = Field(..., pattern=r'^\d{6}$', description="6-digit pincode")
    latitude: Optional[float] = Field(None, description="Latitude coordinates")
    longitude: Optional[float] = Field(None, description="Longitude coordinates")


# Removed CMSLoginRequest - now using combined sign-in flow with OTP


class CMSResetPasswordRequest(BaseModel):
    """Request schema for password reset (invited users)"""
    newPassword: str = Field(..., min_length=8, description="New password")
    confirmPassword: str = Field(..., min_length=8, description="Password confirmation")
    
    @validator('confirmPassword')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['newPassword']:
            raise ValueError('Passwords do not match')
        return v


class CMSRefreshTokenRequest(BaseModel):
    """Request schema for refreshing access token"""
    refreshToken: str = Field(..., description="JWT refresh token")
    cmsUserId: Optional[int] = Field(None, description="User ID for validation (optional)")


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
    userExists: bool = Field(..., description="Whether user already exists")


class CMSVerifySigninResponse(BaseModel):
    """Response schema for verify sign-in (returns tokens for existing users, temp token for new users)"""
    success: bool = Field(..., description="Verification success status")
    message: str = Field(..., description="Response message")
    userExists: bool = Field(..., description="Whether user already exists")
    # For existing users (login)
    accessToken: Optional[str] = Field(None, description="JWT access token for existing users")
    refreshToken: Optional[str] = Field(None, description="JWT refresh token for existing users")
    tokenType: Optional[str] = Field(None, description="Token type")
    expiresIn: Optional[int] = Field(None, description="Token expiry in seconds")
    # For password reset flow
    requiresPasswordReset: Optional[bool] = Field(None, description="Whether user must reset password")
    # For new users (registration)
    nextStep: Optional[str] = Field(None, description="Next step in registration for new users")
    tempToken: Optional[str] = Field(None, description="Temporary token for registration steps")


class CMSRegistrationStepResponse(BaseModel):
    """Response schema for registration step completion"""
    success: bool = Field(..., description="Step completion status")
    message: str = Field(..., description="Response message")
    nextStep: Optional[str] = Field(None, description="Next step in registration")
    tempToken: Optional[str] = Field(None, description="Temporary token for next steps")


class CMSUserProfileResponse(BaseModel):
    """Response schema for CMS user profile"""
    cmsUserId: int
    uuid: str
    email: str
    firstName: str
    lastName: str
    fullName: str
    phoneNumber: Optional[str]
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
    user: CMSUserProfileResponse = Field(..., description="Updated user data")


class CMSCollegeProfileResponse(BaseModel):
    """Response schema for CMS college profile"""
    id: int
    uuid: str
    name: str
    shortName: str
    collegeReferenceId: str
    logoUrl: Optional[str]
    fullAddress: str
    principalCmsUserId: Optional[int]
    createdAt: datetime
    
    class Config:
        from_attributes = True


class CMSErrorResponse(BaseModel):
    """Response schema for error responses"""
    error: bool = Field(default=True, description="Error indicator")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    code: Optional[str] = Field(None, description="Error code")