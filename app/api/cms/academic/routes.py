from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.auth import get_current_active_user, get_principal_user, get_admin_user
from app.db.database import get_db
from app.models.cms.models import (
    CMSUser, Batch, Section, Subject, Timetable, Department, Branch, Degree
)
from app.services.cms.permission_service import get_permission_service

router = APIRouter()


# Batch Management
@router.post("/batches", status_code=201)
async def create_batch(
    batch_data: dict,
    current_user: CMSUser = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new batch (Admin+ only)"""
    permission_service = get_permission_service(db)
    
    if not permission_service.has_module_access(current_user, "programs_structure", "write"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    batch = Batch(
        college_id=current_user.college_id,
        department_id=batch_data["department_id"],
        branch_id=batch_data["branch_id"],
        degree_id=batch_data["degree_id"],
        name=batch_data["name"],
        year=batch_data["year"],
        semester=batch_data["semester"],
        start_date=batch_data.get("start_date"),
        end_date=batch_data.get("end_date")
    )
    
    db.add(batch)
    db.commit()
    db.refresh(batch)
    
    return {
        "id": str(batch.id),
        "name": batch.name,
        "year": batch.year,
        "semester": batch.semester,
        "message": "Batch created successfully"
    }


@router.get("/batches")
async def get_batches(
    department_id: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    current_user: CMSUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get batches with filtering"""
    permission_service = get_permission_service(db)
    accessible_dept_ids = permission_service.get_accessible_departments(current_user)
    
    query = db.query(Batch).filter(Batch.department_id.in_(accessible_dept_ids))
    
    if department_id:
        query = query.filter(Batch.department_id == department_id)
    if year:
        query = query.filter(Batch.year == year)
    
    batches = query.all()
    
    return [
        {
            "id": str(batch.id),
            "name": batch.name,
            "year": batch.year,
            "semester": batch.semester,
            "department_id": str(batch.department_id),
            "branch_id": str(batch.branch_id),
            "is_active": batch.is_active
        }
        for batch in batches
    ]


# Section Management
@router.post("/sections", status_code=201)
async def create_section(
    section_data: dict,
    current_user: CMSUser = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new section"""
    section = Section(
        batch_id=section_data["batch_id"],
        name=section_data["name"],
        capacity=section_data.get("capacity", 60),
        class_teacher_id=section_data.get("class_teacher_id")
    )
    
    db.add(section)
    db.commit()
    db.refresh(section)
    
    return {
        "id": str(section.id),
        "name": section.name,
        "capacity": section.capacity,
        "message": "Section created successfully"
    }


@router.get("/sections")
async def get_sections(
    batch_id: Optional[str] = Query(None),
    current_user: CMSUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get sections with filtering"""
    query = db.query(Section)
    
    if batch_id:
        query = query.filter(Section.batch_id == batch_id)
    
    sections = query.all()
    
    return [
        {
            "id": str(section.id),
            "name": section.name,
            "batch_id": str(section.batch_id),
            "capacity": section.capacity,
            "current_strength": section.current_strength,
            "class_teacher_id": str(section.class_teacher_id) if section.class_teacher_id else None,
            "is_active": section.is_active
        }
        for section in sections
    ]


# Subject Management
@router.post("/subjects", status_code=201)
async def create_subject(
    subject_data: dict,
    current_user: CMSUser = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new subject"""
    permission_service = get_permission_service(db)
    
    if not permission_service.has_module_access(current_user, "programs_structure", "write"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    subject = Subject(
        college_id=current_user.college_id,
        department_id=subject_data["department_id"],
        name=subject_data["name"],
        code=subject_data["code"],
        credits=subject_data.get("credits", 3),
        semester=subject_data["semester"],
        subject_type=subject_data.get("subject_type", "theory"),
        description=subject_data.get("description")
    )
    
    db.add(subject)
    db.commit()
    db.refresh(subject)
    
    return {
        "id": str(subject.id),
        "name": subject.name,
        "code": subject.code,
        "semester": subject.semester,
        "message": "Subject created successfully"
    }


@router.get("/subjects")
async def get_subjects(
    department_id: Optional[str] = Query(None),
    semester: Optional[int] = Query(None),
    current_user: CMSUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get subjects with filtering"""
    permission_service = get_permission_service(db)
    accessible_dept_ids = permission_service.get_accessible_departments(current_user)
    
    query = db.query(Subject).filter(Subject.department_id.in_(accessible_dept_ids))
    
    if department_id:
        query = query.filter(Subject.department_id == department_id)
    if semester:
        query = query.filter(Subject.semester == semester)
    
    subjects = query.all()
    
    return [
        {
            "id": str(subject.id),
            "name": subject.name,
            "code": subject.code,
            "credits": subject.credits,
            "semester": subject.semester,
            "subject_type": subject.subject_type,
            "department_id": str(subject.department_id),
            "is_active": subject.is_active
        }
        for subject in subjects
    ]


# Timetable Management
@router.post("/timetables", status_code=201)
async def create_timetable_entry(
    timetable_data: dict,
    current_user: CMSUser = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new timetable entry"""
    permission_service = get_permission_service(db)
    
    if not permission_service.has_module_access(current_user, "timetable", "write"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    timetable = Timetable(
        college_id=current_user.college_id,
        section_id=timetable_data["section_id"],
        subject_id=timetable_data["subject_id"],
        teacher_id=timetable_data["teacher_id"],
        day_of_week=timetable_data["day_of_week"],
        start_time=timetable_data["start_time"],
        end_time=timetable_data["end_time"],
        room_number=timetable_data.get("room_number")
    )
    
    db.add(timetable)
    db.commit()
    db.refresh(timetable)
    
    return {
        "id": str(timetable.id),
        "day_of_week": timetable.day_of_week,
        "start_time": timetable.start_time,
        "end_time": timetable.end_time,
        "message": "Timetable entry created successfully"
    }


@router.get("/timetables")
async def get_timetable(
    section_id: Optional[str] = Query(None),
    teacher_id: Optional[str] = Query(None),
    day_of_week: Optional[str] = Query(None),
    current_user: CMSUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get timetable entries with filtering"""
    permission_service = get_permission_service(db)
    
    if not permission_service.has_module_access(current_user, "timetable", "read"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    query = db.query(Timetable).filter(Timetable.college_id == current_user.college_id)
    
    if section_id:
        query = query.filter(Timetable.section_id == section_id)
    if teacher_id:
        query = query.filter(Timetable.teacher_id == teacher_id)
    if day_of_week:
        query = query.filter(Timetable.day_of_week == day_of_week)
    
    timetables = query.all()
    
    return [
        {
            "id": str(tt.id),
            "section_id": str(tt.section_id),
            "subject_id": str(tt.subject_id),
            "teacher_id": str(tt.teacher_id),
            "day_of_week": tt.day_of_week,
            "start_time": tt.start_time,
            "end_time": tt.end_time,
            "room_number": tt.room_number,
            "is_active": tt.is_active
        }
        for tt in timetables
    ]


# Cross-Department Teaching Assignment
@router.post("/assign-cross-department-teaching")
async def assign_cross_department_teaching(
    assignment_data: dict,
    current_user: CMSUser = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Assign teacher to subjects in other departments"""
    teacher = db.query(CMSUser).filter(CMSUser.id == assignment_data["teacher_id"]).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    if teacher.role != "staff":
        raise HTTPException(status_code=400, detail="Only staff can be assigned cross-department teaching")
    
    # Update managed departments
    managed_depts = teacher.managed_departments or []
    new_dept = assignment_data["department_id"]
    
    if new_dept not in managed_depts:
        managed_depts.append(new_dept)
        teacher.managed_departments = managed_depts
    
    # Update teaching subjects
    teaching_subjects = teacher.teaching_subjects or []
    new_subjects = assignment_data.get("subject_ids", [])
    
    for subject_id in new_subjects:
        if subject_id not in teaching_subjects:
            teaching_subjects.append(subject_id)
    
    teacher.teaching_subjects = teaching_subjects
    
    db.commit()
    
    return {
        "message": "Cross-department teaching assigned successfully",
        "teacher_id": str(teacher.id),
        "managed_departments": teacher.managed_departments,
        "teaching_subjects": teacher.teaching_subjects
    }


@router.get("/teacher-assignments/{teacher_id}")
async def get_teacher_assignments(
    teacher_id: str,
    current_user: CMSUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get teacher's cross-department assignments"""
    teacher = db.query(CMSUser).filter(CMSUser.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    # Get subjects they're teaching
    subject_ids = teacher.teaching_subjects or []
    subjects = db.query(Subject).filter(Subject.id.in_(subject_ids)).all() if subject_ids else []
    
    return {
        "teacher_id": str(teacher.id),
        "primary_department_id": str(teacher.department_id) if teacher.department_id else None,
        "managed_departments": teacher.managed_departments or [],
        "teaching_subjects": [
            {
                "id": str(subject.id),
                "name": subject.name,
                "code": subject.code,
                "department_id": str(subject.department_id)
            }
            for subject in subjects
        ]
    }