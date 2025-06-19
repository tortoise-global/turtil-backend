from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime


class CreateDepartmentRequest(BaseModel):
    """Request schema for creating a new department"""
    name: str = Field(..., min_length=1, max_length=255, description="Department name")
    code: str = Field(..., min_length=2, max_length=50, description="Department code (e.g., CSE, ECE)")
    description: Optional[str] = Field(None, max_length=1000, description="Department description")
    
    @validator('code')
    def code_uppercase(cls, v):
        return v.upper()


class UpdateDepartmentRequest(BaseModel):
    """Request schema for updating a department"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Department name")
    code: Optional[str] = Field(None, min_length=2, max_length=50, description="Department code")
    description: Optional[str] = Field(None, max_length=1000, description="Department description")
    hodCmsUserId: Optional[int] = Field(None, description="Head of Department user ID")
    
    @validator('code')
    def code_uppercase(cls, v):
        if v is not None:
            return v.upper()
        return v


class DepartmentResponse(BaseModel):
    """Response schema for department information"""
    id: int = Field(..., description="Department ID")
    uuid: str = Field(..., description="Department UUID")
    name: str = Field(..., description="Department name")
    code: str = Field(..., description="Department code")
    description: Optional[str] = Field(None, description="Department description")
    collegeId: int = Field(..., description="College ID")
    hodCmsUserId: Optional[int] = Field(None, description="Head of Department user ID")
    createdAt: datetime = Field(..., description="Creation timestamp")
    updatedAt: datetime = Field(..., description="Update timestamp")


class DepartmentWithStatsResponse(BaseModel):
    """Department response with user statistics"""
    id: int = Field(..., description="Department ID")
    uuid: str = Field(..., description="Department UUID") 
    name: str = Field(..., description="Department name")
    code: str = Field(..., description="Department code")
    description: Optional[str] = Field(None, description="Department description")
    collegeId: int = Field(..., description="College ID")
    hodCmsUserId: Optional[int] = Field(None, description="Head of Department user ID")
    hodName: Optional[str] = Field(None, description="Head of Department name")
    totalUsers: int = Field(..., description="Total users in department")
    activeUsers: int = Field(..., description="Active users in department")
    createdAt: datetime = Field(..., description="Creation timestamp")
    updatedAt: datetime = Field(..., description="Update timestamp")


class DepartmentActionResponse(BaseModel):
    """Generic response schema for department management actions"""
    success: bool = Field(..., description="Action success status")
    message: str = Field(..., description="Action result message")
    departmentId: Optional[int] = Field(None, description="Affected department ID")


class AssignHODRequest(BaseModel):
    """Request schema for assigning HOD to department"""
    cmsUserId: int = Field(..., description="User ID to assign as HOD")


class HODActionResponse(BaseModel):
    """Response schema for HOD assignment/removal actions"""
    success: bool = Field(..., description="Action success status")
    message: str = Field(..., description="Action result message")
    departmentId: int = Field(..., description="Department ID")
    cmsUserId: Optional[int] = Field(None, description="HOD user ID")
    hodName: Optional[str] = Field(None, description="HOD name")