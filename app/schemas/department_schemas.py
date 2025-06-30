from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from app.core.utils import CamelCaseModel


class CreateDepartmentRequest(CamelCaseModel):
    """Request schema for creating a new department"""

    name: str = Field(..., min_length=1, max_length=255, description="Department name")
    code: str = Field(
        ..., min_length=2, max_length=50, description="Department code (e.g., CSE, ECE)"
    )
    description: Optional[str] = Field(
        None, max_length=1000, description="Department description"
    )

    @field_validator("code")
    @classmethod
    def code_uppercase(cls, v):
        return v.upper()


class UpdateDepartmentRequest(CamelCaseModel):
    """Request schema for updating a department"""

    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Department name"
    )
    code: Optional[str] = Field(
        None, min_length=2, max_length=50, description="Department code"
    )
    description: Optional[str] = Field(
        None, max_length=1000, description="Department description"
    )
    hod_cms_staff_id: Optional[str] = Field(None, description="Head of Department staff ID (UUID)")

    @field_validator("code")
    @classmethod
    def code_uppercase(cls, v):
        if v is not None:
            return v.upper()
        return v


class DepartmentResponse(CamelCaseModel):
    """Response schema for department information"""

    id: str = Field(..., description="Department ID (UUID)")
    uuid: str = Field(..., description="Department UUID")
    name: str = Field(..., description="Department name")
    code: str = Field(..., description="Department code")
    description: Optional[str] = Field(None, description="Department description")
    college_id: str = Field(..., description="College ID (UUID)")
    hod_cms_staff_id: Optional[str] = Field(None, description="Head of Department staff ID (UUID)")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")


class DepartmentWithStatsResponse(CamelCaseModel):
    """Department response with staff statistics"""

    id: str = Field(..., description="Department ID (UUID)")
    uuid: str = Field(..., description="Department UUID")
    name: str = Field(..., description="Department name")
    code: str = Field(..., description="Department code")
    description: Optional[str] = Field(None, description="Department description")
    college_id: str = Field(..., description="College ID (UUID)")
    hod_cms_staff_id: Optional[str] = Field(None, description="Head of Department staff ID (UUID)")
    hod_name: Optional[str] = Field(None, description="Head of Department name")
    total_staffs: int = Field(..., description="Total staff in department")
    active_staffs: int = Field(..., description="Active staff in department")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")


class DepartmentActionResponse(CamelCaseModel):
    """Generic response schema for department management actions"""

    success: bool = Field(..., description="Action success status")
    message: str = Field(..., description="Action result message")
    department_id: Optional[str] = Field(None, description="Affected department ID (UUID)")


class AssignHODRequest(CamelCaseModel):
    """Request schema for assigning HOD to department"""

    staff_id: str = Field(..., description="Staff ID to assign as HOD (UUID)")


class HODActionResponse(CamelCaseModel):
    """Response schema for HOD assignment/removal actions"""

    success: bool = Field(..., description="Action success status")
    message: str = Field(..., description="Action result message")
    department_id: str = Field(..., description="Department ID (UUID)")
    staff_id: Optional[str] = Field(None, description="HOD staff ID (UUID)")
    hod_name: Optional[str] = Field(None, description="HOD name")
