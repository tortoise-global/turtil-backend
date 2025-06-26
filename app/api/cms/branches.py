from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.security import HTTPBearer
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate as sqlalchemy_paginate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import Optional

from app.database import get_db
from app.models.staff import Staff
from app.models.term import Term
from app.models.graduation import Graduation
from app.models.degree import Degree
from app.models.branch import Branch
from app.models.subject import Subject
from app.models.section import Section
from app.models.department import Department
from app.schemas.academic_program_schemas import (
    CreateBranchRequest,
    UpdateBranchRequest,
    BranchResponse,
    BranchWithStatsResponse,
    BranchActionResponse,
    CompleteBranchResponse,
    SubjectResponse,
)
from .deps import get_current_staff

router = APIRouter(prefix="/cms/branches", tags=["CMS Branches Management"])
security = HTTPBearer(auto_error=False)


@router.get("", response_model=Page[BranchWithStatsResponse], dependencies=[Depends(security)])
async def get_branches(
    degree_id: Optional[str] = Query(None, description="Filter by degree ID"),
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Get paginated list of branches with resource statistics."""
    try:
        # Build base query
        query = (select(Branch)
                .join(Degree)
                .join(Graduation)
                .join(Term)
                .where(Term.college_id == current_staff.college_id))
        
        if degree_id:
            query = query.where(Branch.degree_id == degree_id)
        
        query = query.order_by(Branch.sequence_order, Branch.branch_name)
        paginated_result = await sqlalchemy_paginate(db, query)

        # Add resource statistics
        branch_responses = []
        for branch in paginated_result.items:
            # Get degree name
            degree_result = await db.execute(
                select(Degree.degree_name).where(Degree.degree_id == branch.degree_id)
            )
            degree_name = degree_result.scalar() or ""

            # Get department name
            department_result = await db.execute(
                select(Department.name).where(Department.department_id == branch.department_id)
            )
            department_name = department_result.scalar() or ""

            # Count subjects
            subjects_result = await db.execute(
                select(func.count(Subject.subject_id)).where(Subject.branch_id == branch.branch_id)
            )
            subjects_count = subjects_result.scalar() or 0

            # Count sections
            sections_result = await db.execute(
                select(func.count(Section.section_id)).where(Section.branch_id == branch.branch_id)
            )
            sections_count = sections_result.scalar() or 0

            branch_dict = branch.to_dict()
            branch_responses.append(
                BranchWithStatsResponse(
                    **branch_dict,
                    degreeName=degree_name,
                    departmentName=department_name,
                    resourceCounts={
                        "subjects": subjects_count,
                        "sections": sections_count,
                    }
                )
            )

        return Page(
            items=branch_responses,
            total=paginated_result.total,
            page=paginated_result.page,
            size=paginated_result.size,
            pages=paginated_result.pages,
        )

    except Exception as e:
        print(f"Error getting branches: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                          detail="Error fetching branches")


@router.post("", response_model=BranchActionResponse, dependencies=[Depends(security)])
async def create_branch(
    request: CreateBranchRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Create a new branch. Only Principal and College Admin can create branches."""
    try:
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                              detail="Only Principal and College Admin can create branches")

        # Verify degree exists and belongs to college
        degree_result = await db.execute(
            select(Degree)
            .join(Graduation)
            .join(Term)
            .where(and_(
                Degree.degree_id == request.degree_id,
                Term.college_id == current_staff.college_id,
            ))
        )
        degree = degree_result.scalar_one_or_none()
        if not degree:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Degree not found")

        # Verify department exists and belongs to college
        department_result = await db.execute(
            select(Department).where(and_(
                Department.department_id == request.department_id,
                Department.college_id == current_staff.college_id,
            ))
        )
        department = department_result.scalar_one_or_none()
        if not department:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

        # Check for duplicate branch code
        existing_branch = await db.execute(
            select(Branch).where(and_(
                Branch.degree_id == request.degree_id,
                Branch.branch_code == request.branch_code,
            ))
        )
        if existing_branch.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                              detail=f"Branch with code '{request.branch_code}' already exists")

        # Create new branch
        new_branch = Branch(
            branch_name=request.branch_name,
            branch_code=request.branch_code,
            short_name=request.short_name,
            description=request.description,
            sequence_order=request.sequence_order,
            degree_id=request.degree_id,
            department_id=request.department_id,
        )

        db.add(new_branch)
        await db.commit()
        await db.refresh(new_branch)

        return BranchActionResponse(
            success=True,
            message=f"Branch '{request.branch_name}' created successfully",
            branchId=str(new_branch.branch_id),
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error creating branch: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                          detail="Error creating branch")


@router.get("/{branch_id}", response_model=BranchResponse, dependencies=[Depends(security)])
async def get_branch(
    branch_id: str,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Get specific branch by ID."""
    try:
        result = await db.execute(
            select(Branch)
            .join(Degree)
            .join(Graduation)
            .join(Term)
            .where(and_(
                Branch.branch_id == branch_id,
                Term.college_id == current_staff.college_id,
            ))
        )
        branch = result.scalar_one_or_none()
        if not branch:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")

        return BranchResponse(**branch.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting branch: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                          detail="Error fetching branch")


@router.get("/{branch_id}/complete", response_model=CompleteBranchResponse, dependencies=[Depends(security)])
async def get_branch_complete(
    branch_id: str,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Get branch with all subjects and sections."""
    try:
        # Get branch
        branch_result = await db.execute(
            select(Branch)
            .join(Degree)
            .join(Graduation)
            .join(Term)
            .where(and_(
                Branch.branch_id == branch_id,
                Term.college_id == current_staff.college_id,
            ))
        )
        branch = branch_result.scalar_one_or_none()
        if not branch:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")

        # Get department name
        department_result = await db.execute(
            select(Department.name).where(Department.department_id == branch.department_id)
        )
        department_name = department_result.scalar() or ""

        # Get all subjects for this branch
        subjects_result = await db.execute(
            select(Subject)
            .where(Subject.branch_id == branch_id)
            .order_by(Subject.sequence_order, Subject.subject_name)
        )
        subjects = subjects_result.scalars().all()

        # Get all sections for this branch with their assigned subjects
        sections_result = await db.execute(
            select(Section)
            .where(Section.branch_id == branch_id)
            .order_by(Section.sequence_order, Section.section_name)
        )
        sections = sections_result.scalars().all()

        # For each section, get assigned subjects
        sections_data = []
        for section in sections:
            # Get class teacher name if assigned
            class_teacher_name = None
            if section.class_teacher_id:
                teacher_result = await db.execute(
                    select(Staff.full_name).where(Staff.staff_id == section.class_teacher_id)
                )
                class_teacher_name = teacher_result.scalar()

            # Get assigned subjects for this section
            from app.models.section_subject import SectionSubject
            assigned_subjects_result = await db.execute(
                select(SectionSubject, Subject, Staff.full_name)
                .join(Subject, SectionSubject.subject_id == Subject.subject_id)
                .outerjoin(Staff, SectionSubject.assigned_staff_id == Staff.staff_id)
                .where(SectionSubject.section_id == section.section_id)
                .where(SectionSubject.is_active == True)
            )
            assigned_subjects = assigned_subjects_result.all()

            assigned_subjects_data = []
            for section_subject, subject, teacher_name in assigned_subjects:
                assigned_subjects_data.append({
                    "subjectName": subject.subject_name,
                    "subjectCode": subject.subject_code,
                    "teacherName": teacher_name,
                })

            section_dict = section.to_dict()
            section_dict["classTeacherName"] = class_teacher_name
            section_dict["assignedSubjects"] = assigned_subjects_data
            sections_data.append(section_dict)

        branch_dict = branch.to_dict()
        branch_dict["departmentName"] = department_name

        return CompleteBranchResponse(
            branch=branch_dict,
            subjects=[SubjectResponse(**subject.to_dict()) for subject in subjects],
            sections=sections_data,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting complete branch: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                          detail="Error fetching complete branch")


@router.put("/{branch_id}", response_model=BranchActionResponse, dependencies=[Depends(security)])
async def update_branch(
    branch_id: str,
    request: UpdateBranchRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Update a branch. Only Principal and College Admin can update branches."""
    try:
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                              detail="Only Principal and College Admin can update branches")

        # Get branch
        result = await db.execute(
            select(Branch)
            .join(Degree)
            .join(Graduation)
            .join(Term)
            .where(and_(
                Branch.branch_id == branch_id,
                Term.college_id == current_staff.college_id,
            ))
        )
        branch = result.scalar_one_or_none()
        if not branch:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")

        # Verify department if provided
        if request.department_id:
            department_result = await db.execute(
                select(Department).where(and_(
                    Department.department_id == request.department_id,
                    Department.college_id == current_staff.college_id,
                ))
            )
            if not department_result.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

        # Update fields
        if request.branch_name is not None:
            branch.branch_name = request.branch_name
        if request.short_name is not None:
            branch.short_name = request.short_name
        if request.description is not None:
            branch.description = request.description
        if request.sequence_order is not None:
            branch.sequence_order = request.sequence_order
        if request.department_id is not None:
            branch.department_id = request.department_id

        await db.commit()

        return BranchActionResponse(
            success=True,
            message=f"Branch '{branch.branch_name}' updated successfully",
            branchId=str(branch_id),
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error updating branch: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                          detail="Error updating branch")


@router.delete("/{branch_id}", response_model=BranchActionResponse, dependencies=[Depends(security)])
async def delete_branch(
    branch_id: str,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Delete a branch. Only Principal and College Admin can delete branches."""
    try:
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                              detail="Only Principal and College Admin can delete branches")

        # Get branch
        result = await db.execute(
            select(Branch)
            .join(Degree)
            .join(Graduation)
            .join(Term)
            .where(and_(
                Branch.branch_id == branch_id,
                Term.college_id == current_staff.college_id,
            ))
        )
        branch = result.scalar_one_or_none()
        if not branch:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")

        # Count resources before deletion
        subjects_count = await db.execute(
            select(func.count(Subject.subject_id)).where(Subject.branch_id == branch_id)
        )
        subjects_count = subjects_count.scalar() or 0

        sections_count = await db.execute(
            select(func.count(Section.section_id)).where(Section.branch_id == branch_id)
        )
        sections_count = sections_count.scalar() or 0

        # Delete branch
        branch_name = branch.branch_name
        await db.delete(branch)
        await db.commit()

        return BranchActionResponse(
            success=True,
            message=f"Branch '{branch_name}' deleted successfully",
            deletedCounts={
                "subjects": subjects_count,
                "sections": sections_count,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error deleting branch: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                          detail="Error deleting branch")