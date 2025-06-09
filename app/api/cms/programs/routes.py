from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.core.auth import get_current_active_user, get_admin_user
from app.models.cms.models import User, Institute
from app.models.cms.programs import Program, Course
from app.schemas.cms.programs import (
    Program as ProgramSchema,
    ProgramCreate,
    ProgramUpdate,
    ProgramWithCourses,
    Course as CourseSchema,
    CourseCreate,
    CourseUpdate
)

router = APIRouter()


# Program Routes
@router.get("/", response_model=List[ProgramSchema])
def get_programs(
    skip: int = 0,
    limit: int = 100,
    institute_id: Optional[int] = Query(None),
    degree_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(Program)
    
    if institute_id:
        query = query.filter(Program.institute_id == institute_id)
    if degree_type:
        query = query.filter(Program.degree_type == degree_type)
    if is_active is not None:
        query = query.filter(Program.is_active == is_active)
    
    programs = query.offset(skip).limit(limit).all()
    return programs


@router.get("/{program_id}", response_model=ProgramWithCourses)
def get_program(
    program_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    program = db.query(Program).filter(Program.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    return program


@router.post("/", response_model=ProgramSchema)
def create_program(
    program: ProgramCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    # Check if institute exists
    institute = db.query(Institute).filter(Institute.id == program.institute_id).first()
    if not institute:
        raise HTTPException(status_code=404, detail="Institute not found")
    
    # Check if program code already exists
    existing_program = db.query(Program).filter(Program.code == program.code).first()
    if existing_program:
        raise HTTPException(status_code=400, detail="Program code already exists")
    
    db_program = Program(**program.dict())
    db.add(db_program)
    db.commit()
    db.refresh(db_program)
    return db_program


@router.put("/{program_id}", response_model=ProgramSchema)
def update_program(
    program_id: int,
    program_update: ProgramUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    db_program = db.query(Program).filter(Program.id == program_id).first()
    if not db_program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    update_data = program_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_program, field, value)
    
    db.commit()
    db.refresh(db_program)
    return db_program


@router.delete("/{program_id}")
def delete_program(
    program_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    db_program = db.query(Program).filter(Program.id == program_id).first()
    if not db_program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    db.delete(db_program)
    db.commit()
    return {"message": "Program deleted successfully"}


# Course Routes
@router.get("/{program_id}/courses", response_model=List[CourseSchema])
def get_program_courses(
    program_id: int,
    semester: Optional[int] = Query(None),
    course_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Check if program exists
    program = db.query(Program).filter(Program.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    query = db.query(Course).filter(Course.program_id == program_id)
    
    if semester:
        query = query.filter(Course.semester == semester)
    if course_type:
        query = query.filter(Course.course_type == course_type)
    
    courses = query.all()
    return courses


@router.post("/{program_id}/courses", response_model=CourseSchema)
def create_course(
    program_id: int,
    course: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    # Check if program exists
    program = db.query(Program).filter(Program.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    # Ensure course is associated with the correct program
    course.program_id = program_id
    
    # Check if course code already exists
    existing_course = db.query(Course).filter(Course.code == course.code).first()
    if existing_course:
        raise HTTPException(status_code=400, detail="Course code already exists")
    
    db_course = Course(**course.dict())
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course


@router.get("/courses/{course_id}", response_model=CourseSchema)
def get_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.put("/courses/{course_id}", response_model=CourseSchema)
def update_course(
    course_id: int,
    course_update: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    db_course = db.query(Course).filter(Course.id == course_id).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    update_data = course_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_course, field, value)
    
    db.commit()
    db.refresh(db_course)
    return db_course


@router.delete("/courses/{course_id}")
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    db_course = db.query(Course).filter(Course.id == course_id).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    db.delete(db_course)
    db.commit()
    return {"message": "Course deleted successfully"}