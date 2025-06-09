from pydantic import BaseModel, validator
from datetime import datetime
from typing import Optional, List
from app.core.validators import validate_institute_code


class ProgramBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    duration_years: int
    degree_type: str
    department: str
    institute_id: int
    total_credits: Optional[int] = None
    admission_capacity: Optional[int] = None
    
    @validator('code')
    def validate_program_code(cls, v):
        if len(v) < 2 or len(v) > 15:
            raise ValueError("Program code must be between 2 and 15 characters")
        return v.upper()
    
    @validator('degree_type')
    def validate_degree_type(cls, v):
        allowed_types = ['Bachelor', 'Master', 'PhD', 'Diploma', 'Certificate']
        if v not in allowed_types:
            raise ValueError(f"Degree type must be one of: {', '.join(allowed_types)}")
        return v
    
    @validator('duration_years')
    def validate_duration(cls, v):
        if v < 1 or v > 10:
            raise ValueError("Duration must be between 1 and 10 years")
        return v


class ProgramCreate(ProgramBase):
    pass


class ProgramUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    duration_years: Optional[int] = None
    degree_type: Optional[str] = None
    department: Optional[str] = None
    total_credits: Optional[int] = None
    admission_capacity: Optional[int] = None
    current_enrolled: Optional[int] = None
    is_active: Optional[bool] = None
    is_admissions_open: Optional[bool] = None


class Program(ProgramBase):
    id: int
    current_enrolled: int
    is_active: bool
    is_admissions_open: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class CourseBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    credits: int
    semester: int
    program_id: int
    course_type: str
    prerequisites: Optional[str] = None
    
    @validator('code')
    def validate_course_code(cls, v):
        if len(v) < 3 or len(v) > 10:
            raise ValueError("Course code must be between 3 and 10 characters")
        return v.upper()
    
    @validator('course_type')
    def validate_course_type(cls, v):
        allowed_types = ['Core', 'Elective', 'Lab', 'Project']
        if v not in allowed_types:
            raise ValueError(f"Course type must be one of: {', '.join(allowed_types)}")
        return v
    
    @validator('credits')
    def validate_credits(cls, v):
        if v < 1 or v > 10:
            raise ValueError("Credits must be between 1 and 10")
        return v
    
    @validator('semester')
    def validate_semester(cls, v):
        if v < 1 or v > 20:
            raise ValueError("Semester must be between 1 and 20")
        return v


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    credits: Optional[int] = None
    semester: Optional[int] = None
    course_type: Optional[str] = None
    prerequisites: Optional[str] = None
    is_active: Optional[bool] = None


class Course(CourseBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ProgramWithCourses(Program):
    courses: List[Course] = []