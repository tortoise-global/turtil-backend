from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.auth import get_current_user
from app.db.database import get_db
from app.models.models import CollegeStudent
from app.schemas.college_students import CollegeStudentCreate, CollegeStudentUpdate, CollegeStudentResponse, PaginatedResponse

router = APIRouter()


@router.post("/college-students", response_model=CollegeStudentResponse)
async def create_student(
    student_data: CollegeStudentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    db_student = CollegeStudent(**student_data.model_dump())
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student


@router.get("/college-students", response_model=PaginatedResponse)
async def get_students(
    college_id: Optional[str] = Query(None),
    college_short_name: Optional[str] = Query(None),
    student_id: Optional[str] = Query(None),
    student_name: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    phone: Optional[str] = Query(None),
    degree: Optional[str] = Query(None),
    batch: Optional[str] = Query(None),
    branch: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    gender: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    query = db.query(CollegeStudent)
    
    if college_id:
        query = query.filter(CollegeStudent.college_id == college_id)
    if college_short_name:
        query = query.filter(CollegeStudent.college_short_name == college_short_name)
    if student_id:
        query = query.filter(CollegeStudent.student_id == student_id)
    if student_name:
        query = query.filter(CollegeStudent.student_name.ilike(f"%{student_name}%"))
    if email:
        query = query.filter(CollegeStudent.email == email)
    if phone:
        query = query.filter(CollegeStudent.phone == phone)
    if degree:
        query = query.filter(CollegeStudent.degree == degree)
    if batch:
        query = query.filter(CollegeStudent.batch == batch)
    if branch:
        query = query.filter(CollegeStudent.branch == branch)
    if section:
        query = query.filter(CollegeStudent.section == section)
    if gender:
        query = query.filter(CollegeStudent.gender == gender)
    
    total = query.count()
    offset = (page - 1) * page_size
    students = query.offset(offset).limit(page_size).all()
    
    return PaginatedResponse(
        total=total,
        page=page,
        per_page=page_size,
        items=students
    )


@router.get("/college-students/{student_id}", response_model=CollegeStudentResponse)
async def get_student(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    student = db.query(CollegeStudent).filter(CollegeStudent.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.put("/college-students/{student_id}", response_model=CollegeStudentResponse)
async def update_student(
    student_id: str,
    student_data: CollegeStudentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    student = db.query(CollegeStudent).filter(CollegeStudent.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    for field, value in student_data.model_dump(exclude_unset=True).items():
        setattr(student, field, value)
    
    db.commit()
    db.refresh(student)
    return student


@router.delete("/college-students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    student = db.query(CollegeStudent).filter(CollegeStudent.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    db.delete(student)
    db.commit()


@router.get("/search-students", response_model=List[CollegeStudentResponse])
async def search_students(
    query: Optional[str] = Query(None),
    college_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    db_query = db.query(CollegeStudent)
    
    if college_id:
        db_query = db_query.filter(CollegeStudent.college_id == college_id)
    
    if query:
        db_query = db_query.filter(
            (CollegeStudent.student_id.ilike(f"%{query}%")) |
            (CollegeStudent.student_name.ilike(f"%{query}%"))
        )
    
    students = db_query.all()
    return students