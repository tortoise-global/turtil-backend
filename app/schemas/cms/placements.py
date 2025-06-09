from pydantic import BaseModel, EmailStr, validator
from datetime import datetime, date
from typing import Optional, List
import json


class CompanyBase(BaseModel):
    name: str
    industry: str
    description: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    company_size: Optional[str] = None
    company_type: Optional[str] = None
    
    @validator('company_size')
    def validate_company_size(cls, v):
        if v and v not in ['Startup', 'Small', 'Medium', 'Large', 'Enterprise']:
            raise ValueError("Invalid company size")
        return v
    
    @validator('company_type')
    def validate_company_type(cls, v):
        if v and v not in ['Private', 'Public', 'Government', 'NGO']:
            raise ValueError("Invalid company type")
        return v


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    company_size: Optional[str] = None
    company_type: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class Company(CompanyBase):
    id: int
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class PlacementDriveBase(BaseModel):
    title: str
    description: Optional[str] = None
    company_id: int
    institute_id: int
    job_role: str
    job_type: str
    location: str
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    currency: str = "INR"
    eligible_programs: Optional[str] = None
    min_cgpa: Optional[float] = None
    max_backlogs: int = 0
    required_skills: Optional[str] = None
    registration_start: datetime
    registration_end: datetime
    drive_date: date
    
    @validator('job_type')
    def validate_job_type(cls, v):
        if v not in ['Full-time', 'Internship', 'Part-time']:
            raise ValueError("Invalid job type")
        return v
    
    @validator('min_cgpa')
    def validate_cgpa(cls, v):
        if v and (v < 0 or v > 10):
            raise ValueError("CGPA must be between 0 and 10")
        return v
    
    @validator('registration_end')
    def validate_registration_dates(cls, v, values):
        if 'registration_start' in values and v <= values['registration_start']:
            raise ValueError("Registration end must be after registration start")
        return v


class PlacementDriveCreate(PlacementDriveBase):
    pass


class PlacementDriveUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    job_role: Optional[str] = None
    job_type: Optional[str] = None
    location: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    eligible_programs: Optional[str] = None
    min_cgpa: Optional[float] = None
    max_backlogs: Optional[int] = None
    required_skills: Optional[str] = None
    registration_start: Optional[datetime] = None
    registration_end: Optional[datetime] = None
    drive_date: Optional[date] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None


class PlacementDrive(PlacementDriveBase):
    id: int
    status: str
    is_active: bool
    total_registered: int
    total_selected: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class PlacementApplicationBase(BaseModel):
    placement_drive_id: int
    student_email: EmailStr
    student_name: str
    student_program: str
    resume_url: Optional[str] = None
    cover_letter: Optional[str] = None
    cgpa: float
    current_backlogs: int = 0
    skills: Optional[str] = None
    
    @validator('cgpa')
    def validate_cgpa(cls, v):
        if v < 0 or v > 10:
            raise ValueError("CGPA must be between 0 and 10")
        return v


class PlacementApplicationCreate(PlacementApplicationBase):
    pass


class PlacementApplicationUpdate(BaseModel):
    resume_url: Optional[str] = None
    cover_letter: Optional[str] = None
    cgpa: Optional[float] = None
    current_backlogs: Optional[int] = None
    skills: Optional[str] = None
    status: Optional[str] = None
    interview_date: Optional[datetime] = None
    interview_feedback: Optional[str] = None
    final_result: Optional[str] = None


class PlacementApplication(PlacementApplicationBase):
    id: int
    status: str
    interview_date: Optional[datetime]
    interview_feedback: Optional[str]
    final_result: Optional[str]
    applied_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class PlacementDriveWithDetails(PlacementDrive):
    company: Company
    applications: List[PlacementApplication] = []


class PlacementStats(BaseModel):
    total_companies: int
    active_drives: int
    total_applications: int
    total_placements: int
    placement_percentage: float