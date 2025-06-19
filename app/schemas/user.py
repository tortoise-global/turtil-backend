from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from app.core.utils import CamelCaseModel
from app.schemas.auth import UserResponse


# User management schemas

class UserCreateRequest(CamelCaseModel):
    """Admin user creation request schema"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    first_name: str = Field(..., min_length=1, max_length=100, description="User first name")
    last_name: str = Field(..., min_length=1, max_length=100, description="User last name")
    is_active: bool = Field(default=True, description="User active status")
    is_verified: bool = Field(default=False, description="Email verification status")
    is_superuser: bool = Field(default=False, description="Superuser status")


class UserUpdateRequest(CamelCaseModel):
    """User update request schema"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100, description="User first name")
    last_name: Optional[str] = Field(None, min_length=1, max_length=100, description="User last name")
    is_active: Optional[bool] = Field(None, description="User active status")
    is_verified: Optional[bool] = Field(None, description="Email verification status")


class AdminUserUpdateRequest(CamelCaseModel):
    """Admin user update request schema (includes more fields)"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100, description="User first name")
    last_name: Optional[str] = Field(None, min_length=1, max_length=100, description="User last name")
    email: Optional[EmailStr] = Field(None, description="User email address")
    is_active: Optional[bool] = Field(None, description="User active status")
    is_verified: Optional[bool] = Field(None, description="Email verification status")
    is_superuser: Optional[bool] = Field(None, description="Superuser status")


class UserListQuery(CamelCaseModel):
    """Query parameters for user list endpoint"""
    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=10, ge=1, le=100, description="Page size")
    search: Optional[str] = Field(None, description="Search term for email/name")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    is_verified: Optional[bool] = Field(None, description="Filter by verification status")
    is_superuser: Optional[bool] = Field(None, description="Filter by superuser status")
    sort_by: str = Field(default="created_at", description="Sort field")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$", description="Sort order")


class UserListResponse(CamelCaseModel):
    """User list response schema with pagination"""
    users: List[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")


class UserStatsResponse(CamelCaseModel):
    """User statistics response schema"""
    total_users: int = Field(..., description="Total number of users")
    active_users: int = Field(..., description="Number of active users")
    verified_users: int = Field(..., description="Number of verified users")
    superusers: int = Field(..., description="Number of superusers")
    new_users_this_month: int = Field(..., description="New users this month")
    new_users_this_week: int = Field(..., description="New users this week")


class UserProfileResponse(CamelCaseModel):
    """User profile response schema"""
    user: UserResponse = Field(..., description="User information")
    profile_completion: float = Field(..., description="Profile completion percentage")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")


class UserActivityResponse(CamelCaseModel):
    """User activity response schema"""
    cms_user_id: int = Field(..., description="CMS User ID")
    login_history: List[dict] = Field(..., description="Recent login history")
    activity_summary: dict = Field(..., description="Activity summary")
    last_seen: Optional[datetime] = Field(None, description="Last seen timestamp")


# Bulk operations schemas

class BulkUserActionRequest(CamelCaseModel):
    """Bulk user action request schema"""
    cms_user_ids: List[int] = Field(..., min_items=1, description="List of CMS user IDs")
    action: str = Field(..., pattern="^(activate|deactivate|verify|unverify|delete)$", description="Action to perform")


class BulkUserActionResponse(CamelCaseModel):
    """Bulk user action response schema"""
    message: str = Field(..., description="Response message")
    success: bool = Field(..., description="Operation success status")
    affected_users: int = Field(..., description="Number of affected users")
    failed_users: List[int] = Field(default=[], description="List of user IDs that failed")


# User preferences schemas

class UserPreferencesRequest(CamelCaseModel):
    """User preferences update request schema"""
    email_notifications: bool = Field(default=True, description="Email notification preference")
    theme: str = Field(default="light", pattern="^(light|dark|auto)$", description="UI theme preference")
    language: str = Field(default="en", description="Language preference")
    timezone: str = Field(default="UTC", description="Timezone preference")


class UserPreferencesResponse(CamelCaseModel):
    """User preferences response schema"""
    cms_user_id: int = Field(..., description="CMS User ID")
    email_notifications: bool = Field(..., description="Email notification preference")
    theme: str = Field(..., description="UI theme preference")
    language: str = Field(..., description="Language preference")
    timezone: str = Field(..., description="Timezone preference")
    updated_at: datetime = Field(..., description="Last update timestamp")