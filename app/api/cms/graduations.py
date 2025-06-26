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
from app.schemas.academic_program_schemas import (
    CreateGraduationRequest,
    UpdateGraduationRequest,
    GraduationResponse,
    GraduationWithStatsResponse,
    GraduationActionResponse,
)
from .deps import get_current_staff

router = APIRouter(prefix="/cms/graduations", tags=["CMS Graduations Management"])

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


@router.get(
    "",
    response_model=Page[GraduationWithStatsResponse],
    dependencies=[Depends(security)],
)
async def get_graduations(
    term_id: Optional[str] = Query(None, description="Filter by term ID"),
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Get paginated list of graduations with resource statistics.
    Can filter by term_id.
    """
    try:
        # Build base query
        query = select(Graduation).join(Term).where(Term.college_id == current_staff.college_id)
        
        # Add term filter if provided
        if term_id:
            query = query.where(Graduation.term_id == term_id)
        
        query = query.order_by(Graduation.sequence_order, Graduation.graduation_name)

        # Get paginated graduations
        paginated_result = await sqlalchemy_paginate(db, query)

        # Add resource statistics for each graduation
        graduation_responses = []
        for graduation in paginated_result.items:
            # Get term name
            term_result = await db.execute(
                select(Term.term_name).where(Term.term_id == graduation.term_id)
            )
            term_name = term_result.scalar() or ""

            # Count degrees
            degrees_result = await db.execute(
                select(func.count(Degree.degree_id)).where(Degree.graduation_id == graduation.graduation_id)
            )
            degrees_count = degrees_result.scalar() or 0

            # Count branches (through degrees)
            branches_result = await db.execute(
                select(func.count(Branch.branch_id))
                .select_from(Branch)
                .join(Degree, Branch.degree_id == Degree.degree_id)
                .where(Degree.graduation_id == graduation.graduation_id)
            )
            branches_count = branches_result.scalar() or 0

            # Count subjects (through degrees -> branches)
            subjects_result = await db.execute(
                select(func.count(Subject.subject_id))
                .select_from(Subject)
                .join(Branch, Subject.branch_id == Branch.branch_id)
                .join(Degree, Branch.degree_id == Degree.degree_id)
                .where(Degree.graduation_id == graduation.graduation_id)
            )
            subjects_count = subjects_result.scalar() or 0

            # Count sections (through degrees -> branches)
            sections_result = await db.execute(
                select(func.count(Section.section_id))
                .select_from(Section)
                .join(Branch, Section.branch_id == Branch.branch_id)
                .join(Degree, Branch.degree_id == Degree.degree_id)
                .where(Degree.graduation_id == graduation.graduation_id)
            )
            sections_count = sections_result.scalar() or 0

            graduation_dict = graduation.to_dict()
            graduation_responses.append(
                GraduationWithStatsResponse(
                    **graduation_dict,
                    termName=term_name,
                    resourceCounts={
                        "degrees": degrees_count,
                        "branches": branches_count,
                        "subjects": subjects_count,
                        "sections": sections_count,
                    }
                )
            )

        return Page(
            items=graduation_responses,
            total=paginated_result.total,
            page=paginated_result.page,
            size=paginated_result.size,
            pages=paginated_result.pages,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting graduations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching graduations",
        )


@router.post("", response_model=GraduationActionResponse, dependencies=[Depends(security)])
async def create_graduation(
    request: CreateGraduationRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Create a new graduation level. Only Principal and College Admin can create graduations.
    """
    try:
        # Check permissions
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can create graduations",
            )

        # Verify term exists and belongs to college
        term_result = await db.execute(
            select(Term).where(
                and_(
                    Term.term_id == request.term_id,
                    Term.college_id == current_staff.college_id,
                )
            )
        )
        term = term_result.scalar_one_or_none()

        if not term:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Term not found",
            )

        # Check if graduation with same code already exists for this term
        existing_graduation_result = await db.execute(
            select(Graduation).where(
                and_(
                    Graduation.term_id == request.term_id,
                    Graduation.graduation_code == request.graduation_code,
                )
            )
        )
        existing_graduation = existing_graduation_result.scalar_one_or_none()

        if existing_graduation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Graduation level with code '{request.graduation_code}' already exists for this term",
            )

        # Create new graduation
        new_graduation = Graduation(
            graduation_name=request.graduation_name,
            graduation_code=request.graduation_code,
            description=request.description,
            sequence_order=request.sequence_order,
            term_id=request.term_id,
        )

        db.add(new_graduation)
        
        # Mark term as ongoing
        term.is_ongoing = True
        
        await db.commit()
        await db.refresh(new_graduation)

        return GraduationActionResponse(
            success=True,
            message=f"Graduation level '{request.graduation_name}' created successfully",
            graduationId=str(new_graduation.graduation_id),
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error creating graduation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating graduation",
        )


@router.get(
    "/{graduation_id}",
    response_model=GraduationResponse,
    dependencies=[Depends(security)],
)
async def get_graduation(
    graduation_id: str,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Get specific graduation by ID.
    """
    try:
        result = await db.execute(
            select(Graduation)
            .join(Term)
            .where(
                and_(
                    Graduation.graduation_id == graduation_id,
                    Term.college_id == current_staff.college_id,
                )
            )
        )
        graduation = result.scalar_one_or_none()

        if not graduation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Graduation not found"
            )

        return GraduationResponse(**graduation.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting graduation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching graduation",
        )


@router.put(
    "/{graduation_id}",
    response_model=GraduationActionResponse,
    dependencies=[Depends(security)],
)
async def update_graduation(
    graduation_id: str,
    request: UpdateGraduationRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Update a graduation. Only Principal and College Admin can update graduations.
    """
    try:
        # Check permissions
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can update graduations",
            )

        # Get graduation
        result = await db.execute(
            select(Graduation)
            .join(Term)
            .where(
                and_(
                    Graduation.graduation_id == graduation_id,
                    Term.college_id == current_staff.college_id,
                )
            )
        )
        graduation = result.scalar_one_or_none()

        if not graduation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Graduation not found"
            )

        # Update graduation fields
        if request.graduation_name is not None:
            graduation.graduation_name = request.graduation_name
        if request.description is not None:
            graduation.description = request.description
        if request.sequence_order is not None:
            graduation.sequence_order = request.sequence_order

        await db.commit()

        return GraduationActionResponse(
            success=True,
            message=f"Graduation level '{graduation.graduation_name}' updated successfully",
            graduationId=str(graduation_id),
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error updating graduation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating graduation",
        )


@router.delete(
    "/{graduation_id}",
    response_model=GraduationActionResponse,
    dependencies=[Depends(security)],
)
async def delete_graduation(
    graduation_id: str,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Delete a graduation. Only Principal and College Admin can delete graduations.
    This will cascade delete all degrees, branches, subjects, and sections.
    """
    try:
        # Check permissions
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can delete graduations",
            )

        # Get graduation
        result = await db.execute(
            select(Graduation)
            .join(Term)
            .where(
                and_(
                    Graduation.graduation_id == graduation_id,
                    Term.college_id == current_staff.college_id,
                )
            )
        )
        graduation = result.scalar_one_or_none()

        if not graduation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Graduation not found"
            )

        # Count resources before deletion
        degrees_count = await db.execute(
            select(func.count(Degree.degree_id)).where(Degree.graduation_id == graduation_id)
        )
        degrees_count = degrees_count.scalar() or 0

        branches_count = await db.execute(
            select(func.count(Branch.branch_id))
            .select_from(Branch)
            .join(Degree, Branch.degree_id == Degree.degree_id)
            .where(Degree.graduation_id == graduation_id)
        )
        branches_count = branches_count.scalar() or 0

        subjects_count = await db.execute(
            select(func.count(Subject.subject_id))
            .select_from(Subject)
            .join(Branch, Subject.branch_id == Branch.branch_id)
            .join(Degree, Branch.degree_id == Degree.degree_id)
            .where(Degree.graduation_id == graduation_id)
        )
        subjects_count = subjects_count.scalar() or 0

        sections_count = await db.execute(
            select(func.count(Section.section_id))
            .select_from(Section)
            .join(Branch, Section.branch_id == Branch.branch_id)
            .join(Degree, Branch.degree_id == Degree.degree_id)
            .where(Degree.graduation_id == graduation_id)
        )
        sections_count = sections_count.scalar() or 0

        # Delete graduation (cascading will handle children)
        graduation_name = graduation.graduation_name
        await db.delete(graduation)
        await db.commit()

        return GraduationActionResponse(
            success=True,
            message=f"Graduation level '{graduation_name}' deleted successfully along with all degrees, branches, subjects, and sections",
            deletedCounts={
                "degrees": degrees_count,
                "branches": branches_count,
                "subjects": subjects_count,
                "sections": sections_count,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error deleting graduation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting graduation",
        )