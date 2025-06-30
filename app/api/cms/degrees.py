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
    CreateDegreeRequest,
    UpdateDegreeRequest,
    DegreeResponse,
    DegreeWithStatsResponse,
    DegreeActionResponse,
)
from .deps import get_current_staff

router = APIRouter(prefix="/cms/degrees", tags=["CMS Degrees Management"])
security = HTTPBearer(auto_error=False)


@router.get("", response_model=Page[DegreeWithStatsResponse], dependencies=[Depends(security)])
async def get_degrees(
    graduation_id: Optional[str] = Query(None, description="Filter by graduation ID"),
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Get paginated list of degrees with resource statistics."""
    try:
        # Build base query
        query = (select(Degree)
                .join(Graduation)
                .join(Term)
                .where(Term.college_id == current_staff.college_id))
        
        if graduation_id:
            query = query.where(Degree.graduation_id == graduation_id)
        
        query = query.order_by(Degree.sequence_order, Degree.degree_name)
        paginated_result = await sqlalchemy_paginate(db, query)

        # Add resource statistics
        degree_responses = []
        for degree in paginated_result.items:
            # Get graduation name
            graduation_result = await db.execute(
                select(Graduation.graduation_name).where(Graduation.graduation_id == degree.graduation_id)
            )
            graduation_name = graduation_result.scalar() or ""

            # Count branches
            branches_result = await db.execute(
                select(func.count(Branch.branch_id)).where(Branch.degree_id == degree.degree_id)
            )
            branches_count = branches_result.scalar() or 0

            # Count subjects through branches
            subjects_result = await db.execute(
                select(func.count(Subject.subject_id))
                .select_from(Subject)
                .join(Branch, Subject.branch_id == Branch.branch_id)
                .where(Branch.degree_id == degree.degree_id)
            )
            subjects_count = subjects_result.scalar() or 0

            # Count sections through branches
            sections_result = await db.execute(
                select(func.count(Section.section_id))
                .select_from(Section)
                .join(Branch, Section.branch_id == Branch.branch_id)
                .where(Branch.degree_id == degree.degree_id)
            )
            sections_count = sections_result.scalar() or 0

            degree_dict = degree.to_dict()
            degree_responses.append(
                DegreeWithStatsResponse(
                    **degree_dict,
                    graduationName=graduation_name,
                    resourceCounts={
                        "branches": branches_count,
                        "subjects": subjects_count,
                        "sections": sections_count,
                    }
                )
            )

        return Page(
            items=degree_responses,
            total=paginated_result.total,
            page=paginated_result.page,
            size=paginated_result.size,
            pages=paginated_result.pages,
        )

    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Get degrees", {"staff_id": str(current_staff.staff_id), "college_id": str(current_staff.college_id), "graduation_id": graduation_id}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("", response_model=DegreeActionResponse, dependencies=[Depends(security)])
async def create_degree(
    request: CreateDegreeRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Create a new degree. Only Principal and College Admin can create degrees."""
    try:
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                              detail="Only Principal and College Admin can create degrees")

        # Verify graduation exists and belongs to college
        graduation_result = await db.execute(
            select(Graduation)
            .join(Term)
            .where(and_(
                Graduation.graduation_id == request.graduation_id,
                Term.college_id == current_staff.college_id,
            ))
        )
        graduation = graduation_result.scalar_one_or_none()
        if not graduation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Graduation not found")

        # Check for duplicate degree code
        existing_degree = await db.execute(
            select(Degree).where(and_(
                Degree.graduation_id == request.graduation_id,
                Degree.degree_code == request.degree_code,
            ))
        )
        if existing_degree.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                              detail=f"Degree with code '{request.degree_code}' already exists")

        # Create new degree
        new_degree = Degree(
            degree_name=request.degree_name,
            degree_code=request.degree_code,
            short_name=request.short_name,
            description=request.description,
            sequence_order=request.sequence_order,
            graduation_id=request.graduation_id,
        )

        db.add(new_degree)
        await db.commit()
        await db.refresh(new_degree)

        return DegreeActionResponse(
            success=True,
            message=f"Degree '{request.degree_name}' created successfully",
            degreeId=str(new_degree.degree_id),
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Create degree", {"staff_id": str(current_staff.staff_id), "graduation_id": str(request.graduation_id), "degree_name": request.degree_name, "degree_code": request.degree_code}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/{degree_id}", response_model=DegreeResponse, dependencies=[Depends(security)])
async def get_degree(
    degree_id: str,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Get specific degree by ID."""
    try:
        result = await db.execute(
            select(Degree)
            .join(Graduation)
            .join(Term)
            .where(and_(
                Degree.degree_id == degree_id,
                Term.college_id == current_staff.college_id,
            ))
        )
        degree = result.scalar_one_or_none()
        if not degree:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Degree not found")

        return DegreeResponse(**degree.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Get degree by ID", {"staff_id": str(current_staff.staff_id), "degree_id": degree_id}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.put("/{degree_id}", response_model=DegreeActionResponse, dependencies=[Depends(security)])
async def update_degree(
    degree_id: str,
    request: UpdateDegreeRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Update a degree. Only Principal and College Admin can update degrees."""
    try:
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                              detail="Only Principal and College Admin can update degrees")

        # Get degree
        result = await db.execute(
            select(Degree)
            .join(Graduation)
            .join(Term)
            .where(and_(
                Degree.degree_id == degree_id,
                Term.college_id == current_staff.college_id,
            ))
        )
        degree = result.scalar_one_or_none()
        if not degree:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Degree not found")

        # Update fields
        if request.degree_name is not None:
            degree.degree_name = request.degree_name
        if request.short_name is not None:
            degree.short_name = request.short_name
        if request.description is not None:
            degree.description = request.description
        if request.sequence_order is not None:
            degree.sequence_order = request.sequence_order

        await db.commit()

        return DegreeActionResponse(
            success=True,
            message=f"Degree '{degree.degree_name}' updated successfully",
            degreeId=str(degree_id),
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Update degree", {"staff_id": str(current_staff.staff_id), "degree_id": degree_id}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.delete("/{degree_id}", response_model=DegreeActionResponse, dependencies=[Depends(security)])
async def delete_degree(
    degree_id: str,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Delete a degree. Only Principal and College Admin can delete degrees."""
    try:
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                              detail="Only Principal and College Admin can delete degrees")

        # Get degree
        result = await db.execute(
            select(Degree)
            .join(Graduation)
            .join(Term)
            .where(and_(
                Degree.degree_id == degree_id,
                Term.college_id == current_staff.college_id,
            ))
        )
        degree = result.scalar_one_or_none()
        if not degree:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Degree not found")

        # Count resources before deletion
        branches_count = await db.execute(
            select(func.count(Branch.branch_id)).where(Branch.degree_id == degree_id)
        )
        branches_count = branches_count.scalar() or 0

        subjects_count = await db.execute(
            select(func.count(Subject.subject_id))
            .select_from(Subject)
            .join(Branch, Subject.branch_id == Branch.branch_id)
            .where(Branch.degree_id == degree_id)
        )
        subjects_count = subjects_count.scalar() or 0

        sections_count = await db.execute(
            select(func.count(Section.section_id))
            .select_from(Section)
            .join(Branch, Section.branch_id == Branch.branch_id)
            .where(Branch.degree_id == degree_id)
        )
        sections_count = sections_count.scalar() or 0

        # Delete degree
        degree_name = degree.degree_name
        await db.delete(degree)
        await db.commit()

        return DegreeActionResponse(
            success=True,
            message=f"Degree '{degree_name}' deleted successfully",
            deletedCounts={
                "branches": branches_count,
                "subjects": subjects_count,
                "sections": sections_count,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Delete degree", {"staff_id": str(current_staff.staff_id), "degree_id": degree_id}, status.HTTP_500_INTERNAL_SERVER_ERROR)