"""
College Contact Management Schemas
Schemas for managing college contact information and staff assignments
"""

from pydantic import BaseModel, Field
from typing import Optional
from app.core.utils import CamelCaseModel


class CollegeContactResponse(CamelCaseModel):
    """Response schema for college contact information"""
    contact_number: Optional[str] = Field(None, description="College contact number")
    contact_staff_id: Optional[str] = Field(None, description="Contact staff ID (UUID)")
    contact_staff_name: Optional[str] = Field(None, description="Contact staff full name")
    contact_staff_email: Optional[str] = Field(None, description="Contact staff email")


class UpdateCollegeContactRequest(CamelCaseModel):
    """Request schema for updating college contact information"""
    contact_staff_id: str = Field(..., description="UUID of staff member to use as college contact")


class CollegeContactActionResponse(CamelCaseModel):
    """Response schema for college contact update actions"""
    success: bool = Field(..., description="Action success status")
    message: str = Field(..., description="Action result message")
    contact_number: Optional[str] = Field(None, description="Updated contact number")
    contact_staff_name: Optional[str] = Field(None, description="Contact staff name")