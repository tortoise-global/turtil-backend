from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.security import HTTPBearer
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate as sqlalchemy_paginate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional

from app.database import get_db
from app.models.staff import Staff
from app.models.college import College
from app.models.department import Department
from app.core.cms_auth import cms_auth
from app.core.aws import EmailService
from app.core.utils import generate_temporary_password
from app.schemas.staff_schemas import (
    InviteStaffRequest,
    InviteStaffResponse,
    StaffResponse,
    AssignDepartmentRequest,
    StaffActionResponse,
    UpdateUsernameRequest,
    UpdateUsernameResponse,
    UpdateContactRequest,
    UpdateContactResponse,
    ContactInfoResponse,
)
from app.schemas.staff_schemas import StaffDetailsResponse
from .deps import get_current_staff

router = APIRouter(prefix="/cms/staff", tags=["CMS Staff Management"])

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


@router.post(
    "/invite", response_model=InviteStaffResponse, dependencies=[Depends(security)]
)
async def invite_staff(
    request: InviteStaffRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Invite a new staff to the college. Only Principal and College Admin can invite staffs.

    - Creates staff with temporary password
    - Sends invitation email with credentials
    - Staff status: invitation_status='pending'
    - Automatically invalidates staff sessions when deleted
    """
    try:
        # Check permissions - only Principal and College Admin can invite CMS staffs
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can invite CMS staffs",
            )

        # Check if CMS staff already exists
        result = await db.execute(select(Staff).where(Staff.email == request.email))
        existing_staff = result.scalar_one_or_none()

        if existing_staff:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CMS staff with this email already exists",
            )

        # Generate temporary password
        temporary_password = generate_temporary_password(12)
        hashed_password = cms_auth.get_password_hash(temporary_password)

        # Create new CMS staff with invitation fields
        new_staff = Staff(
            email=request.email,
            full_name="",  # Will be filled during onboarding
            hashed_password=hashed_password,
            is_active=True,
            is_verified=False,  # Will be verified during first login
            college_id=current_staff.college_id,
            cms_role="staff",  # Default role, can be changed later
            invitation_status="pending",
            temporary_password=True,
            must_reset_password=True,
            invited_by_staff_id=current_staff.staff_id,
        )

        db.add(new_staff)
        await db.flush()  # Get the ID without committing

        # Get college information for email
        college_result = await db.execute(
            select(College).where(College.college_id == current_staff.college_id)
        )
        college = college_result.scalar_one()

        # Send invitation email
        try:
            await EmailService.send_staff_invitation_email(
                email=request.email,
                temporary_password=temporary_password,
                inviter_name=current_staff.full_name,
                college_name=college.name,
            )
        except Exception as email_error:
            # Rollback CMS staff creation if email fails
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send invitation email: {str(email_error)}",
            )

        await db.commit()
        await db.refresh(new_staff)

        return InviteStaffResponse(
            success=True,
            message="CMS staff invitation sent successfully",
            staffId=str(new_staff.staff_id),
            email=request.email,
            temporaryPassword=temporary_password,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error inviting staff: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while inviting CMS staff",
        )


@router.get("", response_model=Page[StaffResponse], dependencies=[Depends(security)])
async def get_staff(
    status: Optional[str] = Query(
        None, description="Filter by approval status: 'approved' or 'unapproved'"
    ),
    department_assigned: Optional[bool] = Query(
        None, description="Filter by department assignment"
    ),
    department_id: Optional[int] = Query(
        None, description="Filter by specific department ID"
    ),
    role: Optional[str] = Query(None, description="Filter by CMS role"),
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Get paginated list of CMS staffs with flexible filtering.

    Query Parameters:
    - status: 'approved' (accepted/active) or 'unapproved' (pending)
    - department_assigned: true (has department) or false (no department)
    - department_id: specific department ID
    - role: CMS role filter
    - page/size: pagination (handled automatically)

    Permissions:
    - Principal/College Admin: Can see all CMS staffs in college
    - HOD: Can see CMS staffs in their department
    - Staff: Cannot access this endpoint
    """
    try:
        # Check permissions
        if current_staff.cms_role not in ["principal", "college_admin", "hod"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view CMS staffs",
            )

        # Build base query - scope to current CMS staff's college
        query = select(Staff).where(Staff.college_id == current_staff.college_id)

        # Apply role-based filtering
        if current_staff.cms_role == "hod":
            # HOD can only see CMS staffs in their department
            query = query.where(Staff.department_id == current_staff.department_id)

        # Apply status filter
        if status == "approved":
            query = query.where(Staff.invitation_status.in_(["accepted", "active"]))
        elif status == "unapproved":
            query = query.where(Staff.invitation_status == "pending")

        # Apply department assignment filter
        if department_assigned is True:
            query = query.where(Staff.department_id.isnot(None))
        elif department_assigned is False:
            query = query.where(Staff.department_id.is_(None))

        # Apply specific department filter
        if department_id is not None:
            query = query.where(Staff.department_id == department_id)

        # Apply role filter
        if role:
            query = query.where(Staff.cms_role == role)

        # Order by creation date (newest first)
        query = query.order_by(Staff.created_at.desc())

        # Use SQLAlchemy pagination for efficient database queries
        paginated_result = await sqlalchemy_paginate(db, query)

        # Convert CMS staffs to response format
        staff_responses = []
        for staff in paginated_result.items:
            staff_responses.append(StaffResponse(
                staffId=str(staff.staff_id),
                uuid=str(staff.staff_id),
                email=staff.email,
                fullName=staff.full_name,
                phoneNumber=None,  # Staff model doesn't have phone_number
                isActive=staff.is_active,
                isVerified=staff.is_verified,
                cmsRole=staff.cms_role,
                collegeId=staff.college_id,
                departmentId=staff.department_id,
                invitationStatus=staff.invitation_status,
                temporaryPassword=staff.temporary_password,
                mustResetPassword=staff.must_reset_password,
                invitedByStaffId=staff.invited_by_staff_id,
                isHod=staff.is_hod,
                lastLoginAt=staff.last_login_at,
                createdAt=staff.created_at,
                updatedAt=staff.updated_at,
            ))

        # Return paginated response
        return Page(
            items=staff_responses,
            total=paginated_result.total,
            page=paginated_result.page,
            size=paginated_result.size,
            pages=paginated_result.pages,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting CMS staffs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching CMS staffs",
        )


@router.get(
    "/{staffId}",
    response_model=StaffDetailsResponse,
    dependencies=[Depends(security)],
)
async def get_staff_by_id(
    staffId: str,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Get staff details by ID.

    Permissions:
    - Principal/College Admin: Can view any staff in their college
    - HOD: Can view staffs in their department
    - Staff: Can only view their own profile
    """
    try:
        # Build query based on role permissions
        if current_staff.cms_role in ["principal", "college_admin"]:
            # Can view any staff in college
            query = select(Staff).where(
                and_(Staff.staff_id == staffId, Staff.college_id == current_staff.college_id)
            )
        elif current_staff.cms_role == "hod":
            # Can only view staffs in same department
            query = select(Staff).where(
                and_(
                    Staff.staff_id == staffId,
                    Staff.college_id == current_staff.college_id,
                    Staff.department_id == current_staff.department_id,
                )
            )
        else:  # staff
            # Can only view their own profile
            if staffId != str(current_staff.staff_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to view this staff",
                )
            query = select(Staff).where(Staff.staff_id == staffId)

        result = await db.execute(query)
        staff = result.scalar_one_or_none()

        if not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found"
            )

        return StaffDetailsResponse(
            staffId=str(staff.staff_id),
            uuid=str(staff.staff_id),
            email=staff.email,
            fullName=staff.full_name,
            cmsRole=staff.cms_role,
            collegeId=staff.college_id,
            departmentId=staff.department_id,
            invitationStatus=staff.invitation_status,
            mustResetPassword=staff.must_reset_password,
            isHod=staff.is_hod,
            createdAt=staff.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting staff by ID: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        )


@router.put(
    "/{staffId}/assign-department",
    response_model=StaffActionResponse,
    dependencies=[Depends(security)],
)
async def assign_staff_to_department(
    staffId: str,
    request: AssignDepartmentRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Assign a staff to a department. Only Principal and College Admin can assign departments.
    """
    try:
        # Check permissions
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can assign departments",
            )

        # Get staff
        result = await db.execute(
            select(Staff).where(
                and_(Staff.staff_id == staffId, Staff.college_id == current_staff.college_id)
            )
        )
        staff = result.scalar_one_or_none()

        if not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found"
            )

        # Validate department exists and belongs to same college
        dept_result = await db.execute(
            select(Department).where(
                and_(
                    Department.department_id == request.departmentId,
                    Department.college_id == current_staff.college_id,
                )
            )
        )
        department = dept_result.scalar_one_or_none()

        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Department not found"
            )

        # Update staff's department
        staff.department_id = request.departmentId
        await db.commit()

        return StaffActionResponse(
            success=True,
            message=f"Staff assigned to {department.name} department successfully",
            staffId=str(staffId),
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error assigning staff to department: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while assigning department",
        )


@router.put(
    "/{staffId}/remove-department",
    response_model=StaffActionResponse,
    dependencies=[Depends(security)],
)
async def remove_staff_from_department(
    staffId: str,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Remove a staff from their current department. Only Principal and College Admin can do this.
    """
    try:
        # Check permissions
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can remove department assignments",
            )

        # Get staff
        result = await db.execute(
            select(Staff).where(
                and_(Staff.staff_id == staffId, Staff.college_id == current_staff.college_id)
            )
        )
        staff = result.scalar_one_or_none()

        if not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found"
            )

        # Remove department assignment and HOD status
        staff.department_id = None
        staff.is_hod = False  # Remove HOD status when removing from department
        await db.commit()

        return StaffActionResponse(
            success=True,
            message="Staff removed from department successfully",
            staffId=str(staffId),
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error removing staff from department: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while removing department assignment",
        )


@router.put(
    "/{staffId}/update-username",
    response_model=UpdateUsernameResponse,
    dependencies=[Depends(security)],
)
async def update_staff_username(
    staffId: str,
    request: UpdateUsernameRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Update staff username (full_name). 
    
    Permissions:
    - Principal/College Admin: Can update any staff in their college
    - HOD: Can update staff in their department
    - Staff: Can update their own username only
    """
    try:
        # Build query based on role permissions
        if current_staff.cms_role in ["principal", "college_admin"]:
            # Can update any staff in college
            query = select(Staff).where(
                and_(Staff.staff_id == staffId, Staff.college_id == current_staff.college_id)
            )
        elif current_staff.cms_role == "hod":
            # Can only update staffs in same department
            query = select(Staff).where(
                and_(
                    Staff.staff_id == staffId,
                    Staff.college_id == current_staff.college_id,
                    Staff.department_id == current_staff.department_id,
                )
            )
        else:  # staff
            # Can only update their own username
            if staffId != str(current_staff.staff_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to update this staff's username",
                )
            query = select(Staff).where(Staff.staff_id == staffId)

        result = await db.execute(query)
        staff = result.scalar_one_or_none()

        if not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found"
            )

        # Update staff's full name (username)
        staff.full_name = request.fullName
        await db.commit()

        return UpdateUsernameResponse(
            success=True,
            message="Staff username updated successfully",
            staffId=str(staffId),
            fullName=request.fullName,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error updating staff username: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating username",
        )


@router.delete(
    "/{staffId}", response_model=StaffActionResponse, dependencies=[Depends(security)]
)
async def delete_staff(
    staffId: str,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Delete a staff. Only Principal and College Admin can delete staffs.
    Cannot delete the principal or yourself.
    Automatically invalidates all staff sessions for real-time logout.
    """
    try:
        # Check permissions
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can delete staffs",
            )

        # Prevent self-deletion
        if staffId == str(current_staff.staff_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account",
            )

        # Get staff
        result = await db.execute(
            select(Staff).where(
                and_(Staff.staff_id == staffId, Staff.college_id == current_staff.college_id)
            )
        )
        staff = result.scalar_one_or_none()

        if not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found"
            )

        # Prevent deleting principal
        if staff.cms_role == "principal":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete principal account",
            )

        # Check if staff is the contact person for the college
        if current_staff.college_id:
            college_result = await db.execute(
                select(College).where(College.college_id == current_staff.college_id)
            )
            college = college_result.scalar_one_or_none()
            
            if college and college.contact_staff_id == staffId:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete staff who is the primary contact person. Please update contact information first.",
                )

        # Invalidate all staff sessions before deletion (real-time logout)
        await cms_auth.invalidate_staff_sessions(staffId)

        # Remove HOD assignment from any departments they may be heading
        if staff.is_hod:
            dept_result = await db.execute(
                select(Department).where(Department.hod_staff_id == staffId)
            )
            departments = dept_result.scalars().all()
            for dept in departments:
                dept.hod_staff_id = None

        # Delete staff
        await db.delete(staff)
        await db.commit()

        return StaffActionResponse(
            success=True,
            message="Staff deleted successfully and all sessions invalidated",
            staffId=str(staffId),
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error deleting staff: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting staff",
        )


@router.put(
    "/contact-info", response_model=UpdateContactResponse, dependencies=[Depends(security)]
)
async def update_contact_info(
    request: UpdateContactRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Update college contact information. Only Principal and College Admin can update contact info.
    Validates that the contact staff exists and belongs to the same college.
    """
    try:
        # Check permissions
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can update contact information",
            )

        # Validate that the contact staff exists and belongs to the same college
        contact_staff_result = await db.execute(
            select(Staff).where(
                and_(
                    Staff.staff_id == request.contactStaffId,
                    Staff.college_id == current_staff.college_id,
                    Staff.is_active == True
                )
            )
        )
        contact_staff = contact_staff_result.scalar_one_or_none()

        if not contact_staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contact staff not found or not active in this college",
            )

        # Get the college
        college_result = await db.execute(
            select(College).where(College.college_id == current_staff.college_id)
        )
        college = college_result.scalar_one_or_none()

        if not college:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="College not found",
            )

        # Update contact information
        college.contact_number = request.contact_number
        college.contact_staff_id = request.contact_staff_id
        await db.commit()

        return UpdateContactResponse(
            success=True,
            message=f"Contact information updated successfully. {contact_staff.full_name} is now the primary contact.",
            contactNumber=request.contactNumber,
            contactStaffId=request.contactStaffId,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error updating contact info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating contact information",
        )


@router.get(
    "/contact-info", response_model=ContactInfoResponse, dependencies=[Depends(security)]
)
async def get_contact_info(
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Get current college contact information. Only staff members of the college can view this.
    """
    try:
        # Get the college
        college_result = await db.execute(
            select(College).where(College.college_id == current_staff.college_id)
        )
        college = college_result.scalar_one_or_none()

        if not college:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="College not found",
            )

        # Get contact staff details if contact_staff_id is set
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

        return ContactInfoResponse(
            contactNumber=college.contact_number,
            contactStaffId=college.contact_staff_id,
            contactStaffName=contact_staff_name,
            contactStaffEmail=contact_staff_email,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting contact info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while getting contact information",
        )
