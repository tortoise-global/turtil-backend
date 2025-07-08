from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.security import HTTPBearer
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate as sqlalchemy_paginate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional, List

from app.database import get_db
from app.models.staff import Staff
from app.models.term import Term
from app.models.graduation import Graduation
from app.models.degree import Degree
from app.models.branch import Branch
from app.models.subject import Subject
from app.schemas.academic_program_schemas import (
    CreateSubjectRequest,
    UpdateSubjectRequest,
    SubjectResponse,
    SubjectWithBranchResponse,
    SubjectActionResponse,
)
from .deps import get_current_staff

router = APIRouter(prefix="/cms/subjects", tags=["CMS Subjects Management"])
security = HTTPBearer(auto_error=False)


@router.get("", response_model=Page[SubjectWithBranchResponse], dependencies=[Depends(security)])
async def get_subjects(
    branch_id: Optional[str] = Query(None, description="Filter by branch ID"),
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Get paginated list of subjects."""
    try:
        # Build base query
        query = (select(Subject)
                .join(Branch)
                .join(Degree)
                .join(Graduation)
                .join(Term)
                .where(Term.college_id == current_staff.college_id))
        
        if branch_id:
            query = query.where(Subject.branch_id == branch_id)
        
        query = query.order_by(Subject.sequence_order, Subject.subject_name)
        paginated_result = await sqlalchemy_paginate(db, query)

        # Add branch information
        subject_responses = []
        for subject in paginated_result.items:
            # Get branch name
            branch_result = await db.execute(
                select(Branch.branch_name).where(Branch.branch_id == subject.branch_id)
            )
            branch_name = branch_result.scalar() or ""

            subject_dict = subject.to_dict()
            subject_responses.append(
                SubjectWithBranchResponse(**subject_dict, branchName=branch_name)
            )

        return Page(
            items=subject_responses,
            total=paginated_result.total,
            page=paginated_result.page,
            size=paginated_result.size,
            pages=paginated_result.pages,
        )

    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Get subjects", {"staff_id": str(current_staff.staff_id), "college_id": str(current_staff.college_id), "branch_id": branch_id}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("", response_model=SubjectActionResponse, dependencies=[Depends(security)])
async def create_subjects(
    request: CreateSubjectRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Create subjects (single or bulk). Only Principal and College Admin can create subjects."""
    try:
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                              detail="Only Principal and College Admin can create subjects")

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

        # Check for duplicate subject codes within the request
        subject_codes = [subject.subject_code for subject in request.subjects]
        if len(subject_codes) != len(set(subject_codes)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                              detail="Duplicate subject codes found in request")

        # Check for existing subject codes in database
        existing_subjects = await db.execute(
            select(Subject.subject_code).where(and_(
                Subject.branch_id == request.branch_id,
                Subject.subject_code.in_(subject_codes),
            ))
        )
        existing_codes = [code for (code,) in existing_subjects.all()]
        if existing_codes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                              detail=f"Subject codes already exist: {', '.join(existing_codes)}")

        # Create subjects
        created_subjects = []
        for subject_data in request.subjects:
            new_subject = Subject(
                subject_name=subject_data.subject_name,
                subject_code=subject_data.subject_code,
                short_name=subject_data.short_name,
                description=subject_data.description,
                credits=subject_data.credits,
                subject_type=subject_data.subject_type,
                sequence_order=subject_data.sequence_order,
                branch_id=request.branch_id,
            )
            db.add(new_subject)
            created_subjects.append({
                "subjectName": subject_data.subject_name,
                "subjectCode": subject_data.subject_code,
                "subjectId": str(new_subject.subject_id) if len(request.subjects) == 1 else None
            })

        await db.commit()

        # Different response based on single vs bulk creation
        if len(request.subjects) == 1:
            return SubjectActionResponse(
                success=True,
                message=f"Subject '{request.subjects[0].subject_name}' created successfully",
                subject_id=str(new_subject.subject_id),
            )
        else:
            return SubjectActionResponse(
                success=True,
                message=f"{len(request.subjects)} subjects created successfully",
                created_count=len(request.subjects),
                subjects=created_subjects,
            )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Create subject", {"staff_id": str(current_staff.staff_id), "branch_id": str(request.branch_id), "subject_name": request.subject_name, "subject_code": request.subject_code}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/{subject_id}", response_model=SubjectResponse, dependencies=[Depends(security)])
async def get_subject(
    subject_id: str,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Get specific subject by ID."""
    try:
        result = await db.execute(
            select(Subject)
            .join(Branch)
            .join(Degree)
            .join(Graduation)
            .join(Term)
            .where(and_(
                Subject.subject_id == subject_id,
                Term.college_id == current_staff.college_id,
            ))
        )
        subject = result.scalar_one_or_none()
        if not subject:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

        return SubjectResponse(**subject.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Get subject by ID", {"staff_id": str(current_staff.staff_id), "subject_id": subject_id}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.put("/{subject_id}", response_model=SubjectActionResponse, dependencies=[Depends(security)])
async def update_subject(
    subject_id: str,
    request: UpdateSubjectRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Update a subject. Only Principal and College Admin can update subjects."""
    try:
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                              detail="Only Principal and College Admin can update subjects")

        # Get subject
        result = await db.execute(
            select(Subject)
            .join(Branch)
            .join(Degree)
            .join(Graduation)
            .join(Term)
            .where(and_(
                Subject.subject_id == subject_id,
                Term.college_id == current_staff.college_id,
            ))
        )
        subject = result.scalar_one_or_none()
        if not subject:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

        # Update fields
        if request.subject_name is not None:
            subject.subject_name = request.subject_name
        if request.short_name is not None:
            subject.short_name = request.short_name
        if request.description is not None:
            subject.description = request.description
        if request.credits is not None:
            subject.credits = request.credits
        if request.subject_type is not None:
            subject.subject_type = request.subject_type
        if request.sequence_order is not None:
            subject.sequence_order = request.sequence_order

        await db.commit()

        return SubjectActionResponse(
            success=True,
            message=f"Subject '{subject.subject_name}' updated successfully",
            subjectId=str(subject_id),
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Update subject", {"staff_id": str(current_staff.staff_id), "subject_id": subject_id}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.delete("/{subject_id}", response_model=SubjectActionResponse, dependencies=[Depends(security)])
async def delete_subject(
    subject_id: str,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Delete a subject. Only Principal and College Admin can delete subjects."""
    try:
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                              detail="Only Principal and College Admin can delete subjects")

        # Get subject
        result = await db.execute(
            select(Subject)
            .join(Branch)
            .join(Degree)
            .join(Graduation)
            .join(Term)
            .where(and_(
                Subject.subject_id == subject_id,
                Term.college_id == current_staff.college_id,
            ))
        )
        subject = result.scalar_one_or_none()
        if not subject:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

        # Check if subject is assigned to any sections
        from app.models.section_subject import SectionSubject
        assignments_result = await db.execute(
            select(SectionSubject).where(SectionSubject.subject_id == subject_id)
        )
        assignments = assignments_result.scalars().all()

        if assignments:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                              detail=f"Cannot delete subject. It is assigned to {len(assignments)} section(s)")

        # Delete subject
        subject_name = subject.subject_name
        await db.delete(subject)
        await db.commit()

        return SubjectActionResponse(
            success=True,
            message=f"Subject '{subject_name}' deleted successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Delete subject", {"staff_id": str(current_staff.staff_id), "subject_id": subject_id}, status.HTTP_500_INTERNAL_SERVER_ERROR)