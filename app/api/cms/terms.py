from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate as sqlalchemy_paginate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List

from app.database import get_db
from app.models.staff import Staff
from app.models.term import Term
from app.models.graduation import Graduation
from app.models.degree import Degree
from app.models.branch import Branch
from app.models.subject import Subject
from app.models.section import Section
from app.schemas.academic_program_schemas import (
    CreateTermRequest,
    UpdateTermRequest,
    TermResponse,
    TermWithStatsResponse,
    TermActionResponse,
)
from .deps import get_current_staff

router = APIRouter(prefix="/cms/terms", tags=["CMS Terms Management"])

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


@router.get(
    "",
    response_model=Page[TermWithStatsResponse],
    dependencies=[Depends(security)],
)
async def get_terms(
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Get paginated list of terms with resource statistics.
    All authenticated staff can view terms in their college.
    """
    try:
        # Build query for terms in current staff's college
        query = select(Term).where(Term.college_id == current_staff.college_id)
        query = query.order_by(Term.batch_year.desc(), Term.current_year.desc(), Term.current_semester.desc())

        # Get paginated terms
        paginated_result = await sqlalchemy_paginate(db, query)

        # Add resource statistics for each term
        term_responses = []
        for term in paginated_result.items:
            # Count graduations
            graduations_result = await db.execute(
                select(func.count(Graduation.graduation_id)).where(Graduation.term_id == term.term_id)
            )
            graduations_count = graduations_result.scalar() or 0

            # Count degrees (through graduations)
            degrees_result = await db.execute(
                select(func.count(Degree.degree_id))
                .select_from(Degree)
                .join(Graduation, Degree.graduation_id == Graduation.graduation_id)
                .where(Graduation.term_id == term.term_id)
            )
            degrees_count = degrees_result.scalar() or 0

            # Count branches (through graduations -> degrees)
            branches_result = await db.execute(
                select(func.count(Branch.branch_id))
                .select_from(Branch)
                .join(Degree, Branch.degree_id == Degree.degree_id)
                .join(Graduation, Degree.graduation_id == Graduation.graduation_id)
                .where(Graduation.term_id == term.term_id)
            )
            branches_count = branches_result.scalar() or 0

            # Count subjects (through graduations -> degrees -> branches)
            subjects_result = await db.execute(
                select(func.count(Subject.subject_id))
                .select_from(Subject)
                .join(Branch, Subject.branch_id == Branch.branch_id)
                .join(Degree, Branch.degree_id == Degree.degree_id)
                .join(Graduation, Degree.graduation_id == Graduation.graduation_id)
                .where(Graduation.term_id == term.term_id)
            )
            subjects_count = subjects_result.scalar() or 0

            # Count sections (through graduations -> degrees -> branches)
            sections_result = await db.execute(
                select(func.count(Section.section_id))
                .select_from(Section)
                .join(Branch, Section.branch_id == Branch.branch_id)
                .join(Degree, Branch.degree_id == Degree.degree_id)
                .join(Graduation, Degree.graduation_id == Graduation.graduation_id)
                .where(Graduation.term_id == term.term_id)
            )
            sections_count = sections_result.scalar() or 0

            term_dict = term.to_dict()
            term_responses.append(
                TermWithStatsResponse(
                    **term_dict,
                    resourceCounts={
                        "graduations": graduations_count,
                        "degrees": degrees_count,
                        "branches": branches_count,
                        "subjects": subjects_count,
                        "sections": sections_count,
                    }
                )
            )

        return Page(
            items=term_responses,
            total=paginated_result.total,
            page=paginated_result.page,
            size=paginated_result.size,
            pages=paginated_result.pages,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting terms: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching terms",
        )


@router.post("", response_model=TermActionResponse, dependencies=[Depends(security)])
async def create_term(
    request: CreateTermRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Create a new term. Only Principal and College Admin can create terms.
    """
    try:
        # Check permissions
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can create terms",
            )

        # Check if term already exists
        existing_term_result = await db.execute(
            select(Term).where(
                and_(
                    Term.college_id == current_staff.college_id,
                    Term.batch_year == request.batch_year,
                    Term.current_year == request.current_year,
                    Term.current_semester == request.current_semester,
                )
            )
        )
        existing_term = existing_term_result.scalar_one_or_none()

        if existing_term:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Term '{request.batch_year}-{request.current_year}-{request.current_semester}' already exists for this college",
            )

        # Create new term
        new_term = Term(
            batch_year=request.batch_year,
            current_year=request.current_year,
            current_semester=request.current_semester,
            start_date=request.start_date,
            end_date=request.end_date,
            college_id=current_staff.college_id,
        )

        # Generate term metadata
        new_term.generate_term_metadata()

        db.add(new_term)
        await db.commit()
        await db.refresh(new_term)

        return TermActionResponse(
            success=True,
            message=f"Term '{new_term.term_name}' created successfully",
            termId=str(new_term.term_id),
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error creating term: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating term",
        )


@router.get(
    "/{term_id}",
    response_model=TermResponse,
    dependencies=[Depends(security)],
)
async def get_term(
    term_id: str,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Get specific term by ID.
    """
    try:
        result = await db.execute(
            select(Term).where(
                and_(
                    Term.term_id == term_id,
                    Term.college_id == current_staff.college_id,
                )
            )
        )
        term = result.scalar_one_or_none()

        if not term:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Term not found"
            )

        return TermResponse(**term.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting term: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching term",
        )


@router.put(
    "/{term_id}",
    response_model=TermActionResponse,
    dependencies=[Depends(security)],
)
async def update_term(
    term_id: str,
    request: UpdateTermRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Update a term. Only Principal and College Admin can update terms.
    """
    try:
        # Check permissions
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can update terms",
            )

        # Get term
        result = await db.execute(
            select(Term).where(
                and_(
                    Term.term_id == term_id,
                    Term.college_id == current_staff.college_id,
                )
            )
        )
        term = result.scalar_one_or_none()

        if not term:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Term not found"
            )

        # Update term fields
        if request.start_date is not None:
            term.start_date = request.start_date
        if request.end_date is not None:
            term.end_date = request.end_date
        if request.is_active is not None:
            term.is_active = request.is_active

        await db.commit()

        return TermActionResponse(
            success=True,
            message=f"Term '{term.term_name}' updated successfully",
            termId=str(term_id),
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error updating term: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating term",
        )


@router.delete(
    "/{term_id}",
    response_model=TermActionResponse,
    dependencies=[Depends(security)],
)
async def delete_term(
    term_id: str,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Delete a term. Only Principal and College Admin can delete terms.
    This will cascade delete all graduations, degrees, branches, subjects, and sections.
    """
    try:
        # Check permissions
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can delete terms",
            )

        # Get term
        result = await db.execute(
            select(Term).where(
                and_(
                    Term.term_id == term_id,
                    Term.college_id == current_staff.college_id,
                )
            )
        )
        term = result.scalar_one_or_none()

        if not term:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Term not found"
            )

        # Count resources before deletion for response
        graduations_count = await db.execute(
            select(func.count(Graduation.graduation_id)).where(Graduation.term_id == term_id)
        )
        graduations_count = graduations_count.scalar() or 0

        degrees_count = await db.execute(
            select(func.count(Degree.degree_id))
            .select_from(Degree)
            .join(Graduation, Degree.graduation_id == Graduation.graduation_id)
            .where(Graduation.term_id == term_id)
        )
        degrees_count = degrees_count.scalar() or 0

        branches_count = await db.execute(
            select(func.count(Branch.branch_id))
            .select_from(Branch)
            .join(Degree, Branch.degree_id == Degree.degree_id)
            .join(Graduation, Degree.graduation_id == Graduation.graduation_id)
            .where(Graduation.term_id == term_id)
        )
        branches_count = branches_count.scalar() or 0

        subjects_count = await db.execute(
            select(func.count(Subject.subject_id))
            .select_from(Subject)
            .join(Branch, Subject.branch_id == Branch.branch_id)
            .join(Degree, Branch.degree_id == Degree.degree_id)
            .join(Graduation, Degree.graduation_id == Graduation.graduation_id)
            .where(Graduation.term_id == term_id)
        )
        subjects_count = subjects_count.scalar() or 0

        sections_count = await db.execute(
            select(func.count(Section.section_id))
            .select_from(Section)
            .join(Branch, Section.branch_id == Branch.branch_id)
            .join(Degree, Branch.degree_id == Degree.degree_id)
            .join(Graduation, Degree.graduation_id == Graduation.graduation_id)
            .where(Graduation.term_id == term_id)
        )
        sections_count = sections_count.scalar() or 0

        # Check if term is ongoing (has resources)
        if term.is_ongoing and (graduations_count > 0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete term. It has attached resources.",
            )

        # Delete term (cascading will handle children)
        term_name = term.term_name
        await db.delete(term)
        await db.commit()

        return TermActionResponse(
            success=True,
            message=f"Term '{term_name}' deleted successfully along with all attached resources",
            deletedCounts={
                "graduations": graduations_count,
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
        print(f"Error deleting term: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting term",
        )