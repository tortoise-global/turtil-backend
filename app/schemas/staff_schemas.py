"""
Staff Schemas
All staff-related request/response schemas for staff management
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from app.core.utils import CamelCaseModel


# Staff management schemas

class StaffCreateRequest(CamelCaseModel):
    """Admin staff creation request schema"""
    email: EmailStr = Field(..., description="Staff email address")
    password: str = Field(..., min_length=8, description="Staff password")
    full_name: str = Field(..., min_length=1, max_length=200, description="Staff full name")
    is_active: bool = Field(default=True, description="Staff active status")
    is_verified: bool = Field(default=False, description="Email verification status")
    is_superstaff: bool = Field(default=False, description="Superstaff status")


class StaffUpdateRequest(CamelCaseModel):
    """Staff update request schema"""
    full_name: Optional[str] = Field(None, min_length=1, max_length=200, description="Staff full name")
    is_active: Optional[bool] = Field(None, description="Staff active status")
    is_verified: Optional[bool] = Field(None, description="Email verification status")


class AdminStaffUpdateRequest(CamelCaseModel):
    """Admin staff update request schema (includes more fields)"""
    full_name: Optional[str] = Field(None, min_length=1, max_length=200, description="Staff full name")
    email: Optional[EmailStr] = Field(None, description="Staff email address")
    is_active: Optional[bool] = Field(None, description="Staff active status")
    is_verified: Optional[bool] = Field(None, description="Email verification status")
    is_superstaff: Optional[bool] = Field(None, description="Superstaff status")


# Staff invitation and assignment schemas

class InviteStaffRequest(CamelCaseModel):
    """Request schema for inviting a new staff member"""
    email: EmailStr = Field(..., description="Staff member's college/university email address")
    full_name: str = Field(..., min_length=1, max_length=200, description="Staff member's full name")
    contact_number: str = Field(..., pattern=r"^(\+[1-9]\d{0,3})?[1-9]\d{6,14}$", description="Staff member's contact number in international format")
    cms_role: str = Field(default="staff", description="CMS role (principal, admin, hod, staff)")
    department_id: Optional[str] = Field(None, description="Department ID (UUID) to assign staff member to")

    @field_validator("cms_role")
    @classmethod
    def validate_cms_role(cls, v):
        allowed_roles = ["principal", "admin", "hod", "staff"]
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of: {', '.join(allowed_roles)}")
        return v


class InviteStaffResponse(CamelCaseModel):
    """Response schema for staff invitation"""
    success: bool = Field(..., description="Invitation success status")
    message: str = Field(..., description="Invitation status message")
    staff_id: Optional[int] = Field(None, description="Created staff ID")
    email: EmailStr = Field(..., description="Invited staff email")
    temporary_password: str = Field(..., description="Generated temporary password")


# Assignment and role update schemas removed - now handled by comprehensive update-details endpoint


class UpdateStaffDetailsRequest(CamelCaseModel):
    """Request schema for updating comprehensive staff details (Principal/Admin only)"""
    full_name: Optional[str] = Field(None, min_length=1, max_length=200, description="Staff full name")
    email: Optional[EmailStr] = Field(None, description="Staff email address")
    contact_number: Optional[str] = Field(None, pattern=r"^(\+[1-9]\d{0,3})?[1-9]\d{6,14}$", description="Staff contact number in international format")
    cms_role: Optional[str] = Field(None, description="CMS role (principal, admin, hod, staff)")
    department_id: Optional[str] = Field(None, description="Department ID (UUID) to assign staff member to")

    @field_validator("cms_role")
    @classmethod
    def validate_cms_role(cls, v):
        if v is not None:
            allowed_roles = ["principal", "admin", "hod", "staff"]
            if v not in allowed_roles:
                raise ValueError(f"Role must be one of: {', '.join(allowed_roles)}")
        return v


# Username update and contact management schemas removed - now handled by comprehensive update-details endpoint


# Staff response schemas

class StaffResponse(CamelCaseModel):
    """Response schema for staff information (used in paginated lists)"""
    staff_id: str = Field(..., description="Staff ID (UUID)")
    uuid: str = Field(..., description="Staff UUID")
    email: EmailStr = Field(..., description="Staff email")
    full_name: str = Field(..., description="Full name")
    contact_number: str = Field(..., description="Contact number")
    is_active: bool = Field(..., description="Account active status")
    is_verified: bool = Field(..., description="Email verification status")
    cms_role: str = Field(..., description="CMS role (principal, admin, hod, staff)")
    college_id: Optional[str] = Field(None, description="College ID (UUID)")
    division_id: Optional[str] = Field(None, description="Division ID (UUID)")
    division_name: Optional[str] = Field(None, description="Division name")
    department_id: Optional[str] = Field(None, description="Department ID (UUID)")
    department_name: Optional[str] = Field(None, description="Department name")
    invitation_status: str = Field(..., description="Invitation status (pending, accepted, active)")
    temporary_password: bool = Field(..., description="Has temporary password")
    must_reset_password: bool = Field(..., description="Must reset password on next login")
    invited_by_staff_id: Optional[str] = Field(None, description="ID of staff member who sent invitation (UUID)")
    is_hod: bool = Field(..., description="Head of Department status")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class StaffDetailsResponse(CamelCaseModel):
    """Detailed staff information response schema - CMS focused"""
    # Identity
    staff_id: str = Field(..., description="Staff ID (UUID)")
    uuid: str = Field(..., description="Staff UUID")
    email: EmailStr = Field(..., description="Staff email")
    full_name: str = Field(..., description="Full name")
    contact_number: str = Field(..., description="Contact number")
    
    # CMS Role & Assignment
    cms_role: str = Field(..., description="CMS role (principal, admin, hod, staff)")
    college_id: Optional[str] = Field(None, description="College ID (UUID)")
    department_id: Optional[str] = Field(None, description="Department ID (UUID)")
    is_hod: bool = Field(..., description="Head of Department status")
    
    # Password Management (simplified)
    requires_password_reset: bool = Field(..., description="Whether staff needs to reset password on next login")
    
    # Audit
    invited_by_staff_id: Optional[str] = Field(None, description="Invited by staff ID (UUID)")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")


class StaffActionResponse(CamelCaseModel):
    """Generic response schema for staff management actions"""
    success: bool = Field(..., description="Action success status")
    message: str = Field(..., description="Action result message")
    staff_id: int = Field(..., description="Affected staff ID")


class UpdateStaffDetailsResponse(CamelCaseModel):
    """Response schema for staff details update"""
    success: bool = Field(..., description="Update success status")
    message: str = Field(..., description="Update result message")
    staff_id: str = Field(..., description="Updated staff ID (UUID)")
    updated_fields: List[str] = Field(..., description="List of fields that were updated")


# Old username update response removed - now handled by comprehensive update-details response


# List and query schemas

class StaffListQuery(CamelCaseModel):
    """Query parameters for staff list endpoint"""
    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=10, ge=1, le=100, description="Page size")
    search: Optional[str] = Field(None, description="Search term for email/name")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    is_verified: Optional[bool] = Field(None, description="Filter by verification status")
    is_superstaff: Optional[bool] = Field(None, description="Filter by superstaff status")
    sort_by: str = Field(default="created_at", description="Sort field")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$", description="Sort order")


class StaffListResponse(CamelCaseModel):
    """Staff list response schema with pagination"""
    staff: List[StaffResponse] = Field(..., description="List of staff members")
    total: int = Field(..., description="Total number of staff members")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")


class StaffStatsResponse(CamelCaseModel):
    """Staff statistics response schema"""
    total_staff: int = Field(..., description="Total number of staff members")
    active_staff: int = Field(..., description="Number of active staff members")
    verified_staff: int = Field(..., description="Number of verified staff members")
    superstaff: int = Field(..., description="Number of superstaff")
    new_staff_this_month: int = Field(..., description="New staff this month")
    new_staff_this_week: int = Field(..., description="New staff this week")


class StaffProfileResponse(CamelCaseModel):
    """Staff profile response schema"""
    staff: StaffResponse = Field(..., description="Staff information")
    profile_completion: float = Field(..., description="Profile completion percentage")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")


class StaffActivityResponse(CamelCaseModel):
    """Staff activity response schema"""
    staff_id: int = Field(..., description="Staff ID")
    login_history: List[dict] = Field(..., description="Recent login history")
    activity_summary: dict = Field(..., description="Activity summary")
    last_seen: Optional[datetime] = Field(None, description="Last seen timestamp")


# Bulk operations schemas

class BulkStaffActionRequest(CamelCaseModel):
    """Bulk staff action request schema"""
    staff_ids: List[int] = Field(..., min_items=1, description="List of staff IDs")
    action: str = Field(..., pattern="^(activate|deactivate|verify|unverify|delete)$", description="Action to perform")


class BulkStaffActionResponse(CamelCaseModel):
    """Bulk staff action response schema"""
    message: str = Field(..., description="Response message")
    success: bool = Field(..., description="Operation success status")
    affected_staff: int = Field(..., description="Number of affected staff members")
    failed_staff: List[int] = Field(default=[], description="List of staff IDs that failed")


# Staff preferences schemas

class StaffPreferencesRequest(CamelCaseModel):
    """Staff preferences update request schema"""
    email_notifications: bool = Field(default=True, description="Email notification preference")
    theme: str = Field(default="light", pattern="^(light|dark|auto)$", description="UI theme preference")
    language: str = Field(default="en", description="Language preference")
    timezone: str = Field(default="UTC", description="Timezone preference")


class StaffPreferencesResponse(CamelCaseModel):
    """Staff preferences response schema"""
    staff_id: int = Field(..., description="Staff ID")
    email_notifications: bool = Field(..., description="Email notification preference")
    theme: str = Field(..., description="UI theme preference")
    language: str = Field(..., description="Language preference")
    timezone: str = Field(..., description="Timezone preference")
    updated_at: datetime = Field(..., description="Last update timestamp")