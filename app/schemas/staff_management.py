from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime


class InviteStaffRequest(BaseModel):
    """Request schema for inviting a new staff member"""

    email: EmailStr = Field(..., description="Staff member's college/university email address")


class InviteStaffResponse(BaseModel):
    """Response schema for staff invitation"""

    success: bool = Field(..., description="Invitation success status")
    message: str = Field(..., description="Invitation status message")
    staffId: Optional[int] = Field(None, description="Created staff ID")
    email: EmailStr = Field(..., description="Invited staff email")
    temporaryPassword: str = Field(..., description="Generated temporary password")


class StaffResponse(BaseModel):
    """Response schema for staff information (used in paginated lists)"""

    staffId: int = Field(..., description="Staff ID")
    uuid: str = Field(..., description="Staff UUID")
    email: EmailStr = Field(..., description="Staff email")
    fullName: str = Field(..., description="Full name")
    phoneNumber: Optional[str] = Field(None, description="Phone number")
    isActive: bool = Field(..., description="Account active status")
    isVerified: bool = Field(..., description="Email verification status")
    cmsRole: str = Field(
        ..., description="CMS role (principal, college_admin, hod, staff)"
    )
    collegeId: Optional[int] = Field(None, description="College ID")
    departmentId: Optional[int] = Field(None, description="Department ID")
    invitationStatus: str = Field(
        ..., description="Invitation status (pending, accepted, active)"
    )
    temporaryPassword: bool = Field(..., description="Has temporary password")
    mustResetPassword: bool = Field(
        ..., description="Must reset password on next login"
    )
    invitedByStaffId: Optional[int] = Field(
        None, description="ID of staff member who sent invitation"
    )
    isHod: bool = Field(..., description="Head of Department status")
    lastLoginAt: Optional[datetime] = Field(None, description="Last login timestamp")
    createdAt: datetime = Field(..., description="Account creation timestamp")
    updatedAt: datetime = Field(..., description="Last update timestamp")


class AssignDepartmentRequest(BaseModel):
    """Request schema for assigning staff member to department"""

    departmentId: int = Field(..., description="Department ID to assign staff member to")


class UpdateStaffRoleRequest(BaseModel):
    """Request schema for updating staff role"""

    role: str = Field(..., description="New CMS role")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        allowed_roles = ["principal", "college_admin", "hod", "staff"]
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of: {', '.join(allowed_roles)}")
        return v


class StaffActionResponse(BaseModel):
    """Generic response schema for staff management actions"""

    success: bool = Field(..., description="Action success status")
    message: str = Field(..., description="Action result message")
    staffId: int = Field(..., description="Affected staff ID")


class UpdateUsernameRequest(BaseModel):
    """Request schema for updating staff username (full_name)"""

    fullName: str = Field(..., min_length=1, max_length=200, description="Full name (username)")


class UpdateUsernameResponse(BaseModel):
    """Response schema for username update"""

    success: bool = Field(..., description="Update success status")
    message: str = Field(..., description="Update result message")
    staffId: int = Field(..., description="Updated staff ID")
    fullName: str = Field(..., description="Updated full name")


class StaffDetailsResponse(BaseModel):
    """Detailed staff information response schema"""

    staffId: int = Field(..., description="Staff ID")
    uuid: str = Field(..., description="Staff UUID")
    email: EmailStr = Field(..., description="Staff email")
    fullName: str = Field(..., description="Full name")
    phoneNumber: Optional[str] = Field(None, description="Phone number")
    isActive: bool = Field(..., description="Account active status")
    isVerified: bool = Field(..., description="Email verification status")
    isSuperstaff: bool = Field(..., description="Superstaff status")
    emailVerifiedAt: Optional[datetime] = Field(
        None, description="Email verification timestamp"
    )
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
    invitedByStaffId: Optional[int] = Field(None, description="Invited by staff ID")
    isHod: bool = Field(..., description="Head of Department status")
    createdAt: datetime = Field(..., description="Creation timestamp")
    updatedAt: datetime = Field(..., description="Update timestamp")


class UpdateContactRequest(BaseModel):
    """Request schema for updating college contact information"""

    contactNumber: str = Field(..., pattern=r"^(\+91)?[6-9]\d{9}$", description="Contact number in Indian format")
    contactStaffId: int = Field(..., description="Staff ID who will be the primary contact")


class UpdateContactResponse(BaseModel):
    """Response schema for contact information update"""

    success: bool = Field(..., description="Update success status")
    message: str = Field(..., description="Update status message")
    contactNumber: str = Field(..., description="Updated contact number")
    contactStaffId: int = Field(..., description="Updated contact staff ID")


class ContactInfoResponse(BaseModel):
    """Response schema for getting current contact information"""

    contactNumber: Optional[str] = Field(None, description="Current contact number")
    contactStaffId: Optional[int] = Field(None, description="Current contact staff ID")
    contactStaffName: Optional[str] = Field(None, description="Contact staff full name")
    contactStaffEmail: Optional[str] = Field(None, description="Contact staff email")
