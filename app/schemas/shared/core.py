from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CollegeBase(BaseModel):
    college_id: str = Field(..., description="Unique college identifier")
    name: str = Field(..., description="Full college name")
    short_name: str = Field(..., description="College abbreviation")
    logo_url: Optional[str] = Field(None, description="College logo URL")
    affiliated_university_name: Optional[str] = Field(
        None, description="University name"
    )
    affiliated_university_short: Optional[str] = Field(
        None, description="University abbreviation"
    )
    university_id: Optional[str] = Field(None, description="University identifier")
    address: Optional[str] = Field(None, description="College address")
    city: Optional[str] = Field(None, description="City")
    district: Optional[str] = Field(None, description="District")
    state: Optional[str] = Field(None, description="State")
    pincode: Optional[str] = Field(None, description="Postal code")
    latitude: Optional[Decimal] = Field(None, description="Latitude coordinates")
    longitude: Optional[Decimal] = Field(None, description="Longitude coordinates")
    total_locations: Optional[int] = Field(1, description="Number of campuses")
    is_active: Optional[bool] = Field(True, description="College status")


class CollegeCreate(CollegeBase):
    pass


class CollegeUpdate(BaseModel):
    college_id: Optional[str] = None
    name: Optional[str] = None
    short_name: Optional[str] = None
    logo_url: Optional[str] = None
    affiliated_university_name: Optional[str] = None
    affiliated_university_short: Optional[str] = None
    university_id: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    total_locations: Optional[int] = None
    is_active: Optional[bool] = None


class CollegeResponse(CollegeBase):
    id: UUID
    created_at: int
    updated_at: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class CollegeLocationBase(BaseModel):
    location_name: str = Field(..., description="Location/campus name")
    address: Optional[str] = Field(None, description="Campus address")
    city: Optional[str] = Field(None, description="City")
    district: Optional[str] = Field(None, description="District")
    state: Optional[str] = Field(None, description="State")
    pincode: Optional[str] = Field(None, description="Postal code")
    latitude: Optional[Decimal] = Field(None, description="Latitude coordinates")
    longitude: Optional[Decimal] = Field(None, description="Longitude coordinates")
    is_main_campus: Optional[bool] = Field(False, description="Main campus flag")


class CollegeLocationCreate(CollegeLocationBase):
    college_id: UUID = Field(..., description="College UUID")


class CollegeLocationResponse(CollegeLocationBase):
    id: UUID
    college_id: UUID
    created_at: int

    model_config = ConfigDict(from_attributes=True)


class DegreeBase(BaseModel):
    name: str = Field(..., description="Degree name (B.Tech, M.Tech, etc.)")
    duration_years: Optional[int] = Field(None, description="Degree duration in years")
    is_active: Optional[bool] = Field(True, description="Degree status")


class DegreeCreate(DegreeBase):
    college_id: UUID = Field(..., description="College UUID")


class DegreeUpdate(BaseModel):
    name: Optional[str] = None
    duration_years: Optional[int] = None
    is_active: Optional[bool] = None


class DegreeResponse(DegreeBase):
    id: UUID
    college_id: UUID
    created_at: int

    model_config = ConfigDict(from_attributes=True)


class DepartmentBase(BaseModel):
    name: str = Field(..., description="Department name")
    short_name: Optional[str] = Field(None, description="Department abbreviation")
    head_name: Optional[str] = Field(None, description="Department head name")
    is_active: Optional[bool] = Field(True, description="Department status")


class DepartmentCreate(DepartmentBase):
    college_id: UUID = Field(..., description="College UUID")


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    short_name: Optional[str] = None
    head_name: Optional[str] = None
    is_active: Optional[bool] = None


class DepartmentResponse(DepartmentBase):
    id: UUID
    college_id: UUID
    created_at: int

    model_config = ConfigDict(from_attributes=True)


class BranchBase(BaseModel):
    name: str = Field(..., description="Branch name")
    code: Optional[str] = Field(None, description="Branch code")
    is_active: Optional[bool] = Field(True, description="Branch status")


class BranchCreate(BranchBase):
    department_id: UUID = Field(..., description="Department UUID")
    degree_id: UUID = Field(..., description="Degree UUID")


class BranchUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    department_id: Optional[UUID] = None
    degree_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class BranchResponse(BranchBase):
    id: UUID
    department_id: UUID
    degree_id: UUID
    created_at: int

    model_config = ConfigDict(from_attributes=True)


class SubjectBase(BaseModel):
    subject_code: str = Field(..., description="Subject code")
    subject_name: str = Field(..., description="Subject name")
    semester: Optional[int] = Field(None, description="Semester number")
    credits: Optional[int] = Field(0, description="Subject credits")
    is_core: Optional[bool] = Field(True, description="Core subject flag")
    is_active: Optional[bool] = Field(True, description="Subject status")


class SubjectCreate(SubjectBase):
    college_id: UUID = Field(..., description="College UUID")
    branch_id: Optional[UUID] = Field(None, description="Branch UUID")


class SubjectUpdate(BaseModel):
    subject_code: Optional[str] = None
    subject_name: Optional[str] = None
    semester: Optional[int] = None
    credits: Optional[int] = None
    is_core: Optional[bool] = None
    is_active: Optional[bool] = None
    branch_id: Optional[UUID] = None


class SubjectResponse(SubjectBase):
    id: UUID
    college_id: UUID
    branch_id: Optional[UUID] = None
    created_at: int

    model_config = ConfigDict(from_attributes=True)


# RESPONSE MODELS WITH NESTED DATA


class CollegeWithLocations(CollegeResponse):
    locations: List[CollegeLocationResponse] = []


class DepartmentWithBranches(DepartmentResponse):
    branches: List[BranchResponse] = []


class BranchWithSubjects(BranchResponse):
    subjects: List[SubjectResponse] = []


class AcademicStructure(BaseModel):
    """Complete academic structure for a college"""

    college: CollegeResponse
    departments: List[DepartmentWithBranches] = []
    degrees: List[DegreeResponse] = []

    model_config = ConfigDict(from_attributes=True)


# UTILITY SCHEMAS


class PaginatedResponse(BaseModel):
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    items: List[dict] = Field(..., description="List of items")


class StatusResponse(BaseModel):
    message: str = Field(..., description="Status message")
    success: bool = Field(..., description="Success flag")


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")


# ENUM SCHEMAS


class UserRole(BaseModel):
    """Base user role schema"""

    role: str = Field(..., description="User role")


class CMSUserRoles(BaseModel):
    """CMS specific user roles"""

    SUPER_ADMIN = "super_admin"
    DEPARTMENT_ADMIN = "department_admin"
    LECTURER = "lecturer"
    STAFF_ADMIN = "staff_admin"


class StudentUserRoles(BaseModel):
    """Student specific user roles"""

    STUDENT = "student"


class NotificationTypes(BaseModel):
    """Notification types"""

    INFO = "info"
    WARNING = "warning"
    SUCCESS = "success"
    ERROR = "error"


class EventTypes(BaseModel):
    """Event types"""

    ACADEMIC = "academic"
    CULTURAL = "cultural"
    SPORTS = "sports"
    PLACEMENT = "placement"
    SEMINAR = "seminar"
    WORKSHOP = "workshop"
