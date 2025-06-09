from pydantic import BaseModel
from typing import Optional, List


class CollegeStudentCreate(BaseModel):
    collegeId: str
    collegeShortName: str
    collegeName: str
    studentId: str
    studentName: str
    email: str
    phone: str
    degree: str
    batch: str
    branch: str
    section: str
    gender: str


class CollegeStudentUpdate(BaseModel):
    collegeId: Optional[str] = None
    collegeShortName: Optional[str] = None
    collegeName: Optional[str] = None
    studentId: Optional[str] = None
    studentName: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    degree: Optional[str] = None
    batch: Optional[str] = None
    branch: Optional[str] = None
    section: Optional[str] = None
    gender: Optional[str] = None


class CollegeStudentResponse(BaseModel):
    id: str
    collegeId: str
    collegeShortName: str
    collegeName: str
    studentId: str
    studentName: str
    email: str
    phone: str
    degree: str
    batch: str
    branch: str
    section: str
    gender: str
    createdAt: int
    updatedAt: Optional[int] = None

    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel):
    total: int
    page: int
    per_page: int
    items: List[CollegeStudentResponse]