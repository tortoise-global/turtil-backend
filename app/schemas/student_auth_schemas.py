"""
Student Authentication Schemas - Phone-Based
Pydantic schemas for student mobile app phone-based authentication flow
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime


# ==================== PHONE-BASED SIGNIN FLOW SCHEMAS ====================

class StudentSigninRequest(BaseModel):
    """Student signin request - Step 1: Phone number OTP"""
    phoneNumber: str = Field(..., description="Student phone number")
    
    @validator('phoneNumber')
    def validate_phone_number(cls, v):
        if not v.strip():
            raise ValueError('Phone number cannot be empty')
        
        # Remove spaces, dashes, parentheses for validation
        cleaned = v.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        
        # Basic validation: 10-15 digits, optionally starting with +
        if cleaned.startswith("+"):
            cleaned = cleaned[1:]
        
        if not cleaned.isdigit() or not (10 <= len(cleaned) <= 15):
            raise ValueError('Invalid phone number format')
        
        return v.strip()

class StudentSigninResponse(BaseModel):
    """Student signin response - OTP sent"""
    success: bool = True
    message: str = "OTP sent successfully to your phone number."
    phoneNumber: str = Field(..., description="Formatted phone number")
    otpExpiresIn: int = 300  # 5 minutes


class StudentVerifyOTPRequest(BaseModel):
    """Student OTP verification - Step 2: Verify OTP and get tokens"""
    phoneNumber: str = Field(..., description="Student phone number")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP")
    expoPushToken: str = Field(..., description="Expo push notification token for mobile app")

class StudentDeviceInfo(BaseModel):
    """Student device information for session tracking"""
    browser: str = Field(..., description="Browser name")
    os: str = Field(..., description="Operating system")
    device: str = Field(..., description="Device type")

class StudentVerifyOTPResponse(BaseModel):
    """Student OTP verification response - Direct authentication with tokens"""
    success: bool = True
    message: str = "Authentication successful"
    accessToken: str = Field(..., description="JWT access token for API requests")
    refreshToken: str = Field(..., description="JWT refresh token")
    tokenType: str = "bearer"
    expiresIn: int = Field(..., description="Access token expiration in seconds")
    deviceInfo: StudentDeviceInfo
    student: Dict[str, Any] = Field(..., description="Student profile information")
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
    phoneNumber: str = Field(..., description="Student phone number")
    email: Optional[str] = Field(None, description="Student email (optional)")
    fullName: Optional[str] = Field(None, description="Student full name")
    gender: Optional[str] = Field(None, description="Student gender")
    isActive: bool = Field(..., description="Account active status")
    isVerified: bool = Field(..., description="Phone verification status")
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
    email: Optional[str] = Field(None, description="Updated email address")
    
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


# ==================== USER DETAILS STEP SCHEMAS ====================

class StudentUserDetailsRequest(BaseModel):
    """Student user details request - Final registration step"""
    fullName: str = Field(..., min_length=2, max_length=200, description="Student full name")
    gender: str = Field(..., description="Student gender")
    rollNumber: str = Field(..., min_length=1, max_length=50, description="Student roll number")
    email: Optional[str] = Field(None, description="Student email (optional)")
    
    @validator('fullName')
    def validate_full_name(cls, v):
        if not v.strip():
            raise ValueError('Full name cannot be empty')
        return ' '.join(v.strip().split())
    
    @validator('gender')
    def validate_gender(cls, v):
        allowed_genders = ['male', 'female', 'other']
        if v.lower() not in allowed_genders:
            raise ValueError(f'Gender must be one of: {", ".join(allowed_genders)}')
        return v.lower()
    
    @validator('rollNumber')
    def validate_roll_number(cls, v):
        if not v.strip():
            raise ValueError('Roll number cannot be empty')
        return v.strip().upper()

class StudentUserDetailsResponse(BaseModel):
    """Student user details response - Registration completed"""
    success: bool = True
    message: str = "Registration completed successfully. Waiting for college approval."
    studentProfile: Dict[str, Any] = Field(..., description="Complete student profile")
    admissionNumber: str = Field(..., description="Generated admission number")
    nextStep: str = "approval_pending"


# ==================== BACKWARD COMPATIBILITY (TO BE REMOVED) ====================
# Keep some old schemas temporarily to avoid breaking existing code

StudentSignupRequest = StudentSigninRequest  # Alias for backward compatibility
StudentSignupResponse = StudentSigninResponse  # Alias for backward compatibility