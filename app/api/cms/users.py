from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate as sqlalchemy_paginate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.college import College
from app.models.department import Department
from app.core.cms_auth import cms_auth
from app.core.aws import EmailService
from app.core.utils import generate_temporary_password
from app.schemas.user_management import (
    InviteUserRequest, InviteUserResponse, UserResponse, UserDetailsResponse,
    AssignDepartmentRequest, UserActionResponse
)
from app.schemas.cms_auth import CMSUserProfileResponse
from .auth import get_current_cms_user

router = APIRouter(prefix="/cms/users", tags=["CMS User Management"])

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


@router.post("/invite", response_model=InviteUserResponse)
async def invite_user(
    request: InviteUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_cms_user)
):
    """
    Invite a new user to the college. Only Principal and College Admin can invite users.
    
    - Creates user with temporary password
    - Sends invitation email with credentials
    - User status: invitation_status='pending'
    - Automatically invalidates user sessions when deleted
    """
    try:
        # Check permissions - only Principal and College Admin can invite users
        if current_user.cms_role not in ['principal', 'college_admin']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can invite users"
            )
        
        # Check if user already exists
        result = await db.execute(select(User).where(User.email == request.email))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Generate temporary password
        temporary_password = generate_temporary_password(12)
        hashed_password = cms_auth.get_password_hash(temporary_password)
        
        # Create new user with invitation fields
        new_user = User(
            email=request.email,
            first_name="",  # Will be filled during onboarding
            last_name="",   # Will be filled during onboarding
            hashed_password=hashed_password,
            is_active=True,
            is_verified=False,  # Will be verified during first login
            college_id=current_user.college_id,
            cms_role='staff',  # Default role, can be changed later
            invitation_status='pending',
            temporary_password=True,
            must_reset_password=True,
            invited_by_cms_user_id=current_user.id
        )
        
        db.add(new_user)
        await db.flush()  # Get the ID without committing
        
        # Get college information for email
        college_result = await db.execute(select(College).where(College.id == current_user.college_id))
        college = college_result.scalar_one()
        
        # Send invitation email
        try:
            await EmailService.send_user_invitation_email(
                email=request.email,
                temporary_password=temporary_password,
                inviter_name=current_user.full_name,
                college_name=college.name
            )
        except Exception as email_error:
            # Rollback user creation if email fails
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send invitation email: {str(email_error)}"
            )
        
        await db.commit()
        await db.refresh(new_user)
        
        return InviteUserResponse(
            success=True,
            message="User invitation sent successfully",
            cmsUserId=new_user.id,
            email=request.email,
            temporaryPassword=temporary_password
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error inviting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while inviting user"
        )


@router.get("", response_model=Page[UserResponse])
async def get_users(
    status: Optional[str] = Query(None, description="Filter by approval status: 'approved' or 'unapproved'"),
    department_assigned: Optional[bool] = Query(None, description="Filter by department assignment"),
    department_id: Optional[int] = Query(None, description="Filter by specific department ID"),
    role: Optional[str] = Query(None, description="Filter by CMS role"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_cms_user)
):
    """
    Get paginated list of users with flexible filtering.
    
    Query Parameters:
    - status: 'approved' (accepted/active) or 'unapproved' (pending)
    - department_assigned: true (has department) or false (no department)
    - department_id: specific department ID
    - role: CMS role filter
    - page/size: pagination (handled automatically)
    
    Permissions:
    - Principal/College Admin: Can see all users in college
    - HOD: Can see users in their department
    - Staff: Cannot access this endpoint
    """
    try:
        # Check permissions
        if current_user.cms_role not in ['principal', 'college_admin', 'hod']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view users"
            )
        
        # Build base query - scope to current user's college
        query = select(User).where(User.college_id == current_user.college_id)
        
        # Apply role-based filtering
        if current_user.cms_role == 'hod':
            # HOD can only see users in their department
            query = query.where(User.department_id == current_user.department_id)
        
        # Apply status filter
        if status == 'approved':
            query = query.where(User.invitation_status.in_(['accepted', 'active']))
        elif status == 'unapproved':
            query = query.where(User.invitation_status == 'pending')
        
        # Apply department assignment filter
        if department_assigned is True:
            query = query.where(User.department_id.isnot(None))
        elif department_assigned is False:
            query = query.where(User.department_id.is_(None))
        
        # Apply specific department filter
        if department_id is not None:
            query = query.where(User.department_id == department_id)
        
        # Apply role filter
        if role:
            query = query.where(User.cms_role == role)
        
        # Order by creation date (newest first)
        query = query.order_by(User.created_at.desc())
        
        # Use SQLAlchemy pagination for efficient database queries
        paginated_result = await sqlalchemy_paginate(db, query)
        
        # Convert users to response format with isHod field
        user_responses = []
        for user in paginated_result.items:
            user_dict = user.to_dict()
            user_responses.append(UserResponse(**user_dict))
        
        # Return paginated response
        return Page(
            items=user_responses,
            total=paginated_result.total,
            page=paginated_result.page,
            size=paginated_result.size,
            pages=paginated_result.pages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching users"
        )


@router.get("/{user_id}", response_model=CMSUserProfileResponse)
async def get_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_cms_user)
):
    """
    Get user details by ID.
    
    Permissions:
    - Principal/College Admin: Can view any user in their college
    - HOD: Can view users in their department
    - Staff: Can only view their own profile
    """
    try:
        # Build query based on role permissions
        if current_user.cms_role in ['principal', 'college_admin']:
            # Can view any user in college
            query = select(User).where(
                and_(User.id == user_id, User.college_id == current_user.college_id)
            )
        elif current_user.cms_role == 'hod':
            # Can only view users in same department
            query = select(User).where(
                and_(
                    User.id == user_id,
                    User.college_id == current_user.college_id,
                    User.department_id == current_user.department_id
                )
            )
        else:  # staff
            # Can only view their own profile
            if user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to view this user"
                )
            query = select(User).where(User.id == user_id)
        
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return CMSUserProfileResponse(
            cmsUserId=user.id,
            uuid=str(user.uuid),
            email=user.email,
            firstName=user.first_name,
            lastName=user.last_name,
            fullName=user.full_name,
            phoneNumber=user.phone_number,
            cmsRole=user.cms_role,
            collegeId=user.college_id,
            departmentId=user.department_id,
            invitationStatus=user.invitation_status,
            mustResetPassword=user.must_reset_password,
            isHod=user.is_hod,
            createdAt=user.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting user by ID: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


@router.put("/{user_id}/assign-department", response_model=UserActionResponse)
async def assign_user_to_department(
    user_id: int,
    request: AssignDepartmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_cms_user)
):
    """
    Assign a user to a department. Only Principal and College Admin can assign departments.
    """
    try:
        # Check permissions
        if current_user.cms_role not in ['principal', 'college_admin']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can assign departments"
            )
        
        # Get user
        result = await db.execute(
            select(User).where(
                and_(User.id == user_id, User.college_id == current_user.college_id)
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Validate department exists and belongs to same college
        dept_result = await db.execute(
            select(Department).where(
                and_(Department.id == request.departmentId, Department.college_id == current_user.college_id)
            )
        )
        department = dept_result.scalar_one_or_none()
        
        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found"
            )
        
        # Update user's department
        user.department_id = request.departmentId
        await db.commit()
        
        return UserActionResponse(
            success=True,
            message=f"User assigned to {department.name} department successfully",
            cmsUserId=user_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error assigning user to department: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while assigning department"
        )


@router.put("/{user_id}/remove-department", response_model=UserActionResponse)
async def remove_user_from_department(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_cms_user)
):
    """
    Remove a user from their current department. Only Principal and College Admin can do this.
    """
    try:
        # Check permissions
        if current_user.cms_role not in ['principal', 'college_admin']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can remove department assignments"
            )
        
        # Get user
        result = await db.execute(
            select(User).where(
                and_(User.id == user_id, User.college_id == current_user.college_id)
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Remove department assignment and HOD status
        user.department_id = None
        user.is_hod = False  # Remove HOD status when removing from department
        await db.commit()
        
        return UserActionResponse(
            success=True,
            message="User removed from department successfully",
            cmsUserId=user_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error removing user from department: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while removing department assignment"
        )


@router.delete("/{user_id}", response_model=UserActionResponse)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_cms_user)
):
    """
    Delete a user. Only Principal and College Admin can delete users.
    Cannot delete the principal or yourself.
    Automatically invalidates all user sessions for real-time logout.
    """
    try:
        # Check permissions
        if current_user.cms_role not in ['principal', 'college_admin']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can delete users"
            )
        
        # Prevent self-deletion
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        # Get user
        result = await db.execute(
            select(User).where(
                and_(User.id == user_id, User.college_id == current_user.college_id)
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prevent deleting principal
        if user.cms_role == 'principal':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete principal account"
            )
        
        # Invalidate all user sessions before deletion (real-time logout)
        await cms_auth.invalidate_user_sessions(user_id)
        
        # Remove HOD assignment from any departments they may be heading
        if user.is_hod:
            dept_result = await db.execute(
                select(Department).where(Department.hod_cms_user_id == user_id)
            )
            departments = dept_result.scalars().all()
            for dept in departments:
                dept.hod_cms_user_id = None
        
        # Delete user
        await db.delete(user)
        await db.commit()
        
        return UserActionResponse(
            success=True,
            message="User deleted successfully and all sessions invalidated",
            cmsUserId=user_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error deleting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting user"
        )