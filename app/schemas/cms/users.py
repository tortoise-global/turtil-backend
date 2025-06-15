"""CMS user schemas and data models.

This module contains Pydantic models for CMS user management including:
- User creation, update, and response models
- Permission and role management models
- Module access and configuration models
- Bulk operations and statistics models
"""

from datetime import date
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CMSUserRole(str, Enum):
    """Enumeration of available CMS user roles."""

    PRINCIPAL = "principal"
    ADMIN = "admin"
    HEAD = "head"
    STAFF = "staff"


class CMSUserBase(BaseModel):
    """Base model for CMS user data with common fields."""

    username: str = Field(..., description="Unique username")
    email: EmailStr = Field(..., description="Email address")
    full_name: str = Field(..., description="Full name", alias="fullName")
    phone: Optional[str] = Field(None, description="Phone number")
    role: CMSUserRole = Field(..., description="User role")
    department_id: Optional[UUID] = Field(
        None, description="Department UUID", alias="departmentId"
    )
    branch_id: Optional[UUID] = Field(None, description="Branch UUID", alias="branchId")
    degree_id: Optional[UUID] = Field(None, description="Degree UUID", alias="degreeId")
    is_active: Optional[bool] = Field(True, description="User status", alias="isActive")
    email_verified: Optional[bool] = Field(
        False, description="Email verification status", alias="emailVerified"
    )

    model_config = ConfigDict(populate_by_name=True)


class CMSUserCreate(CMSUserBase):
    """Model for creating a new CMS user."""

    college_id: UUID = Field(..., description="College UUID", alias="collegeId")
    password: str = Field(..., min_length=8, description="User password")


class CMSUserUpdate(BaseModel):
    """Model for updating CMS user data."""

    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, alias="fullName")
    phone: Optional[str] = None
    role: Optional[CMSUserRole] = None
    department_id: Optional[UUID] = Field(None, alias="departmentId")
    branch_id: Optional[UUID] = Field(None, alias="branchId")
    degree_id: Optional[UUID] = Field(None, alias="degreeId")
    is_active: Optional[bool] = Field(None, alias="isActive")
    email_verified: Optional[bool] = Field(None, alias="emailVerified")

    model_config = ConfigDict(populate_by_name=True)


class CMSUserResponse(CMSUserBase):
    """Model for CMS user API responses."""

    id: UUID
    college_id: UUID = Field(..., alias="collegeId")
    last_login: Optional[int] = Field(None, alias="lastLogin")
    created_at: int = Field(..., alias="createdAt")
    updated_at: Optional[int] = Field(None, alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class CMSUserLogin(BaseModel):
    """Model for CMS user login credentials."""

    username_or_email: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")


class CMSUserToken(BaseModel):
    """Model for CMS user authentication token response."""

    access_token: str = Field(..., description="JWT access token", alias="accessToken")
    token_type: str = Field("bearer", description="Token type", alias="tokenType")
    user_id: UUID = Field(..., description="User UUID", alias="userId")
    role: CMSUserRole = Field(..., description="User role")
    college_id: UUID = Field(..., description="College UUID", alias="collegeId")
    expires_in: int = Field(
        ..., description="Token expiration time in seconds", alias="expiresIn"
    )

    model_config = ConfigDict(populate_by_name=True)


class CMSPasswordChange(BaseModel):
    """Model for password change request."""

    current_password: str = Field(
        ..., description="Current password", alias="currentPassword"
    )
    new_password: str = Field(
        ..., min_length=8, description="New password", alias="newPassword"
    )

    model_config = ConfigDict(populate_by_name=True)


class CMSPasswordReset(BaseModel):
    """Model for password reset request."""

    email: EmailStr = Field(..., description="Email address")


class CMSPasswordResetConfirm(BaseModel):
    """Model for password reset confirmation."""

    token: str = Field(..., description="Reset token")
    new_password: str = Field(
        ..., min_length=8, description="New password", alias="newPassword"
    )

    model_config = ConfigDict(populate_by_name=True)


class CMSSystemModuleBase(BaseModel):
    """Base model for CMS system modules."""

    name: str = Field(..., description="Module name")
    display_name: str = Field(..., description="Display name", alias="displayName")
    description: Optional[str] = Field(None, description="Module description")
    is_core: Optional[bool] = Field(
        False, description="Core module flag", alias="isCore"
    )

    model_config = ConfigDict(populate_by_name=True)


class CMSSystemModuleCreate(CMSSystemModuleBase):
    """Model for creating a new system module."""

    pass


class CMSSystemModuleUpdate(BaseModel):
    """Model for updating system module data."""

    name: Optional[str] = None
    display_name: Optional[str] = Field(None, alias="displayName")
    description: Optional[str] = None
    is_core: Optional[bool] = Field(None, alias="isCore")

    model_config = ConfigDict(populate_by_name=True)


class CMSSystemModuleResponse(CMSSystemModuleBase):
    """Model for system module API responses."""

    id: UUID
    created_at: int = Field(..., alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class CMSCollegeModuleBase(BaseModel):
    """Base model for college module configuration."""

    is_enabled: bool = Field(
        True, description="Module enabled status", alias="isEnabled"
    )

    model_config = ConfigDict(populate_by_name=True)


class CMSCollegeModuleCreate(CMSCollegeModuleBase):
    """Model for creating college module configuration."""

    college_id: UUID = Field(..., description="College UUID", alias="collegeId")
    module_id: UUID = Field(..., description="Module UUID", alias="moduleId")


class CMSCollegeModuleUpdate(BaseModel):
    """Model for updating college module configuration."""

    is_enabled: Optional[bool] = Field(None, alias="isEnabled")

    model_config = ConfigDict(populate_by_name=True)


class CMSCollegeModuleResponse(CMSCollegeModuleBase):
    """Model for college module configuration API responses."""

    id: UUID
    college_id: UUID
    module_id: UUID
    configured_at: int

    model_config = ConfigDict(from_attributes=True)


class CMSUserModulePermissionBase(BaseModel):
    """Base model for user module permissions."""

    has_access: bool = Field(False, description="Access permission")


class CMSUserModulePermissionCreate(CMSUserModulePermissionBase):
    """Model for creating user module permissions."""

    user_id: UUID = Field(..., description="User UUID")
    module_id: UUID = Field(..., description="Module UUID")


class CMSUserModulePermissionUpdate(BaseModel):
    """Model for updating user module permissions."""

    has_access: Optional[bool] = None


class CMSUserModulePermissionResponse(CMSUserModulePermissionBase):
    """Model for user module permission API responses."""

    id: UUID
    user_id: UUID
    module_id: UUID
    granted_at: int

    model_config = ConfigDict(from_attributes=True)


class CMSCollegeSettingBase(BaseModel):
    """Base model for college settings."""

    setting_key: str = Field(..., description="Setting key")
    setting_value: Optional[str] = Field(None, description="Setting value")
    data_type: Optional[str] = Field("string", description="Data type")


class CMSCollegeSettingCreate(CMSCollegeSettingBase):
    """Model for creating college settings."""

    college_id: UUID = Field(..., description="College UUID")


class CMSCollegeSettingUpdate(BaseModel):
    """Model for updating college settings."""

    setting_value: Optional[str] = None
    data_type: Optional[str] = None


class CMSCollegeSettingResponse(CMSCollegeSettingBase):
    """Model for college setting API responses."""

    id: UUID
    college_id: UUID
    created_at: int
    updated_at: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class CMSFacultySubjectAssignmentBase(BaseModel):
    """Base model for faculty subject assignments."""

    academic_year: Optional[int] = Field(None, description="Academic year")
    semester: Optional[int] = Field(None, description="Semester")
    assigned_date: Optional[date] = Field(None, description="Assignment date")
    is_active: Optional[bool] = Field(True, description="Assignment status")


class CMSFacultySubjectAssignmentCreate(CMSFacultySubjectAssignmentBase):
    """Model for creating faculty subject assignments."""

    user_id: UUID = Field(..., description="Faculty UUID")
    subject_id: UUID = Field(..., description="Subject UUID")


class CMSFacultySubjectAssignmentUpdate(BaseModel):
    """Model for updating faculty subject assignments."""

    academic_year: Optional[int] = None
    semester: Optional[int] = None
    is_active: Optional[bool] = None


class CMSFacultySubjectAssignmentResponse(CMSFacultySubjectAssignmentBase):
    """Model for faculty subject assignment API responses."""

    id: UUID
    user_id: UUID
    subject_id: UUID

    model_config = ConfigDict(from_attributes=True)


class CMSUserWithPermissions(CMSUserResponse):
    """Model for CMS user with their module permissions."""

    module_permissions: List[CMSUserModulePermissionResponse] = []


class CMSCollegeWithModules(BaseModel):
    """Model for college with enabled modules and settings."""

    college_id: UUID
    enabled_modules: List[CMSSystemModuleResponse] = []
    settings: List[CMSCollegeSettingResponse] = []

    model_config = ConfigDict(from_attributes=True)


class CMSBulkUserCreate(BaseModel):
    """Model for bulk user creation operations."""

    users: List[CMSUserCreate] = Field(..., description="List of users to create")
    send_welcome_email: Optional[bool] = Field(True, description="Send welcome emails")


class CMSBulkUserUpdate(BaseModel):
    """Model for bulk user update operations."""

    user_ids: List[UUID] = Field(..., description="List of user UUIDs")
    updates: CMSUserUpdate = Field(..., description="Updates to apply")


class CMSBulkPermissionUpdate(BaseModel):
    """Model for bulk permission update operations."""

    user_ids: List[UUID] = Field(..., description="List of user UUIDs")
    module_id: UUID = Field(..., description="Module UUID")
    has_access: bool = Field(..., description="Access permission")


class CMSUserStatistics(BaseModel):
    """Model for CMS user statistics and metrics."""

    total_users: int = Field(..., description="Total number of users")
    active_users: int = Field(..., description="Number of active users")
    users_by_role: dict = Field(..., description="User count by role")
    recent_logins: int = Field(..., description="Recent login count")
    verification_pending: int = Field(..., description="Users pending verification")

    model_config = ConfigDict(from_attributes=True)


class CMSModuleUsageStatistics(BaseModel):
    """Model for module usage statistics and metrics."""

    module_id: UUID = Field(..., description="Module UUID")
    module_name: str = Field(..., description="Module name")
    total_users: int = Field(..., description="Total users with access")
    active_users: int = Field(..., description="Active users")
    usage_percentage: float = Field(..., description="Usage percentage")

    model_config = ConfigDict(from_attributes=True)
