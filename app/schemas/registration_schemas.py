"""
Registration Schemas
College registration and setup schemas
"""

from pydantic import BaseModel, Field
from typing import Optional
from app.core.utils import CamelCaseModel


# College setup schemas

class CollegeLogoRequest(CamelCaseModel):
    """Request schema for college logo upload (step 2)"""
    logo_url: Optional[str] = Field(None, description="S3 URL of uploaded college logo")
    skip_logo: bool = Field(False, description="Skip logo upload")


class CollegeDetailsRequest(CamelCaseModel):
    """Request schema for college details (step 3)"""
    name: str = Field(..., min_length=1, max_length=255, description="College/University full name")
    short_name: str = Field(..., min_length=1, max_length=50, description="Short name/code")
    college_reference_id: str = Field(..., min_length=1, max_length=100, description="College reference ID")
    # phone_number removed - automatically uses initial staff's contact number


class AddressDetailsRequest(CamelCaseModel):
    """Request schema for address details (step 5)"""
    area: str = Field(..., min_length=1, max_length=255, description="Area/locality")
    city: str = Field(..., min_length=1, max_length=100, description="City")
    district: str = Field(..., min_length=1, max_length=100, description="District")
    state: str = Field(..., min_length=1, max_length=100, description="State")
    pincode: str = Field(..., pattern=r"^\d{6}$", description="6-digit pincode")
    latitude: Optional[float] = Field(None, description="Latitude coordinates")
    longitude: Optional[float] = Field(None, description="Longitude coordinates")


# Response schemas

class RegistrationStepResponse(CamelCaseModel):
    """Response schema for registration step completion"""
    success: bool = Field(..., description="Step completion success status")
    message: str = Field(..., description="Step completion message")
    next_step: Optional[str] = Field(None, description="Next step in registration process")
    completion_percentage: int = Field(..., description="Overall registration completion percentage")


class TokenResponse(CamelCaseModel):
    """Response schema for token-based operations"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Status message")
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(..., description="Token type (bearer)")
    expires_in: int = Field(..., description="Token expiry time in seconds")