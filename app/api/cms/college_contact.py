"""
College Contact Management API
Endpoints for managing college contact information and staff assignments
"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.database import get_db
from app.models.staff import Staff
from app.models.college import College
from app.schemas.college_contact_schemas import (
    CollegeContactResponse,
    UpdateCollegeContactRequest,
    CollegeContactActionResponse,
)
from .deps import get_current_staff

router = APIRouter(prefix="/cms/college", tags=["CMS College Contact Management"])

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


@router.get(
    "/contact",
    response_model=CollegeContactResponse,
    dependencies=[Depends(security)],
)
async def get_college_contact(
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Get current college contact information.
    All authenticated staff can view college contact details.
    """
    try:
        # Get college information
        result = await db.execute(
            select(College).where(College.college_id == current_staff.college_id)
        )
        college = result.scalar_one_or_none()

        if not college:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="College not found"
            )

        # Get contact staff information if contact_staff_id exists
        contact_staff_name = None
        contact_staff_email = None
        if college.contact_staff_id:
            contact_staff_result = await db.execute(
                select(Staff).where(Staff.staff_id == college.contact_staff_id)
            )
            contact_staff = contact_staff_result.scalar_one_or_none()
            if contact_staff:
                contact_staff_name = contact_staff.full_name
                contact_staff_email = contact_staff.email

        return CollegeContactResponse(
            contact_number=college.contact_number,
            contact_staff_id=str(college.contact_staff_id) if college.contact_staff_id else None,
            contact_staff_name=contact_staff_name,
            contact_staff_email=contact_staff_email,
        )

    except HTTPException:
        raise
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Get college contact", {"staff_id": str(current_staff.staff_id), "college_id": str(current_staff.college_id)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.put(
    "/contact",
    response_model=CollegeContactActionResponse,
    dependencies=[Depends(security)],
)
async def update_college_contact(
    request: UpdateCollegeContactRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Update college contact information by assigning a staff member as contact person.
    Only Principal and Admin can update college contact information.
    
    This endpoint will:
    1. Set the staff member as the college contact person
    2. Copy the staff member's contact number to college contact number
    """
    try:
        # Check permissions - only Principal and Admin can update college contact
        if current_staff.cms_role not in ["principal", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and Admin can update college contact information",
            )

        # Get college
        college_result = await db.execute(
            select(College).where(College.college_id == current_staff.college_id)
        )
        college = college_result.scalar_one_or_none()

        if not college:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="College not found"
            )

        # Get target staff member
        staff_result = await db.execute(
            select(Staff).where(
                and_(
                    Staff.staff_id == request.contact_staff_id,
                    Staff.college_id == current_staff.college_id
                )
            )
        )
        target_staff = staff_result.scalar_one_or_none()

        if not target_staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Staff member not found or does not belong to your college"
            )

        # Ensure target staff has a contact number
        if not target_staff.contact_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Staff member '{target_staff.full_name}' does not have a contact number. Please update their contact information first."
            )

        # Update college contact information
        college.contact_staff_id = request.contact_staff_id
        college.contact_number = target_staff.contact_number

        await db.commit()

        return CollegeContactActionResponse(
            success=True,
            message=f"College contact updated successfully. {target_staff.full_name} is now the college contact person.",
            contact_number=target_staff.contact_number,
            contact_staff_name=target_staff.full_name,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Update college contact", {"staff_id": str(current_staff.staff_id), "target_staff_id": request.contact_staff_id}, status.HTTP_500_INTERNAL_SERVER_ERROR)