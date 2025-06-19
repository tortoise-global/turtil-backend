from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime


class InviteUserRequest(BaseModel):
    """Request schema for inviting a new user"""
    email: EmailStr = Field(..., description="User's college/university email address")


class InviteUserResponse(BaseModel):
    """Response schema for user invitation"""
    success: bool = Field(..., description="Invitation success status")
    message: str = Field(..., description="Invitation status message")
    cmsUserId: Optional[int] = Field(None, description="Created user ID")
    email: EmailStr = Field(..., description="Invited user email")
    temporaryPassword: str = Field(..., description="Generated temporary password")


class UserResponse(BaseModel):
    """Response schema for user information (used in paginated lists)"""
    cmsUserId: int = Field(..., description="User ID")
    uuid: str = Field(..., description="User UUID")
    email: EmailStr = Field(..., description="User email")
    firstName: str = Field(..., description="First name")
    lastName: str = Field(..., description="Last name")
    fullName: str = Field(..., description="Full name")
    phoneNumber: Optional[str] = Field(None, description="Phone number")
    isActive: bool = Field(..., description="Account active status")
    isVerified: bool = Field(..., description="Email verification status")
    cmsRole: str = Field(..., description="CMS role (principal, college_admin, hod, staff)")
    collegeId: Optional[int] = Field(None, description="College ID")
    departmentId: Optional[int] = Field(None, description="Department ID")
    invitationStatus: str = Field(..., description="Invitation status (pending, accepted, active)")
    temporaryPassword: bool = Field(..., description="Has temporary password")
    mustResetPassword: bool = Field(..., description="Must reset password on next login")
    invitedByCmsUserId: Optional[int] = Field(None, description="ID of user who sent invitation")
    isHod: bool = Field(..., description="Head of Department status")
    lastLoginAt: Optional[datetime] = Field(None, description="Last login timestamp")
    createdAt: datetime = Field(..., description="Account creation timestamp")
    updatedAt: datetime = Field(..., description="Last update timestamp")


class AssignDepartmentRequest(BaseModel):
    """Request schema for assigning user to department"""
    departmentId: int = Field(..., description="Department ID to assign user to")


class UpdateUserRoleRequest(BaseModel):
    """Request schema for updating user role"""
    role: str = Field(..., description="New CMS role")
    
    @validator('role')
    def validate_role(cls, v):
        allowed_roles = ['principal', 'college_admin', 'hod', 'staff']
        if v not in allowed_roles:
            raise ValueError(f'Role must be one of: {", ".join(allowed_roles)}')
        return v


class UserActionResponse(BaseModel):
    """Generic response schema for user management actions"""
    success: bool = Field(..., description="Action success status")
    message: str = Field(..., description="Action result message")
    cmsUserId: int = Field(..., description="Affected user ID")


class UserDetailsResponse(BaseModel):
    """Detailed user information response schema"""
    cmsUserId: int = Field(..., description="User ID")
    uuid: str = Field(..., description="User UUID")
    email: EmailStr = Field(..., description="User email")
    firstName: str = Field(..., description="First name")
    lastName: str = Field(..., description="Last name")
    fullName: str = Field(..., description="Full name")
    phoneNumber: Optional[str] = Field(None, description="Phone number")
    isActive: bool = Field(..., description="Account active status")
    isVerified: bool = Field(..., description="Email verification status")
    isSuperuser: bool = Field(..., description="Superuser status")
    emailVerifiedAt: Optional[datetime] = Field(None, description="Email verification timestamp")
    lastLoginAt: Optional[datetime] = Field(None, description="Last login timestamp")
    loginCount: int = Field(..., description="Login count")
    marketingConsent: bool = Field(..., description="Marketing consent")
    termsAccepted: bool = Field(..., description="Terms accepted")
    cmsRole: str = Field(..., description="CMS role")
    collegeId: Optional[int] = Field(None, description="College ID")
    departmentId: Optional[int] = Field(None, description="Department ID")
    invitationStatus: str = Field(..., description="Invitation status")
    temporaryPassword: bool = Field(..., description="Has temporary password")
    mustResetPassword: bool = Field(..., description="Must reset password")
    canAssignDepartment: bool = Field(..., description="Can assign departments")
    invitedByCmsUserId: Optional[int] = Field(None, description="Invited by user ID")
    isHod: bool = Field(..., description="Head of Department status")
    createdAt: datetime = Field(..., description="Creation timestamp")
    updatedAt: datetime = Field(..., description="Update timestamp")