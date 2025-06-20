from pydantic import EmailStr, Field
from typing import Optional, List
from datetime import datetime
from app.core.utils import CamelCaseModel
from app.schemas.auth import StaffResponse


# Staff management schemas


class StaffCreateRequest(CamelCaseModel):
    """Admin staff creation request schema"""

    email: EmailStr = Field(..., description="Staff email address")
    password: str = Field(..., min_length=8, description="Staff password")
    first_name: str = Field(
        ..., min_length=1, max_length=100, description="Staff first name"
    )
    last_name: str = Field(
        ..., min_length=1, max_length=100, description="Staff last name"
    )
    is_active: bool = Field(default=True, description="Staff active status")
    is_verified: bool = Field(default=False, description="Email verification status")
    is_superstaff: bool = Field(default=False, description="Superstaff status")


class StaffUpdateRequest(CamelCaseModel):
    """Staff update request schema"""

    first_name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Staff first name"
    )
    last_name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Staff last name"
    )
    is_active: Optional[bool] = Field(None, description="Staff active status")
    is_verified: Optional[bool] = Field(None, description="Email verification status")


class AdminStaffUpdateRequest(CamelCaseModel):
    """Admin staff update request schema (includes more fields)"""

    first_name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Staff first name"
    )
    last_name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Staff last name"
    )
    email: Optional[EmailStr] = Field(None, description="Staff email address")
    is_active: Optional[bool] = Field(None, description="Staff active status")
    is_verified: Optional[bool] = Field(None, description="Email verification status")
    is_superstaff: Optional[bool] = Field(None, description="Superstaff status")


class StaffListQuery(CamelCaseModel):
    """Query parameters for staff list endpoint"""

    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=10, ge=1, le=100, description="Page size")
    search: Optional[str] = Field(None, description="Search term for email/name")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    is_verified: Optional[bool] = Field(
        None, description="Filter by verification status"
    )
    is_superstaff: Optional[bool] = Field(None, description="Filter by superstaff status")
    sort_by: str = Field(default="created_at", description="Sort field")
    sort_order: str = Field(
        default="desc", pattern="^(asc|desc)$", description="Sort order"
    )


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
    last_activity: Optional[datetime] = Field(
        None, description="Last activity timestamp"
    )


class StaffActivityResponse(CamelCaseModel):
    """Staff activity response schema"""

    staff_id: int = Field(..., description="Staff ID")
    login_history: List[dict] = Field(..., description="Recent login history")
    activity_summary: dict = Field(..., description="Activity summary")
    last_seen: Optional[datetime] = Field(None, description="Last seen timestamp")


# Bulk operations schemas


class BulkStaffActionRequest(CamelCaseModel):
    """Bulk staff action request schema"""

    staff_ids: List[int] = Field(
        ..., min_items=1, description="List of staff IDs"
    )
    action: str = Field(
        ...,
        pattern="^(activate|deactivate|verify|unverify|delete)$",
        description="Action to perform",
    )


class BulkStaffActionResponse(CamelCaseModel):
    """Bulk staff action response schema"""

    message: str = Field(..., description="Response message")
    success: bool = Field(..., description="Operation success status")
    affected_staff: int = Field(..., description="Number of affected staff members")
    failed_staff: List[int] = Field(
        default=[], description="List of staff IDs that failed"
    )


# Staff preferences schemas


class StaffPreferencesRequest(CamelCaseModel):
    """Staff preferences update request schema"""

    email_notifications: bool = Field(
        default=True, description="Email notification preference"
    )
    theme: str = Field(
        default="light",
        pattern="^(light|dark|auto)$",
        description="UI theme preference",
    )
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
