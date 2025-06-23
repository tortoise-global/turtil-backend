"""
Session Schemas
All session-related request/response schemas for authentication and session management
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any, List
from app.core.utils import CamelCaseModel


# Request Schemas

class SigninRequest(CamelCaseModel):
    """Request schema for user sign-in (password-based)"""
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Password")


class RefreshTokenRequest(CamelCaseModel):
    """Request schema for token refresh"""
    refresh_token: str = Field(..., description="Refresh token")


# Device and Session Info Schemas

class DeviceInfo(CamelCaseModel):
    """Device information schema"""
    browser: str = Field(..., description="Browser name")
    os: str = Field(..., description="Operating system")
    device: str = Field(..., description="Device type")


class SessionInfo(CamelCaseModel):
    """Session information schema"""
    session_id: str = Field(..., description="Session ID")
    device: str = Field(..., description="Device type")
    browser: str = Field(..., description="Browser name")
    os: str = Field(..., description="Operating system")
    created_at: int = Field(..., description="Session creation timestamp")
    last_used: int = Field(..., description="Last used timestamp")
    ip_address: Optional[str] = Field(None, description="IP address")
    is_current: bool = Field(..., description="Whether this is the current session")


# Response Schemas

class SigninResponse(CamelCaseModel):
    """Response schema for successful sign-in - simplified for optimal flow"""
    refresh_token: str = Field(..., description="JWT refresh token for token rotation")
    device_info: DeviceInfo = Field(..., description="Device information")
    user: Optional[Dict[str, Any]] = Field(None, description="User information (optional)")


class RefreshTokenResponse(CamelCaseModel):
    """Response schema for token refresh"""
    access_token: str = Field(..., description="New JWT access token")
    refresh_token: str = Field(..., description="New JWT refresh token")
    token_type: str = Field(..., description="Token type (bearer)")
    expires_in: int = Field(..., description="Token expiry time in seconds")


class SessionListResponse(CamelCaseModel):
    """Response schema for listing user sessions"""
    sessions: List[SessionInfo] = Field(..., description="List of active sessions")
    total_count: int = Field(..., description="Total number of sessions")


class CurrentSessionResponse(CamelCaseModel):
    """Response schema for current session information"""
    session_id: str = Field(..., description="Current session ID")
    device_info: DeviceInfo = Field(..., description="Device information")
    created_at: int = Field(..., description="Session creation timestamp")
    last_used: int = Field(..., description="Last used timestamp")
    ip_address: Optional[str] = Field(None, description="IP address")


class LogoutResponse(CamelCaseModel):
    """Response schema for logout operations"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Status message")
    sessions_invalidated: int = Field(..., description="Number of sessions invalidated")


# Legacy compatibility schemas (for backwards compatibility during transition)

class LegacyLoginRequest(CamelCaseModel):
    """Legacy login request schema for backwards compatibility"""
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Password")


class LegacyLoginResponse(CamelCaseModel):
    """Legacy login response schema for backwards compatibility"""
    success: bool = Field(..., description="Login success status")
    message: str = Field(..., description="Status message")
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(..., description="Token type")
    expires_in: int = Field(..., description="Token expiry time in seconds")