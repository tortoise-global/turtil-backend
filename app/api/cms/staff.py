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
from app.models.division import Division
from app.core.cms_auth import cms_auth
from app.core.aws import EmailService
from app.core.utils import generate_temporary_password
from app.schemas.staff_schemas import (
    InviteStaffRequest,
    InviteStaffResponse,
    StaffResponse,
    StaffActionResponse,
    UpdateStaffDetailsRequest,
    UpdateStaffDetailsResponse,
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
        # Check permissions - only Principal and Admin can invite CMS staffs
        if current_staff.cms_role not in ["principal", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and Admin can invite CMS staffs",
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

        # Validate department if provided and auto-assign division
        division_id = None
        department_id = None
        is_hod = False
        
        if request.department_id:
            # Validate department exists and belongs to college
            department_result = await db.execute(
                select(Department).where(
                    and_(
                        Department.department_id == request.department_id,
                        Department.college_id == current_staff.college_id
                    )
                )
            )
            department = department_result.scalar_one_or_none()
            if not department:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Department not found or does not belong to your college"
                )
            department_id = request.department_id
            
            # Auto-assign division from department
            if department.division_id:
                division_id = department.division_id
        
        # Set HOD status based on role and department assignment
        if request.cms_role == "hod" and department_id:
            is_hod = True

        # Create new CMS staff with invitation fields
        new_staff = Staff(
            email=request.email,
            full_name=request.full_name,  # Set name immediately
            contact_number=request.contact_number,  # Set contact number (mandatory)
            hashed_password=hashed_password,
            is_active=True,
            is_verified=False,  # Will be verified during first login
            college_id=current_staff.college_id,
            cms_role=request.cms_role,  # Use provided role
            division_id=division_id,    # Set division if provided
            department_id=department_id, # Set department if provided
            is_hod=is_hod,              # Set HOD status based on role
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
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Invite staff", {"inviter_staff_id": str(current_staff.staff_id), "invitee_email": request.email}, status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        if current_staff.cms_role not in ["principal", "admin", "hod"]:
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

        # Execute query to get all matching staff
        result = await db.execute(query)
        staff_list = result.scalars().all()
        
        # Transform staff models to StaffResponse objects
        staff_responses = []
        for staff in staff_list:
            staff_response = StaffResponse(
                staffId=str(staff.staff_id),
                uuid=str(staff.staff_id),
                email=staff.email,
                fullName=staff.full_name,
                contactNumber=staff.contact_number,
                isActive=staff.is_active,
                isVerified=staff.is_verified,
                cmsRole=staff.cms_role,
                collegeId=str(staff.college_id) if staff.college_id else None,
                departmentId=str(staff.department_id) if staff.department_id else None,
                invitationStatus=staff.invitation_status,
                temporaryPassword=staff.temporary_password,
                mustResetPassword=staff.must_reset_password,
                invitedByStaffId=str(staff.invited_by_staff_id) if staff.invited_by_staff_id else None,
                isHod=staff.is_hod,
                lastLoginAt=staff.last_login_at,
                createdAt=staff.created_at,
                updatedAt=staff.updated_at,
            )
            staff_responses.append(staff_response)
        
        # Use fastapi-pagination to paginate the transformed data
        from fastapi_pagination import paginate
        return paginate(staff_responses)

    except HTTPException:
        raise
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Get CMS staffs", {"staff_id": str(current_staff.staff_id), "role": current_staff.cms_role, "filters": {"status": status, "department_assigned": department_assigned, "role": role}}, status.HTTP_500_INTERNAL_SERVER_ERROR)


# Contact info endpoints removed - phone number now handled in staff invite/update endpoints


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
        if current_staff.cms_role in ["principal", "admin"]:
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

        # Determine if password reset is required (consolidated logic)
        requires_password_reset = (
            staff.must_reset_password or 
            staff.temporary_password or
            staff.invitation_status == "pending"
        )

        return StaffDetailsResponse(
            staffId=str(staff.staff_id),
            uuid=str(staff.staff_id),
            email=staff.email,
            fullName=staff.full_name,
            contactNumber=staff.contact_number,
            cmsRole=staff.cms_role,
            collegeId=str(staff.college_id) if staff.college_id else None,
            departmentId=str(staff.department_id) if staff.department_id else None,
            isHod=staff.is_hod,
            requiresPasswordReset=requires_password_reset,
            invitedByStaffId=str(staff.invited_by_staff_id) if staff.invited_by_staff_id else None,
            createdAt=staff.created_at,
            updatedAt=staff.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Get staff by ID", {"requester_staff_id": str(current_staff.staff_id), "target_staff_id": staffId}, status.HTTP_500_INTERNAL_SERVER_ERROR)


# Assign department endpoint removed - now handled by staff update-details endpoint


# Remove department endpoint removed - now handled by staff update-details endpoint


# Update username endpoint removed - now handled by staff update-details endpoint


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
        if current_staff.cms_role not in ["principal", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and Admin can delete staffs",
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
                select(Department).where(Department.head_staff_id == staffId)
            )
            departments = dept_result.scalars().all()
            for dept in departments:
                dept.head_staff_id = None

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
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Delete staff", {"staff_id": str(current_staff.staff_id), "target_staff_id": staffId}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.put(
    "/{staffId}/update-details", 
    response_model=UpdateStaffDetailsResponse, 
    dependencies=[Depends(security)]
)
async def update_staff_details(
    staffId: str,
    request: UpdateStaffDetailsRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Update comprehensive staff details including name, email, role, and assignments.
    Only Principal and College Admin can update staff details.
    Automatically handles division assignment through department assignment.
    """
    try:
        # Check permissions - only Principal and Admin can update staff details
        if current_staff.cms_role not in ["principal", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and Admin can update staff details",
            )

        # Get staff to update
        result = await db.execute(
            select(Staff).where(
                and_(Staff.staff_id == staffId, Staff.college_id == current_staff.college_id)
            )
        )
        staff = result.scalar_one_or_none()

        if not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Staff not found"
            )

        # Prevent updating principal role unless current user is principal
        if staff.cms_role == "principal" and current_staff.cms_role != "principal":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal can update another Principal's details",
            )

        updated_fields = []
        
        # Update basic details
        if request.full_name is not None:
            staff.full_name = request.full_name
            updated_fields.append("full_name")
            
        if request.email is not None:
            # Check if email is already taken
            existing_staff_result = await db.execute(
                select(Staff).where(
                    and_(
                        Staff.email == request.email,
                        Staff.staff_id != staffId
                    )
                )
            )
            existing_staff = existing_staff_result.scalar_one_or_none()
            if existing_staff:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email address is already in use by another staff member"
                )
            staff.email = request.email
            updated_fields.append("email")

        if request.contact_number is not None:
            staff.contact_number = request.contact_number
            updated_fields.append("contact_number")

        if request.cms_role is not None:
            old_role = staff.cms_role
            staff.cms_role = request.cms_role
            updated_fields.append("cms_role")
            
            # Handle HOD status based on role change
            if old_role == "hod" and request.cms_role != "hod":
                # Removing HOD role
                staff.is_hod = False
                updated_fields.append("is_hod (removed due to role change)")
            elif request.cms_role == "hod" and staff.department_id:
                # Assigning HOD role and staff has department
                staff.is_hod = True
                updated_fields.append("is_hod (assigned due to role change)")

        # Handle department assignment and auto-assign division
        if request.department_id is not None:
            if request.department_id == "":
                # Empty string means remove department assignment
                staff.department_id = None
                staff.division_id = None  # Also remove division
                # Also remove HOD status if removing department
                if staff.is_hod:
                    staff.is_hod = False
                    updated_fields.append("is_hod (removed due to department removal)")
                updated_fields.extend(["department_id", "division_id"])
            else:
                # Validate department exists and belongs to college
                department_result = await db.execute(
                    select(Department).where(
                        and_(
                            Department.department_id == request.department_id,
                            Department.college_id == current_staff.college_id
                        )
                    )
                )
                department = department_result.scalar_one_or_none()
                if not department:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Department not found or does not belong to your college"
                    )
                
                # Update department and auto-assign division
                staff.department_id = request.department_id
                updated_fields.append("department_id")
                
                if department.division_id:
                    staff.division_id = department.division_id
                    updated_fields.append("division_id (auto-assigned)")
                
                # Handle HOD assignment based on role
                if staff.cms_role == "hod":
                    staff.is_hod = True
                    updated_fields.append("is_hod (assigned due to HOD role + department)")

        await db.commit()
        await db.refresh(staff)

        return UpdateStaffDetailsResponse(
            success=True,
            message=f"Staff details updated successfully",
            staffId=str(staffId),
            updatedFields=updated_fields,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Update staff details", {"staff_id": str(current_staff.staff_id), "target_staff_id": staffId}, status.HTTP_500_INTERNAL_SERVER_ERROR)


