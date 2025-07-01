from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class DivisionCreateRequest(BaseModel):
    """Schema for creating a new division"""
    name: str = Field(..., min_length=1, max_length=255, description="Division name")
    code: str = Field(..., min_length=1, max_length=50, description="Division code (e.g., ENG, MGMT)")
    description: Optional[str] = Field(None, description="Division description")


class DivisionUpdateRequest(BaseModel):
    """Schema for updating division details"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None


class DivisionResponse(BaseModel):
    """Schema for division API responses"""
    model_config = ConfigDict(from_attributes=True)
    
    divisionId: UUID
    name: str
    code: str
    description: Optional[str]
    collegeId: UUID
    createdAt: datetime
    updatedAt: datetime


class DivisionWithStatsResponse(DivisionResponse):
    """Division response with additional statistics"""
    departmentCount: int = Field(default=0, description="Number of departments in this division")
    staffCount: int = Field(default=0, description="Number of staff assigned to this division")


class DivisionListResponse(BaseModel):
    """Paginated response for division list"""
    items: List[DivisionWithStatsResponse]
    total: int
    page: int
    size: int
    pages: int


# Removed staff assignment schemas as they are no longer needed
# Staff will be auto-assigned to division through department assignment


# Response schemas for division operations
class DivisionOperationResponse(BaseModel):
    """Response for division operations"""
    success: bool
    message: str
    divisionId: Optional[UUID] = None