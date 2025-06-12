from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from app.schemas.student.users import StudentUserCreate, StudentUserUpdate, StudentUserResponse
class CollegeStudentCreate(BaseModel):
    college_id: UUID
    student_id: str
    full_name: str
    email: str
    phone: Optional[str] = None
    batch_year: Optional[int] = None
    branch_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    degree_id: Optional[UUID] = None
    gender: Optional[str] = None
    username: str
    password: str

CollegeStudentUpdate = StudentUserUpdate
CollegeStudentResponse = StudentUserResponse

class PaginatedResponse(BaseModel):
    total: int
    page: int
    per_page: int
    items: List[StudentUserResponse]