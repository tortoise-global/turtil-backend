from datetime import date
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CMSUserRole(str, Enum):
    PRINCIPAL = "principal"
    ADMIN = "admin"
    HEAD = "head"
    STAFF = "staff"


class CMSUserBase(BaseModel):
    username: str = Field(..., description="Unique username")
    email: EmailStr = Field(..., description="Email address")
    full_name: str = Field(..., description="Full name")
    phone: Optional[str] = Field(None, description="Phone number")
    role: CMSUserRole = Field(..., description="User role")
    department_id: Optional[UUID] = Field(None, description="Department UUID")
    branch_id: Optional[UUID] = Field(None, description="Branch UUID")
    degree_id: Optional[UUID] = Field(None, description="Degree UUID")
    is_active: Optional[bool] = Field(True, description="User status")
    email_verified: Optional[bool] = Field(
        False, description="Email verification status"
    )


class CMSUserCreate(CMSUserBase):
    college_id: UUID = Field(..., description="College UUID")
    password: str = Field(..., min_length=8, description="User password")


class CMSUserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[CMSUserRole] = None
    department_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    degree_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    email_verified: Optional[bool] = None


class CMSUserResponse(CMSUserBase):
    id: UUID
    college_id: UUID
    last_login: Optional[int] = None
    created_at: int
    updated_at: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class CMSUserLogin(BaseModel):
    username_or_email: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")


class CMSUserToken(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    user_id: UUID = Field(..., description="User UUID")
    role: CMSUserRole = Field(..., description="User role")
    college_id: UUID = Field(..., description="College UUID")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class CMSPasswordChange(BaseModel):
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")


class CMSPasswordReset(BaseModel):
    email: EmailStr = Field(..., description="Email address")


class CMSPasswordResetConfirm(BaseModel):
    token: str = Field(..., description="Reset token")
    new_password: str = Field(..., min_length=8, description="New password")


class CMSSystemModuleBase(BaseModel):
    name: str = Field(..., description="Module name")
    display_name: str = Field(..., description="Display name")
    description: Optional[str] = Field(None, description="Module description")
    is_core: Optional[bool] = Field(False, description="Core module flag")


class CMSSystemModuleCreate(CMSSystemModuleBase):
    pass


class CMSSystemModuleUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    is_core: Optional[bool] = None


class CMSSystemModuleResponse(CMSSystemModuleBase):
    id: UUID
    created_at: int

    model_config = ConfigDict(from_attributes=True)


class CMSCollegeModuleBase(BaseModel):
    is_enabled: bool = Field(True, description="Module enabled status")


class CMSCollegeModuleCreate(CMSCollegeModuleBase):
    college_id: UUID = Field(..., description="College UUID")
    module_id: UUID = Field(..., description="Module UUID")


class CMSCollegeModuleUpdate(BaseModel):
    is_enabled: Optional[bool] = None


class CMSCollegeModuleResponse(CMSCollegeModuleBase):
    id: UUID
    college_id: UUID
    module_id: UUID
    configured_at: int

    model_config = ConfigDict(from_attributes=True)


class CMSUserModulePermissionBase(BaseModel):
    has_access: bool = Field(False, description="Access permission")


class CMSUserModulePermissionCreate(CMSUserModulePermissionBase):
    user_id: UUID = Field(..., description="User UUID")
    module_id: UUID = Field(..., description="Module UUID")


class CMSUserModulePermissionUpdate(BaseModel):
    has_access: Optional[bool] = None


class CMSUserModulePermissionResponse(CMSUserModulePermissionBase):
    id: UUID
    user_id: UUID
    module_id: UUID
    granted_at: int

    model_config = ConfigDict(from_attributes=True)


class CMSCollegeSettingBase(BaseModel):
    setting_key: str = Field(..., description="Setting key")
    setting_value: Optional[str] = Field(None, description="Setting value")
    data_type: Optional[str] = Field("string", description="Data type")


class CMSCollegeSettingCreate(CMSCollegeSettingBase):
    college_id: UUID = Field(..., description="College UUID")


class CMSCollegeSettingUpdate(BaseModel):
    setting_value: Optional[str] = None
    data_type: Optional[str] = None


class CMSCollegeSettingResponse(CMSCollegeSettingBase):
    id: UUID
    college_id: UUID
    created_at: int
    updated_at: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class CMSFacultySubjectAssignmentBase(BaseModel):
    academic_year: Optional[int] = Field(None, description="Academic year")
    semester: Optional[int] = Field(None, description="Semester")
    assigned_date: Optional[date] = Field(None, description="Assignment date")
    is_active: Optional[bool] = Field(True, description="Assignment status")


class CMSFacultySubjectAssignmentCreate(CMSFacultySubjectAssignmentBase):
    user_id: UUID = Field(..., description="Faculty UUID")
    subject_id: UUID = Field(..., description="Subject UUID")


class CMSFacultySubjectAssignmentUpdate(BaseModel):
    academic_year: Optional[int] = None
    semester: Optional[int] = None
    is_active: Optional[bool] = None


class CMSFacultySubjectAssignmentResponse(CMSFacultySubjectAssignmentBase):
    id: UUID
    user_id: UUID
    subject_id: UUID

    model_config = ConfigDict(from_attributes=True)


class CMSUserWithPermissions(CMSUserResponse):
    module_permissions: List[CMSUserModulePermissionResponse] = []


class CMSCollegeWithModules(BaseModel):
    college_id: UUID
    enabled_modules: List[CMSSystemModuleResponse] = []
    settings: List[CMSCollegeSettingResponse] = []

    model_config = ConfigDict(from_attributes=True)


class CMSBulkUserCreate(BaseModel):
    users: List[CMSUserCreate] = Field(..., description="List of users to create")
    send_welcome_email: Optional[bool] = Field(True, description="Send welcome emails")


class CMSBulkUserUpdate(BaseModel):
    user_ids: List[UUID] = Field(..., description="List of user UUIDs")
    updates: CMSUserUpdate = Field(..., description="Updates to apply")


class CMSBulkPermissionUpdate(BaseModel):
    user_ids: List[UUID] = Field(..., description="List of user UUIDs")
    module_id: UUID = Field(..., description="Module UUID")
    has_access: bool = Field(..., description="Access permission")


class CMSUserStatistics(BaseModel):
    total_users: int = Field(..., description="Total number of users")
    active_users: int = Field(..., description="Number of active users")
    users_by_role: dict = Field(..., description="User count by role")
    recent_logins: int = Field(..., description="Recent login count")
    verification_pending: int = Field(..., description="Users pending verification")

    model_config = ConfigDict(from_attributes=True)


class CMSModuleUsageStatistics(BaseModel):
    module_id: UUID = Field(..., description="Module UUID")
    module_name: str = Field(..., description="Module name")
    total_users: int = Field(..., description="Total users with access")
    active_users: int = Field(..., description="Active users")
    usage_percentage: float = Field(..., description="Usage percentage")

    model_config = ConfigDict(from_attributes=True)
