from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth import get_admin_user, get_current_active_user, get_principal_user
from app.db.database import get_db
from app.models.cms.models import (
    Batch,
    Branch,
    CMSUser,
    Degree,
    Department,
    Section,
    Subject,
    Timetable,
)
from app.services.cms.permission_service import get_permission_service

router = APIRouter()


# Batch Management
@router.post("/batches", status_code=201)
async def create_batch(
    batch_data: dict,
    current_user: CMSUser = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """
    Create a new batch (Admin+ only)

    ## Request Payload Example:
    ```json
    {
        "departmentId": "123e4567-e89b-12d3-a456-426614174000",
        "branchId": "123e4567-e89b-12d3-a456-426614174001",
        "degreeId": "123e4567-e89b-12d3-a456-426614174002",
        "name": "2024-CSE-A",
        "year": 2024,
        "semester": 1,
        "startDate": 1706764200,
        "endDate": 1722550800
    }
    ```

    ## Indian Context Examples:

    ### Engineering Batch:
    ```json
    {
        "departmentId": "dept-cse-2024",
        "branchId": "branch-cse",
        "degreeId": "degree-btech",
        "name": "BTech-CSE-2024",
        "year": 2024,
        "semester": 1,
        "startDate": 1706764200,
        "endDate": 1722550800
    }
    ```

    ### Medical Batch:
    ```json
    {
        "departmentId": "dept-medicine-2024",
        "branchId": "branch-general-medicine",
        "degreeId": "degree-mbbs",
        "name": "MBBS-2024-Batch1",
        "year": 2024,
        "semester": 1,
        "startDate": 1706764200,
        "endDate": 1875142800
    }
    ```

    ### Commerce Batch:
    ```json
    {
        "departmentId": "dept-commerce-2024",
        "branchId": "branch-accounting",
        "degreeId": "degree-bcom",
        "name": "BCom-Accounting-2024",
        "year": 2024,
        "semester": 1,
        "startDate": 1706764200,
        "endDate": 1801459200
    }
    ```

    ## Response Example:
    ```json
    {
        "id": "batch-123e4567-e89b-12d3-a456-426614174000",
        "name": "BTech-CSE-2024",
        "year": 2024,
        "semester": 1,
        "message": "Batch created successfully"
    }
    ```
    """
    permission_service = get_permission_service(db)

    if not permission_service.has_module_access(
        current_user, "programs_structure", "write"
    ):
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
        end_date=batch_data.get("end_date"),
    )

    db.add(batch)
    db.commit()
    db.refresh(batch)

    return {
        "id": str(batch.id),
        "name": batch.name,
        "year": batch.year,
        "semester": batch.semester,
        "message": "Batch created successfully",
    }


@router.get("/batches")
async def get_batches(
    department_id: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    current_user: CMSUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
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
            "is_active": batch.is_active,
        }
        for batch in batches
    ]


# Section Management
@router.post("/sections", status_code=201)
async def create_section(
    section_data: dict,
    current_user: CMSUser = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """
    Create a new section

    ## Request Payload Example:
    ```json
    {
        "batchId": "batch-123e4567-e89b-12d3-a456-426614174000",
        "name": "Section-A",
        "capacity": 60,
        "classTeacherId": "teacher-123e4567-e89b-12d3-a456-426614174001"
    }
    ```

    ## Indian Context Examples:

    ### Engineering Section:
    ```json
    {
        "batchId": "batch-btech-cse-2024",
        "name": "CSE-A",
        "capacity": 60,
        "classTeacherId": "teacher-dr-rajesh-kumar"
    }
    ```

    ### Medical Section:
    ```json
    {
        "batchId": "batch-mbbs-2024",
        "name": "MBBS-Group-1",
        "capacity": 100,
        "classTeacherId": "teacher-dr-priya-sharma"
    }
    ```

    ### Arts Section:
    ```json
    {
        "batchId": "batch-ba-english-2024",
        "name": "English-A",
        "capacity": 50,
        "classTeacherId": "teacher-prof-anita-singh"
    }
    ```

    ## Response Example:
    ```json
    {
        "id": "section-123e4567-e89b-12d3-a456-426614174000",
        "name": "CSE-A",
        "capacity": 60,
        "message": "Section created successfully"
    }
    ```
    """
    section = Section(
        batch_id=section_data["batch_id"],
        name=section_data["name"],
        capacity=section_data.get("capacity", 60),
        class_teacher_id=section_data.get("class_teacher_id"),
    )

    db.add(section)
    db.commit()
    db.refresh(section)

    return {
        "id": str(section.id),
        "name": section.name,
        "capacity": section.capacity,
        "message": "Section created successfully",
    }


@router.get("/sections")
async def get_sections(
    batch_id: Optional[str] = Query(None),
    current_user: CMSUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
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
            "class_teacher_id": str(section.class_teacher_id)
            if section.class_teacher_id
            else None,
            "is_active": section.is_active,
        }
        for section in sections
    ]


# Subject Management
@router.post("/subjects", status_code=201)
async def create_subject(
    subject_data: dict,
    current_user: CMSUser = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """
    Create a new subject

    ## Request Payload Example:
    ```json
    {
        "department_id": "dept-123e4567-e89b-12d3-a456-426614174000",
        "name": "Data Structures and Algorithms",
        "code": "CS201",
        "credits": 4,
        "semester": 3,
        "subject_type": "theory",
        "description": "Introduction to fundamental data structures and algorithms"
    }
    ```

    ## Indian Context Examples:

    ### Engineering Subjects:
    ```json
    {
        "department_id": "dept-cse",
        "name": "डेटा स्ट्रक्चर और एल्गोरिदम (Data Structures and Algorithms)",
        "code": "CSE301",
        "credits": 4,
        "semester": 3,
        "subject_type": "theory",
        "description": "Comprehensive study of data structures, algorithms and their applications in software development"
    }
    ```

    ### Medical Subjects:
    ```json
    {
        "department_id": "dept-medicine",
        "name": "शरीर विज्ञान (Human Physiology)",
        "code": "MED102",
        "credits": 6,
        "semester": 2,
        "subject_type": "theory",
        "description": "Study of normal functions of human body systems"
    }
    ```

    ### Commerce Subjects:
    ```json
    {
        "department_id": "dept-commerce",
        "name": "व्यावसायिक गणित (Business Mathematics)",
        "code": "COM101",
        "credits": 3,
        "semester": 1,
        "subject_type": "theory",
        "description": "Mathematical concepts and their application in business scenarios"
    }
    ```

    ### Laboratory Subjects:
    ```json
    {
        "department_id": "dept-cse",
        "name": "कंप्यूटर प्रोग्रामिंग लैब (Computer Programming Lab)",
        "code": "CSE191",
        "credits": 2,
        "semester": 1,
        "subject_type": "lab",
        "description": "Hands-on programming experience in C/C++ and Python"
    }
    ```

    ## Response Example:
    ```json
    {
        "id": "subject-123e4567-e89b-12d3-a456-426614174000",
        "name": "डेटा स्ट्रक्चर और एल्गोरिदम (Data Structures and Algorithms)",
        "code": "CSE301",
        "semester": 3,
        "message": "Subject created successfully"
    }
    ```
    """
    permission_service = get_permission_service(db)

    if not permission_service.has_module_access(
        current_user, "programs_structure", "write"
    ):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    subject = Subject(
        college_id=current_user.college_id,
        department_id=subject_data["department_id"],
        name=subject_data["name"],
        code=subject_data["code"],
        credits=subject_data.get("credits", 3),
        semester=subject_data["semester"],
        subject_type=subject_data.get("subject_type", "theory"),
        description=subject_data.get("description"),
    )

    db.add(subject)
    db.commit()
    db.refresh(subject)

    return {
        "id": str(subject.id),
        "name": subject.name,
        "code": subject.code,
        "semester": subject.semester,
        "message": "Subject created successfully",
    }


@router.get("/subjects")
async def get_subjects(
    department_id: Optional[str] = Query(None),
    semester: Optional[int] = Query(None),
    current_user: CMSUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
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
            "is_active": subject.is_active,
        }
        for subject in subjects
    ]


# Timetable Management
@router.post("/timetables", status_code=201)
async def create_timetable_entry(
    timetable_data: dict,
    current_user: CMSUser = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """
    Create a new timetable entry

    ## Request Payload Example:
    ```json
    {
        "section_id": "section-123e4567-e89b-12d3-a456-426614174000",
        "subject_id": "subject-123e4567-e89b-12d3-a456-426614174001",
        "teacher_id": "teacher-123e4567-e89b-12d3-a456-426614174002",
        "day_of_week": "monday",
        "start_time": "09:00",
        "end_time": "10:00",
        "room_number": "CS-101"
    }
    ```

    ## Indian Context Examples:

    ### Engineering Timetable:
    ```json
    {
        "section_id": "section-btech-cse-a",
        "subject_id": "subject-data-structures",
        "teacher_id": "teacher-dr-rajesh-kumar",
        "day_of_week": "monday",
        "start_time": "09:00",
        "end_time": "10:00",
        "room_number": "CS-101"
    }
    ```

    ### Medical Timetable:
    ```json
    {
        "section_id": "section-mbbs-batch1",
        "subject_id": "subject-anatomy",
        "teacher_id": "teacher-dr-priya-sharma",
        "day_of_week": "tuesday",
        "start_time": "10:00",
        "end_time": "12:00",
        "room_number": "Anatomy-Hall-1"
    }
    ```

    ### Laboratory Schedule:
    ```json
    {
        "section_id": "section-btech-cse-a",
        "subject_id": "subject-programming-lab",
        "teacher_id": "teacher-prof-anita-singh",
        "day_of_week": "wednesday",
        "start_time": "14:00",
        "end_time": "17:00",
        "room_number": "Computer-Lab-2"
    }
    ```

    ### Multiple Sessions (Same Day):
    ```json
    [
        {
            "section_id": "section-bcom-a",
            "subject_id": "subject-business-maths",
            "teacher_id": "teacher-prof-suresh-gupta",
            "day_of_week": "thursday",
            "start_time": "09:00",
            "end_time": "10:00",
            "room_number": "Commerce-101"
        },
        {
            "section_id": "section-bcom-a",
            "subject_id": "subject-accounting",
            "teacher_id": "teacher-ca-meera-patel",
            "day_of_week": "thursday",
            "start_time": "10:00",
            "end_time": "11:00",
            "room_number": "Commerce-101"
        }
    ]
    ```

    ## Response Example:
    ```json
    {
        "id": "timetable-123e4567-e89b-12d3-a456-426614174000",
        "day_of_week": "monday",
        "start_time": "09:00",
        "end_time": "10:00",
        "message": "Timetable entry created successfully"
    }
    ```
    """
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
        room_number=timetable_data.get("room_number"),
    )

    db.add(timetable)
    db.commit()
    db.refresh(timetable)

    return {
        "id": str(timetable.id),
        "day_of_week": timetable.day_of_week,
        "start_time": timetable.start_time,
        "end_time": timetable.end_time,
        "message": "Timetable entry created successfully",
    }


@router.get("/timetables")
async def get_timetable(
    section_id: Optional[str] = Query(None),
    teacher_id: Optional[str] = Query(None),
    day_of_week: Optional[str] = Query(None),
    current_user: CMSUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
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
            "is_active": tt.is_active,
        }
        for tt in timetables
    ]


# Cross-Department Teaching Assignment
@router.post("/assign-cross-department-teaching")
async def assign_cross_department_teaching(
    assignment_data: dict,
    current_user: CMSUser = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """
    Assign teacher to subjects in other departments

    ## Request Payload Example:
    ```json
    {
        "teacher_id": "teacher-123e4567-e89b-12d3-a456-426614174000",
        "department_id": "dept-123e4567-e89b-12d3-a456-426614174001",
        "subject_ids": [
            "subject-123e4567-e89b-12d3-a456-426614174002",
            "subject-123e4567-e89b-12d3-a456-426614174003"
        ]
    }
    ```

    ## Indian Context Examples:

    ### Mathematics Teacher Teaching Across Departments:
    ```json
    {
        "teacher_id": "teacher-dr-suresh-sharma",
        "department_id": "dept-computer-science",
        "subject_ids": [
            "subject-discrete-mathematics",
            "subject-statistics-for-cs"
        ]
    }
    ```

    ### English Teacher for Technical Communication:
    ```json
    {
        "teacher_id": "teacher-prof-kavita-nair",
        "department_id": "dept-mechanical-engineering",
        "subject_ids": [
            "subject-technical-english",
            "subject-communication-skills"
        ]
    }
    ```

    ### Physics Teacher for Multiple Engineering Branches:
    ```json
    {
        "teacher_id": "teacher-dr-rajesh-yadav",
        "department_id": "dept-electrical-engineering",
        "subject_ids": [
            "subject-engineering-physics",
            "subject-electromagnetic-theory"
        ]
    }
    ```

    ### Guest Faculty Assignment:
    ```json
    {
        "teacher_id": "teacher-ca-priya-singh",
        "department_id": "dept-management",
        "subject_ids": [
            "subject-financial-accounting",
            "subject-cost-accounting",
            "subject-taxation"
        ]
    }
    ```

    ## Response Example:
    ```json
    {
        "message": "Cross-department teaching assigned successfully",
        "teacher_id": "teacher-dr-suresh-sharma",
        "managed_departments": [
            "dept-mathematics",
            "dept-computer-science"
        ],
        "teaching_subjects": [
            "subject-calculus",
            "subject-discrete-mathematics",
            "subject-statistics-for-cs"
        ]
    }
    ```
    """
    teacher = (
        db.query(CMSUser).filter(CMSUser.id == assignment_data["teacher_id"]).first()
    )
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    if teacher.role != "staff":
        raise HTTPException(
            status_code=400,
            detail="Only staff can be assigned cross-department teaching",
        )

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
        "teaching_subjects": teacher.teaching_subjects,
    }


@router.get("/teacher-assignments/{teacher_id}")
async def get_teacher_assignments(
    teacher_id: str,
    current_user: CMSUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get teacher's cross-department assignments"""
    teacher = db.query(CMSUser).filter(CMSUser.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    # Get subjects they're teaching
    subject_ids = teacher.teaching_subjects or []
    subjects = (
        db.query(Subject).filter(Subject.id.in_(subject_ids)).all()
        if subject_ids
        else []
    )

    return {
        "teacher_id": str(teacher.id),
        "primary_department_id": str(teacher.department_id)
        if teacher.department_id
        else None,
        "managed_departments": teacher.managed_departments or [],
        "teaching_subjects": [
            {
                "id": str(subject.id),
                "name": subject.name,
                "code": subject.code,
                "department_id": str(subject.department_id),
            }
            for subject in subjects
        ],
    }
