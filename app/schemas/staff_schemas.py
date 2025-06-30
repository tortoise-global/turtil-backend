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


class InviteStaffResponse(CamelCaseModel):
    """Response schema for staff invitation"""
    success: bool = Field(..., description="Invitation success status")
    message: str = Field(..., description="Invitation status message")
    staff_id: Optional[int] = Field(None, description="Created staff ID")
    email: EmailStr = Field(..., description="Invited staff email")
    temporary_password: str = Field(..., description="Generated temporary password")


class AssignDepartmentRequest(CamelCaseModel):
    """Request schema for assigning staff member to department"""
    department_id: int = Field(..., description="Department ID to assign staff member to")


class UpdateStaffRoleRequest(CamelCaseModel):
    """Request schema for updating staff role"""
    role: str = Field(..., description="New CMS role")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        allowed_roles = ["principal", "college_admin", "hod", "staff"]
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of: {', '.join(allowed_roles)}")
        return v


class UpdateUsernameRequest(CamelCaseModel):
    """Request schema for updating staff username (full_name)"""
    full_name: str = Field(..., min_length=1, max_length=200, description="Full name (username)")


# Contact management schemas

class UpdateContactRequest(CamelCaseModel):
    """Request schema for updating college contact information"""
    contact_number: str = Field(..., pattern=r"^(\+91)?[6-9]\d{9}$", description="Contact number in Indian format")
    contact_staff_id: str = Field(..., description="Staff ID (UUID) who will be the primary contact")


class UpdateContactResponse(CamelCaseModel):
    """Response schema for contact information update"""
    success: bool = Field(..., description="Update success status")
    message: str = Field(..., description="Update status message")
    contact_number: str = Field(..., description="Updated contact number")
    contact_staff_id: str = Field(..., description="Updated contact staff ID (UUID)")


class ContactInfoResponse(CamelCaseModel):
    """Response schema for getting current contact information"""
    contact_number: Optional[str] = Field(None, description="Current contact number")
    contact_staff_id: Optional[str] = Field(None, description="Current contact staff ID (UUID)")
    contact_staff_name: Optional[str] = Field(None, description="Contact staff full name")
    contact_staff_email: Optional[str] = Field(None, description="Contact staff email")


# Staff response schemas

class StaffResponse(CamelCaseModel):
    """Response schema for staff information (used in paginated lists)"""
    staff_id: str = Field(..., description="Staff ID (UUID)")
    uuid: str = Field(..., description="Staff UUID")
    email: EmailStr = Field(..., description="Staff email")
    full_name: str = Field(..., description="Full name")
    phone_number: Optional[str] = Field(None, description="Phone number")
    is_active: bool = Field(..., description="Account active status")
    is_verified: bool = Field(..., description="Email verification status")
    cms_role: str = Field(..., description="CMS role (principal, college_admin, hod, staff)")
    college_id: Optional[str] = Field(None, description="College ID (UUID)")
    department_id: Optional[str] = Field(None, description="Department ID (UUID)")
    invitation_status: str = Field(..., description="Invitation status (pending, accepted, active)")
    temporary_password: bool = Field(..., description="Has temporary password")
    must_reset_password: bool = Field(..., description="Must reset password on next login")
    invited_by_staff_id: Optional[str] = Field(None, description="ID of staff member who sent invitation (UUID)")
    is_hod: bool = Field(..., description="Head of Department status")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class StaffDetailsResponse(CamelCaseModel):
    """Detailed staff information response schema"""
    staff_id: str = Field(..., description="Staff ID (UUID)")
    uuid: str = Field(..., description="Staff UUID")
    email: EmailStr = Field(..., description="Staff email")
    full_name: str = Field(..., description="Full name")
    phone_number: Optional[str] = Field(None, description="Phone number")
    is_active: bool = Field(..., description="Account active status")
    is_verified: bool = Field(..., description="Email verification status")
    is_superstaff: bool = Field(..., description="Superstaff status")
    email_verified_at: Optional[datetime] = Field(None, description="Email verification timestamp")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    login_count: int = Field(..., description="Login count")
    marketing_consent: bool = Field(..., description="Marketing consent")
    terms_accepted: bool = Field(..., description="Terms accepted")
    cms_role: str = Field(..., description="CMS role")
    college_id: Optional[str] = Field(None, description="College ID (UUID)")
    department_id: Optional[str] = Field(None, description="Department ID (UUID)")
    invitation_status: str = Field(..., description="Invitation status")
    temporary_password: bool = Field(..., description="Has temporary password")
    must_reset_password: bool = Field(..., description="Must reset password")
    can_assign_department: bool = Field(..., description="Can assign departments")
    invited_by_staff_id: Optional[str] = Field(None, description="Invited by staff ID (UUID)")
    is_hod: bool = Field(..., description="Head of Department status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")


class StaffActionResponse(CamelCaseModel):
    """Generic response schema for staff management actions"""
    success: bool = Field(..., description="Action success status")
    message: str = Field(..., description="Action result message")
    staff_id: int = Field(..., description="Affected staff ID")


class UpdateUsernameResponse(CamelCaseModel):
    """Response schema for username update"""
    success: bool = Field(..., description="Update success status")
    message: str = Field(..., description="Update result message")
    staff_id: int = Field(..., description="Updated staff ID")
    full_name: str = Field(..., description="Updated full name")


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