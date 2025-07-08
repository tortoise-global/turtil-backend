"""
Division management endpoints for CMS

Allows Principal and College Admin to:
- Create, update, delete divisions
- List divisions within their college
- Assign staff to divisions
- Get division statistics
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
import logging

from app.database import get_db
from app.models import Division, Department, Staff, College
from app.schemas.division_schemas import (
    DivisionCreateRequest,
    DivisionUpdateRequest,
    DivisionResponse,
    DivisionWithStatsResponse,
    DivisionListResponse,
    DivisionOperationResponse
)
from app.api.cms.deps import (
    require_principal_or_admin,
    get_current_staff,
    check_college_access
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=DivisionResponse, status_code=status.HTTP_201_CREATED)
async def create_division(
    division_data: DivisionCreateRequest,
    current_staff: Staff = Depends(require_principal_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new division within the college.
    Only Principal and College Admin can create divisions.
    """
    try:
        # Check if division code already exists in this college
        existing_result = await db.execute(
            select(Division).where(
                and_(
                    Division.college_id == current_staff.college_id,
                    Division.code == division_data.code
                )
            )
        )
        existing_division = existing_result.scalar_one_or_none()
        
        if existing_division:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Division with code '{division_data.code}' already exists in this college"
            )
        
        # Create new division
        new_division = Division(
            name=division_data.name,
            code=division_data.code,
            description=division_data.description,
            college_id=current_staff.college_id
        )
        
        db.add(new_division)
        await db.commit()
        await db.refresh(new_division)
        
        logger.info(f"Division created: {new_division.name} by staff {current_staff.staff_id}")
        
        return DivisionResponse(**new_division.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating division: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create division"
        )


@router.get("/", response_model=DivisionListResponse)
async def list_divisions(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by division name or code"),
    current_staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    List all divisions within the college with pagination and optional filtering.
    Includes department and staff counts for each division.
    """
    try:
        # Build query conditions
        conditions = [Division.college_id == current_staff.college_id]
        
        if search:
            search_term = f"%{search}%"
            conditions.append(
                or_(
                    Division.name.ilike(search_term),
                    Division.code.ilike(search_term)
                )
            )
        
        # Removed is_active filtering as all divisions are always active
        
        # Get total count
        count_result = await db.execute(
            select(func.count(Division.division_id)).where(and_(*conditions))
        )
        total = count_result.scalar()
        
        # Get divisions with pagination
        offset = (page - 1) * size
        divisions_result = await db.execute(
            select(Division)
            .where(and_(*conditions))
            .order_by(Division.created_at.desc())
            .offset(offset)
            .limit(size)
        )
        divisions = divisions_result.scalars().all()
        
        # Get statistics for each division
        division_responses = []
        for division in divisions:
            # Count departments
            dept_count_result = await db.execute(
                select(func.count(Department.department_id))
                .where(Department.division_id == division.division_id)
            )
            dept_count = dept_count_result.scalar() or 0
            
            # Count staff
            staff_count_result = await db.execute(
                select(func.count(Staff.staff_id))
                .where(Staff.division_id == division.division_id)
            )
            staff_count = staff_count_result.scalar() or 0
            
            division_dict = division.to_dict()
            division_dict.update({
                "departmentCount": dept_count,
                "staffCount": staff_count
            })
            
            division_responses.append(DivisionWithStatsResponse(**division_dict))
        
        total_pages = (total + size - 1) // size
        
        return DivisionListResponse(
            items=division_responses,
            total=total,
            page=page,
            size=size,
            pages=total_pages
        )
        
    except Exception as e:
        logger.error(f"Error listing divisions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve divisions"
        )


@router.get("/{division_id}", response_model=DivisionWithStatsResponse)
async def get_division(
    division_id: UUID,
    current_staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get details of a specific division with statistics.
    """
    try:
        # Get division
        result = await db.execute(
            select(Division).where(Division.division_id == division_id)
        )
        division = result.scalar_one_or_none()
        
        if not division:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Division not found"
            )
        
        # Check college access
        await check_college_access(current_staff, division.college_id)
        
        # Get statistics
        dept_count_result = await db.execute(
            select(func.count(Department.department_id))
            .where(Department.division_id == division_id)
        )
        dept_count = dept_count_result.scalar() or 0
        
        staff_count_result = await db.execute(
            select(func.count(Staff.staff_id))
            .where(Staff.division_id == division_id)
        )
        staff_count = staff_count_result.scalar() or 0
        
        division_dict = division.to_dict()
        division_dict.update({
            "departmentCount": dept_count,
            "staffCount": staff_count
        })
        
        return DivisionWithStatsResponse(**division_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting division {division_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve division"
        )


@router.put("/{division_id}", response_model=DivisionResponse)
async def update_division(
    division_id: UUID,
    division_data: DivisionUpdateRequest,
    current_staff: Staff = Depends(require_principal_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Update division details.
    Only Principal and College Admin can update divisions.
    """
    try:
        # Get division
        result = await db.execute(
            select(Division).where(Division.division_id == division_id)
        )
        division = result.scalar_one_or_none()
        
        if not division:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Division not found"
            )
        
        # Check college access
        await check_college_access(current_staff, division.college_id)
        
        # Check if code is being changed and if it conflicts
        if division_data.code and division_data.code != division.code:
            existing_result = await db.execute(
                select(Division).where(
                    and_(
                        Division.college_id == current_staff.college_id,
                        Division.code == division_data.code,
                        Division.division_id != division_id
                    )
                )
            )
            existing_division = existing_result.scalar_one_or_none()
            
            if existing_division:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Division with code '{division_data.code}' already exists in this college"
                )
        
        # Update division
        update_data = division_data.model_dump(exclude_unset=True)
        
        await db.execute(
            update(Division)
            .where(Division.division_id == division_id)
            .values(**update_data)
        )
        
        await db.commit()
        await db.refresh(division)
        
        logger.info(f"Division updated: {division.name} by staff {current_staff.staff_id}")
        
        return DivisionResponse(**division.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating division {division_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update division"
        )


@router.delete("/{division_id}", response_model=DivisionOperationResponse)
async def delete_division(
    division_id: UUID,
    current_staff: Staff = Depends(require_principal_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a division.
    Only Principal and College Admin can delete divisions.
    Cannot delete if division has departments.
    """
    try:
        # Get division
        result = await db.execute(
            select(Division).where(Division.division_id == division_id)
        )
        division = result.scalar_one_or_none()
        
        if not division:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Division not found"
            )
        
        # Check college access
        await check_college_access(current_staff, division.college_id)
        
        # Check if division has departments
        dept_count_result = await db.execute(
            select(func.count(Department.department_id))
            .where(Department.division_id == division_id)
        )
        dept_count = dept_count_result.scalar() or 0
        
        if dept_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete division with {dept_count} department(s). Please move or delete departments first."
            )
        
        # Remove staff assignments to this division
        await db.execute(
            update(Staff)
            .where(Staff.division_id == division_id)
            .values(division_id=None)
        )
        
        # Delete division
        await db.execute(
            delete(Division).where(Division.division_id == division_id)
        )
        
        await db.commit()
        
        logger.info(f"Division deleted: {division.name} by staff {current_staff.staff_id}")
        
        return DivisionOperationResponse(
            success=True,
            message="Division deleted successfully",
            divisionId=division_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting division {division_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete division"
        )


# Removed staff assignment endpoints - staff will be auto-assigned to division through department assignment

@router.get("/{division_id}/departments", response_model=List[dict])
async def get_division_departments(
    division_id: UUID,
    current_staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all departments within a division.
    """
    try:
        # Get division
        result = await db.execute(
            select(Division).where(Division.division_id == division_id)
        )
        division = result.scalar_one_or_none()
        
        if not division:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Division not found"
            )
        
        # Check college access
        await check_college_access(current_staff, division.college_id)
        
        # Get departments
        departments_result = await db.execute(
            select(Department)
            .where(Department.division_id == division_id)
            .order_by(Department.name)
        )
        departments = departments_result.scalars().all()
        
        return [dept.to_dict() for dept in departments]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting division departments {division_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve division departments"
        )


@router.get("/{division_id}/staff", response_model=List[dict])
async def get_division_staff(
    division_id: UUID,
    current_staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all staff assigned to a division.
    """
    try:
        # Get division
        result = await db.execute(
            select(Division).where(Division.division_id == division_id)
        )
        division = result.scalar_one_or_none()
        
        if not division:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Division not found"
            )
        
        # Check college access
        await check_college_access(current_staff, division.college_id)
        
        # Get staff
        staff_result = await db.execute(
            select(Staff)
            .where(Staff.division_id == division_id)
            .order_by(Staff.full_name)
        )
        staff_members = staff_result.scalars().all()
        
        return [staff.to_dict() for staff in staff_members]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting division staff {division_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve division staff"
        )