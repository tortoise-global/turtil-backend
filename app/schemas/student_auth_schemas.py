"""
Student Authentication Schemas
Pydantic schemas for student mobile app authentication flow
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime


# ==================== SIGNUP FLOW SCHEMAS ====================

class StudentSignupRequest(BaseModel):
    """Student signup request - Step 1: Email OTP"""
    email: EmailStr = Field(..., description="Student email address")

class StudentSignupResponse(BaseModel):
    """Student signup response - OTP sent"""
    success: bool = True
    message: str = "OTP sent successfully. Please check your email to continue registration."
    attemptsRemaining: int = 3


class StudentVerifyOTPRequest(BaseModel):
    """Student OTP verification - Step 2: Verify OTP"""
    email: EmailStr = Field(..., description="Student email address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP")

class StudentVerifyOTPResponse(BaseModel):
    """Student OTP verification response - Temp token for profile setup"""
    success: bool = True
    message: str = "Email verified successfully. Please set up your profile to continue."
    nextStep: str = "profile_setup"
    tempToken: str = Field(..., description="Temporary token for profile setup (5 minutes)")


class StudentSetupProfileRequest(BaseModel):
    """Student profile setup - Step 3: Set password and basic info"""
    tempToken: str = Field(..., description="Temporary token from OTP verification")
    fullName: str = Field(..., min_length=2, max_length=200, description="Student full name")
    password: str = Field(..., min_length=8, max_length=128, description="Strong password")
    
    @validator('fullName')
    def validate_full_name(cls, v):
        if not v.strip():
            raise ValueError('Full name cannot be empty')
        # Remove extra spaces and ensure proper format
        return ' '.join(v.strip().split())
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class StudentSetupProfileResponse(BaseModel):
    """Student profile setup response - Account created, ready for registration"""
    success: bool = True
    message: str = "Account created successfully. Please complete your academic registration."
    nextStep: str = "academic_registration"


# ==================== SIGNIN FLOW SCHEMAS ====================

class StudentSigninRequest(BaseModel):
    """Student signin request - Single device authentication"""
    email: EmailStr = Field(..., description="Student email address")
    password: str = Field(..., description="Student password")
    expoPushToken: str = Field(..., description="Expo push notification token for mobile app")

class StudentDeviceInfo(BaseModel):
    """Student device information for session tracking"""
    browser: str = Field(..., description="Browser name")
    os: str = Field(..., description="Operating system")
    device: str = Field(..., description="Device type")

class StudentSigninResponse(BaseModel):
    """Student signin response - JWT tokens and profile"""
    accessToken: str = Field(..., description="JWT access token for API requests")
    refreshToken: str = Field(..., description="JWT refresh token")
    tokenType: str = "bearer"
    expiresIn: int = Field(..., description="Access token expiration in seconds")
    deviceInfo: StudentDeviceInfo
    student: Dict[str, Any] = Field(..., description="Student profile information")
    message: str = "Sign in successful"
    registrationRequired: bool = Field(..., description="True if student needs to complete academic registration")


# ==================== TOKEN MANAGEMENT SCHEMAS ====================

class StudentRefreshTokenRequest(BaseModel):
    """Student token refresh request"""
    refreshToken: str = Field(..., description="Valid refresh token")

class StudentRefreshTokenResponse(BaseModel):
    """Student token refresh response - New tokens with rotation"""
    accessToken: str = Field(..., description="New JWT access token")
    refreshToken: str = Field(..., description="New JWT refresh token (rotated)")
    tokenType: str = "bearer"
    expiresIn: int = Field(..., description="Access token expiration in seconds")


# ==================== SESSION MANAGEMENT SCHEMAS ====================

class StudentCurrentSessionResponse(BaseModel):
    """Student current session information"""
    sessionId: str = Field(..., description="Current session ID")
    deviceInfo: StudentDeviceInfo
    createdAt: int = Field(..., description="Session creation timestamp")
    lastUsed: int = Field(..., description="Last activity timestamp")
    ipAddress: Optional[str] = Field(None, description="IP address")

class StudentLogoutResponse(BaseModel):
    """Student logout response"""
    success: bool = True
    message: str = "Successfully signed out"


# ==================== REGISTRATION STATUS SCHEMAS ====================

class StudentRegistrationProgress(BaseModel):
    """Student academic registration progress"""
    currentStep: str = Field(..., description="Current registration step")
    progressPercentage: int = Field(..., ge=0, le=100, description="Progress percentage")
    details: Dict[str, Any] = Field(..., description="Registration details")
    canAccessApp: bool = Field(..., description="Can access main app features")

class StudentRegistrationStatusResponse(BaseModel):
    """Student registration status response"""
    registrationCompleted: bool = Field(..., description="Registration completion status")
    progress: StudentRegistrationProgress


# ==================== PROFILE SCHEMAS ====================

class StudentProfileResponse(BaseModel):
    """Student profile response"""
    studentId: str = Field(..., description="Student UUID")
    email: EmailStr = Field(..., description="Student email")
    fullName: str = Field(..., description="Student full name")
    isActive: bool = Field(..., description="Account active status")
    isVerified: bool = Field(..., description="Email verification status")
    registrationCompleted: bool = Field(..., description="Academic registration status")
    collegeId: Optional[str] = Field(None, description="Assigned college ID")
    sectionId: Optional[str] = Field(None, description="Assigned section ID")
    admissionNumber: Optional[str] = Field(None, description="Student admission number")
    rollNumber: Optional[str] = Field(None, description="Student roll number")
    lastLoginAt: Optional[datetime] = Field(None, description="Last login timestamp")
    loginCount: int = Field(..., description="Total login count")
    createdAt: datetime = Field(..., description="Account creation timestamp")

class StudentUpdateProfileRequest(BaseModel):
    """Student profile update request"""
    fullName: Optional[str] = Field(None, min_length=2, max_length=200, description="Updated full name")
    
    @validator('fullName')
    def validate_full_name(cls, v):
        if v and not v.strip():
            raise ValueError('Full name cannot be empty')
        if v:
            return ' '.join(v.strip().split())
        return v


# ==================== ERROR SCHEMAS ====================

class StudentAuthErrorResponse(BaseModel):
    """Student authentication error response"""
    statusCode: int = Field(..., description="HTTP status code")
    message: str = Field(..., description="Error message")
    success: bool = False
    timestamp: float = Field(..., description="Error timestamp")
    attemptsRemaining: Optional[int] = Field(None, description="Remaining OTP attempts")


# ==================== PASSWORD RESET SCHEMAS ====================

class StudentForgotPasswordRequest(BaseModel):
    """Student forgot password request"""
    email: EmailStr = Field(..., description="Student email address")

class StudentForgotPasswordResponse(BaseModel):
    """Student forgot password response"""
    success: bool = True
    message: str = "Password reset OTP sent successfully. Please check your email."
    attemptsRemaining: int = 3
    studentExists: bool = True

class StudentResetPasswordRequest(BaseModel):
    """Student password reset request"""
    tempToken: str = Field(..., description="Temporary token from OTP verification")
    newPassword: str = Field(..., min_length=8, max_length=128, description="New password")
    
    @validator('newPassword')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class StudentResetPasswordResponse(BaseModel):
    """Student password reset response"""
    success: bool = True
    message: str = "Password reset successful. Please sign in with your new password."