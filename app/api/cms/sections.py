from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.security import HTTPBearer
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate as sqlalchemy_paginate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import Optional, List

from app.database import get_db
from app.models.staff import Staff
from app.models.term import Term
from app.models.graduation import Graduation
from app.models.degree import Degree
from app.models.branch import Branch
from app.models.subject import Subject
from app.models.section import Section
from app.models.section_subject import SectionSubject
from app.schemas.academic_program_schemas import (
    CreateSectionRequest,
    UpdateSectionRequest,
    SectionResponse,
    SectionWithDetailsResponse,
    SectionActionResponse,
    AssignSubjectsRequest,
    AssignTeacherRequest,
    SectionSubjectResponse,
    AssignmentActionResponse,
)
from .deps import get_current_staff

router = APIRouter(prefix="/cms/sections", tags=["CMS Sections Management"])
security = HTTPBearer(auto_error=False)


@router.get("", response_model=Page[SectionWithDetailsResponse], dependencies=[Depends(security)])
async def get_sections(
    branch_id: Optional[str] = Query(None, description="Filter by branch ID"),
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Get paginated list of sections."""
    try:
        # Build base query
        query = (select(Section)
                .join(Branch)
                .join(Degree)
                .join(Graduation)
                .join(Term)
                .where(Term.college_id == current_staff.college_id))
        
        if branch_id:
            query = query.where(Section.branch_id == branch_id)
        
        query = query.order_by(Section.sequence_order, Section.section_name)
        paginated_result = await sqlalchemy_paginate(db, query)

        # Add additional details
        section_responses = []
        for section in paginated_result.items:
            # Get branch name
            branch_result = await db.execute(
                select(Branch.branch_name).where(Branch.branch_id == section.branch_id)
            )
            branch_name = branch_result.scalar() or ""

            # Get class teacher name
            class_teacher_name = None
            if section.class_teacher_id:
                teacher_result = await db.execute(
                    select(Staff.full_name).where(Staff.staff_id == section.class_teacher_id)
                )
                class_teacher_name = teacher_result.scalar()

            # Count assigned subjects
            assigned_subjects_result = await db.execute(
                select(func.count(SectionSubject.section_subject_id))
                .where(and_(
                    SectionSubject.section_id == section.section_id,
                    SectionSubject.is_active == True
                ))
            )
            assigned_subjects_count = assigned_subjects_result.scalar() or 0

            section_dict = section.to_dict()
            section_responses.append(
                SectionWithDetailsResponse(
                    **section_dict,
                    branchName=branch_name,
                    classTeacherName=class_teacher_name,
                    assignedSubjectsCount=assigned_subjects_count,
                )
            )

        return Page(
            items=section_responses,
            total=paginated_result.total,
            page=paginated_result.page,
            size=paginated_result.size,
            pages=paginated_result.pages,
        )

    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Get sections", {"staff_id": str(current_staff.staff_id), "college_id": str(current_staff.college_id)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("", response_model=SectionActionResponse, dependencies=[Depends(security)])
async def create_section(
    request: CreateSectionRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Create a new section. Only Principal and College Admin can create sections."""
    try:
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                              detail="Only Principal and College Admin can create sections")

        # Verify branch exists and belongs to college
        branch_result = await db.execute(
            select(Branch)
            .join(Degree)
            .join(Graduation)
            .join(Term)
            .where(and_(
                Branch.branch_id == request.branch_id,
                Term.college_id == current_staff.college_id,
            ))
        )
        branch = branch_result.scalar_one_or_none()
        if not branch:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")

        # Verify class teacher if provided
        if request.class_teacher_id:
            teacher_result = await db.execute(
                select(Staff).where(and_(
                    Staff.staff_id == request.class_teacher_id,
                    Staff.college_id == current_staff.college_id,
                ))
            )
            if not teacher_result.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class teacher not found")

        # Check for duplicate section code
        existing_section = await db.execute(
            select(Section).where(and_(
                Section.branch_id == request.branch_id,
                Section.section_code == request.section_code,
            ))
        )
        if existing_section.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                              detail=f"Section with code '{request.section_code}' already exists")

        # Create new section
        new_section = Section(
            section_name=request.section_name,
            section_code=request.section_code,
            description=request.description,
            student_capacity=request.student_capacity,
            sequence_order=request.sequence_order,
            branch_id=request.branch_id,
            class_teacher_id=request.class_teacher_id,
        )

        db.add(new_section)
        await db.commit()
        await db.refresh(new_section)

        return SectionActionResponse(
            success=True,
            message=f"Section '{request.section_name}' created successfully",
            sectionId=str(new_section.section_id),
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Create section", {"staff_id": str(current_staff.staff_id), "section_name": request.section_name, "branch_id": str(request.branch_id)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/{section_id}", response_model=SectionResponse, dependencies=[Depends(security)])
async def get_section(
    section_id: str,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Get specific section by ID."""
    try:
        result = await db.execute(
            select(Section)
            .join(Branch)
            .join(Degree)
            .join(Graduation)
            .join(Term)
            .where(and_(
                Section.section_id == section_id,
                Term.college_id == current_staff.college_id,
            ))
        )
        section = result.scalar_one_or_none()
        if not section:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

        return SectionResponse(**section.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Get section by ID", {"staff_id": str(current_staff.staff_id), "section_id": section_id}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.put("/{section_id}", response_model=SectionActionResponse, dependencies=[Depends(security)])
async def update_section(
    section_id: str,
    request: UpdateSectionRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Update a section. Only Principal and College Admin can update sections."""
    try:
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                              detail="Only Principal and College Admin can update sections")

        # Get section
        result = await db.execute(
            select(Section)
            .join(Branch)
            .join(Degree)
            .join(Graduation)
            .join(Term)
            .where(and_(
                Section.section_id == section_id,
                Term.college_id == current_staff.college_id,
            ))
        )
        section = result.scalar_one_or_none()
        if not section:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

        # Verify class teacher if provided
        if request.class_teacher_id:
            teacher_result = await db.execute(
                select(Staff).where(and_(
                    Staff.staff_id == request.class_teacher_id,
                    Staff.college_id == current_staff.college_id,
                ))
            )
            if not teacher_result.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class teacher not found")

        # Update fields
        if request.section_name is not None:
            section.section_name = request.section_name
        if request.description is not None:
            section.description = request.description
        if request.student_capacity is not None:
            section.student_capacity = request.student_capacity
        if request.sequence_order is not None:
            section.sequence_order = request.sequence_order
        if request.class_teacher_id is not None:
            section.class_teacher_id = request.class_teacher_id

        await db.commit()

        return SectionActionResponse(
            success=True,
            message=f"Section '{section.section_name}' updated successfully",
            sectionId=str(section_id),
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Update section", {"staff_id": str(current_staff.staff_id), "section_id": section_id}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.delete("/{section_id}", response_model=SectionActionResponse, dependencies=[Depends(security)])
async def delete_section(
    section_id: str,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Delete a section. Only Principal and College Admin can delete sections."""
    try:
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                              detail="Only Principal and College Admin can delete sections")

        # Get section
        result = await db.execute(
            select(Section)
            .join(Branch)
            .join(Degree)
            .join(Graduation)
            .join(Term)
            .where(and_(
                Section.section_id == section_id,
                Term.college_id == current_staff.college_id,
            ))
        )
        section = result.scalar_one_or_none()
        if not section:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

        # Delete section (cascading will handle section_subjects)
        section_name = section.section_name
        await db.delete(section)
        await db.commit()

        return SectionActionResponse(
            success=True,
            message=f"Section '{section_name}' deleted successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Delete section", {"staff_id": str(current_staff.staff_id), "section_id": section_id}, status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# SECTION-SUBJECT ASSIGNMENT ENDPOINTS
# ============================================================================

@router.get("/{section_id}/subjects", response_model=Page[SectionSubjectResponse], dependencies=[Depends(security)])
async def get_section_subjects(
    section_id: str,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Get assigned subjects for a section."""
    try:
        # Verify section belongs to college
        section_result = await db.execute(
            select(Section)
            .join(Branch)
            .join(Degree)
            .join(Graduation)
            .join(Term)
            .where(and_(
                Section.section_id == section_id,
                Term.college_id == current_staff.college_id,
            ))
        )
        section = section_result.scalar_one_or_none()
        if not section:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

        # Get section-subject assignments
        query = (select(SectionSubject, Subject, Staff.full_name, Section.section_name)
                .join(Subject, SectionSubject.subject_id == Subject.subject_id)
                .join(Section, SectionSubject.section_id == Section.section_id)
                .outerjoin(Staff, SectionSubject.assigned_staff_id == Staff.staff_id)
                .where(SectionSubject.section_id == section_id)
                .where(SectionSubject.is_active == True)
                .order_by(Subject.sequence_order, Subject.subject_name))

        paginated_result = await sqlalchemy_paginate(db, query)

        # Build response
        section_subject_responses = []
        for section_subject, subject, staff_name, section_name in paginated_result.items:
            section_subject_dict = section_subject.to_dict()
            section_subject_responses.append(
                SectionSubjectResponse(
                    **section_subject_dict,
                    sectionName=section_name,
                    subjectName=subject.subject_name,
                    subjectCode=subject.subject_code,
                    assignedStaffName=staff_name,
                )
            )

        return Page(
            items=section_subject_responses,
            total=paginated_result.total,
            page=paginated_result.page,
            size=paginated_result.size,
            pages=paginated_result.pages,
        )

    except HTTPException:
        raise
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Get section subjects", {"staff_id": str(current_staff.staff_id), "section_id": section_id}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/{section_id}/assign-subjects", response_model=AssignmentActionResponse, dependencies=[Depends(security)])
async def assign_subjects_to_section(
    section_id: str,
    request: AssignSubjectsRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Assign subjects to a section. Only Principal and College Admin can assign subjects."""
    try:
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                              detail="Only Principal and College Admin can assign subjects")

        # Verify section belongs to college
        section_result = await db.execute(
            select(Section)
            .join(Branch)
            .join(Degree)
            .join(Graduation)
            .join(Term)
            .where(and_(
                Section.section_id == section_id,
                Term.college_id == current_staff.college_id,
            ))
        )
        section = section_result.scalar_one_or_none()
        if not section:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

        # Verify all subjects belong to the same branch as section
        subject_ids = [assignment.subject_id for assignment in request.assignments]
        subjects_result = await db.execute(
            select(Subject).where(and_(
                Subject.subject_id.in_(subject_ids),
                Subject.branch_id == section.branch_id,
            ))
        )
        subjects = subjects_result.scalars().all()
        if len(subjects) != len(subject_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                              detail="Some subjects do not belong to the section's branch")

        # Verify staff assignments if provided
        staff_ids = [assignment.assigned_staff_id for assignment in request.assignments if assignment.assigned_staff_id]
        if staff_ids:
            staff_result = await db.execute(
                select(Staff.staff_id).where(and_(
                    Staff.staff_id.in_(staff_ids),
                    Staff.college_id == current_staff.college_id,
                ))
            )
            valid_staff_ids = {str(staff_id) for (staff_id,) in staff_result.all()}
            for assignment in request.assignments:
                if assignment.assigned_staff_id and assignment.assigned_staff_id not in valid_staff_ids:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                      detail=f"Staff with ID {assignment.assigned_staff_id} not found")

        # Create assignments
        created_assignments = []
        for assignment in request.assignments:
            # Check if assignment already exists
            existing_assignment = await db.execute(
                select(SectionSubject).where(and_(
                    SectionSubject.section_id == section_id,
                    SectionSubject.subject_id == assignment.subject_id,
                ))
            )
            if existing_assignment.scalar_one_or_none():
                continue  # Skip if already assigned

            new_assignment = SectionSubject(
                section_id=section_id,
                subject_id=assignment.subject_id,
                assigned_staff_id=assignment.assigned_staff_id,
            )
            db.add(new_assignment)

            # Get subject name for response
            subject = next(s for s in subjects if str(s.subject_id) == assignment.subject_id)
            created_assignments.append({
                "subjectName": subject.subject_name,
                "subjectCode": subject.subject_code,
            })

        await db.commit()

        return AssignmentActionResponse(
            success=True,
            message=f"{len(created_assignments)} subjects assigned to {section.section_name} successfully",
            sectionName=section.section_name,
            assignedCount=len(created_assignments),
            assignments=created_assignments,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Assign subjects to section", {"staff_id": str(current_staff.staff_id), "section_id": section_id, "subject_count": len(request.subject_ids)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.put("/{section_id}/subjects/{subject_id}/assign-teacher", 
           response_model=AssignmentActionResponse, dependencies=[Depends(security)])
async def assign_teacher_to_subject(
    section_id: str,
    subject_id: str,
    request: AssignTeacherRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Assign teacher to a section-subject. Only Principal and College Admin can assign teachers."""
    try:
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                              detail="Only Principal and College Admin can assign teachers")

        # Get section-subject assignment using section_id and subject_id
        assignment_result = await db.execute(
            select(SectionSubject, Subject.subject_name)
            .join(Subject, SectionSubject.subject_id == Subject.subject_id)
            .join(Section, SectionSubject.section_id == Section.section_id)
            .join(Branch, Section.branch_id == Branch.branch_id)
            .join(Degree, Branch.degree_id == Degree.degree_id)
            .join(Graduation, Degree.graduation_id == Graduation.graduation_id)
            .join(Term, Graduation.term_id == Term.term_id)
            .where(and_(
                SectionSubject.section_id == section_id,
                SectionSubject.subject_id == subject_id,
                Term.college_id == current_staff.college_id,
            ))
        )
        assignment_data = assignment_result.first()
        if not assignment_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section-subject assignment not found")

        assignment, subject_name = assignment_data

        # Get old teacher name
        old_teacher_name = None
        if assignment.assigned_staff_id:
            old_teacher_result = await db.execute(
                select(Staff.full_name).where(Staff.staff_id == assignment.assigned_staff_id)
            )
            old_teacher_name = old_teacher_result.scalar()

        # Verify new teacher
        new_teacher_result = await db.execute(
            select(Staff.full_name).where(and_(
                Staff.staff_id == request.staff_id,
                Staff.college_id == current_staff.college_id,
            ))
        )
        new_teacher_name = new_teacher_result.scalar()
        if not new_teacher_name:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")

        # Update assignment
        assignment.assigned_staff_id = request.staff_id
        await db.commit()

        return AssignmentActionResponse(
            success=True,
            message="Teacher assigned successfully",
            section_subject_id=str(assignment.section_subject_id),
            subject_name=subject_name,
            old_teacher=old_teacher_name,
            new_teacher=new_teacher_name,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Assign teacher to section", {"staff_id": str(current_staff.staff_id), "section_id": section_id, "teacher_staff_id": str(request.teacher_staff_id)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.delete("/{section_id}/subjects/{subject_id}", 
              response_model=AssignmentActionResponse, dependencies=[Depends(security)])
async def remove_subject_assignment(
    section_id: str,
    subject_id: str,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Remove subject assignment from section. Only Principal and College Admin can remove assignments."""
    try:
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                              detail="Only Principal and College Admin can remove assignments")

        # Get section-subject assignment using section_id and subject_id
        assignment_result = await db.execute(
            select(SectionSubject, Subject.subject_name)
            .join(Subject, SectionSubject.subject_id == Subject.subject_id)
            .join(Section, SectionSubject.section_id == Section.section_id)
            .join(Branch, Section.branch_id == Branch.branch_id)
            .join(Degree, Branch.degree_id == Degree.degree_id)
            .join(Graduation, Degree.graduation_id == Graduation.graduation_id)
            .join(Term, Graduation.term_id == Term.term_id)
            .where(and_(
                SectionSubject.section_id == section_id,
                SectionSubject.subject_id == subject_id,
                Term.college_id == current_staff.college_id,
            ))
        )
        assignment_data = assignment_result.first()
        if not assignment_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section-subject assignment not found")

        assignment, subject_name = assignment_data

        # Delete assignment
        await db.delete(assignment)
        await db.commit()

        return AssignmentActionResponse(
            success=True,
            message=f"Subject '{subject_name}' removed from section successfully",
            subject_name=subject_name,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Remove section assignment", {"staff_id": str(current_staff.staff_id), "section_subject_id": section_subject_id}, status.HTTP_500_INTERNAL_SERVER_ERROR)