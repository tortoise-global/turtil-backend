from fastapi import APIRouter, HTTPException, status, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate as sqlalchemy_paginate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.department import Department
from app.schemas.department import (
    CreateDepartmentRequest, UpdateDepartmentRequest, DepartmentResponse,
    DepartmentWithStatsResponse, DepartmentActionResponse,
    AssignHODRequest, HODActionResponse
)
from .auth import get_current_cms_user

router = APIRouter(prefix="/cms/departments", tags=["CMS Department Management"])


@router.get("", response_model=Page[DepartmentWithStatsResponse])
async def get_departments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_cms_user)
):
    """
    Get paginated list of departments with user statistics.
    All authenticated users can view departments in their college.
    """
    try:
        # Build query for departments in current user's college
        query = select(Department).where(Department.college_id == current_user.college_id)
        query = query.order_by(Department.name)
        
        # Get paginated departments
        paginated_result = await sqlalchemy_paginate(db, query)
        
        # Add user statistics for each department
        department_responses = []
        for department in paginated_result.items:
            # Count total users in department
            total_users_result = await db.execute(
                select(func.count(User.id)).where(User.department_id == department.id)
            )
            total_users = total_users_result.scalar() or 0
            
            # Count active users in department
            active_users_result = await db.execute(
                select(func.count(User.id)).where(
                    and_(User.department_id == department.id, User.is_active == True)
                )
            )
            active_users = active_users_result.scalar() or 0
            
            # Get HOD information
            hod_name = None
            if department.hod_cms_user_id:
                hod_result = await db.execute(
                    select(User).where(User.id == department.hod_cms_user_id)
                )
                hod_user = hod_result.scalar_one_or_none()
                if hod_user:
                    hod_name = hod_user.full_name
            
            dept_dict = department.to_dict()
            department_responses.append(DepartmentWithStatsResponse(
                **dept_dict,
                totalUsers=total_users,
                activeUsers=active_users,
                hodName=hod_name
            ))
        
        return Page(
            items=department_responses,
            total=paginated_result.total,
            page=paginated_result.page,
            size=paginated_result.size,
            pages=paginated_result.pages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting departments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching departments"
        )


@router.post("", response_model=DepartmentActionResponse)
async def create_department(
    request: CreateDepartmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_cms_user)
):
    """
    Create a new department. Only Principal and College Admin can create departments.
    """
    try:
        # Check permissions
        if current_user.cms_role not in ['principal', 'college_admin']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can create departments"
            )
        
        # Check if department with same code already exists in college
        existing_dept_result = await db.execute(
            select(Department).where(
                and_(Department.code == request.code, Department.college_id == current_user.college_id)
            )
        )
        existing_dept = existing_dept_result.scalar_one_or_none()
        
        if existing_dept:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Department with code '{request.code}' already exists"
            )
        
        # Create new department
        new_department = Department(
            name=request.name,
            code=request.code,
            description=request.description,
            college_id=current_user.college_id
        )
        
        db.add(new_department)
        await db.commit()
        await db.refresh(new_department)
        
        return DepartmentActionResponse(
            success=True,
            message=f"Department '{request.name}' created successfully",
            departmentId=new_department.id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error creating department: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating department"
        )


@router.put("/{department_id}", response_model=DepartmentActionResponse)
async def update_department(
    department_id: int,
    request: UpdateDepartmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_cms_user)
):
    """
    Update a department. Only Principal and College Admin can update departments.
    """
    try:
        # Check permissions
        if current_user.cms_role not in ['principal', 'college_admin']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can update departments"
            )
        
        # Get department
        result = await db.execute(
            select(Department).where(
                and_(Department.id == department_id, Department.college_id == current_user.college_id)
            )
        )
        department = result.scalar_one_or_none()
        
        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found"
            )
        
        # Check if new code conflicts with existing department
        if request.code and request.code != department.code:
            existing_dept_result = await db.execute(
                select(Department).where(
                    and_(
                        Department.code == request.code,
                        Department.college_id == current_user.college_id,
                        Department.id != department_id
                    )
                )
            )
            existing_dept = existing_dept_result.scalar_one_or_none()
            
            if existing_dept:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Department with code '{request.code}' already exists"
                )
        
        # Update department fields
        if request.name is not None:
            department.name = request.name
        if request.code is not None:
            department.code = request.code
        if request.description is not None:
            department.description = request.description
        
        await db.commit()
        
        return DepartmentActionResponse(
            success=True,
            message=f"Department '{department.name}' updated successfully",
            departmentId=department_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error updating department: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating department"
        )


@router.put("/{department_id}/assign-hod", response_model=HODActionResponse)
async def assign_hod_to_department(
    department_id: int,
    request: AssignHODRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_cms_user)
):
    """
    Assign a Head of Department (HOD) to a department.
    Only Principal and College Admin can assign HODs.
    """
    try:
        # Check permissions
        if current_user.cms_role not in ['principal', 'college_admin']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can assign HODs"
            )
        
        # Get department
        dept_result = await db.execute(
            select(Department).where(
                and_(Department.id == department_id, Department.college_id == current_user.college_id)
            )
        )
        department = dept_result.scalar_one_or_none()
        
        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found"
            )
        
        # Get user to be assigned as HOD
        user_result = await db.execute(
            select(User).where(
                and_(
                    User.id == request.cmsUserId,
                    User.college_id == current_user.college_id,
                    User.is_active == True
                )
            )
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or inactive"
            )
        
        # Check if user is already HOD of another department
        if user.is_hod:
            existing_hod_dept_result = await db.execute(
                select(Department).where(Department.hod_cms_user_id == user.id)
            )
            existing_dept = existing_hod_dept_result.scalar_one_or_none()
            if existing_dept and existing_dept.id != department_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User is already HOD of {existing_dept.name} department"
                )
        
        # Remove current HOD if exists
        if department.hod_cms_user_id:
            current_hod_result = await db.execute(
                select(User).where(User.id == department.hod_cms_user_id)
            )
            current_hod = current_hod_result.scalar_one_or_none()
            if current_hod:
                current_hod.is_hod = False
        
        # Assign new HOD
        department.hod_cms_user_id = user.id
        user.is_hod = True
        user.department_id = department_id  # Ensure HOD is assigned to the department
        
        await db.commit()
        
        return HODActionResponse(
            success=True,
            message=f"{user.full_name} assigned as HOD of {department.name} department",
            departmentId=department_id,
            cmsUserId=user.id,
            hodName=user.full_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error assigning HOD: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while assigning HOD"
        )


@router.put("/{department_id}/remove-hod", response_model=HODActionResponse)
async def remove_hod_from_department(
    department_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_cms_user)
):
    """
    Remove the Head of Department (HOD) from a department.
    Only Principal and College Admin can remove HODs.
    """
    try:
        # Check permissions
        if current_user.cms_role not in ['principal', 'college_admin']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can remove HODs"
            )
        
        # Get department
        dept_result = await db.execute(
            select(Department).where(
                and_(Department.id == department_id, Department.college_id == current_user.college_id)
            )
        )
        department = dept_result.scalar_one_or_none()
        
        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found"
            )
        
        if not department.hod_cms_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Department does not have an assigned HOD"
            )
        
        # Get current HOD
        hod_result = await db.execute(
            select(User).where(User.id == department.hod_cms_user_id)
        )
        hod_user = hod_result.scalar_one_or_none()
        
        hod_name = hod_user.full_name if hod_user else "Unknown"
        
        # Remove HOD assignment
        if hod_user:
            hod_user.is_hod = False
        department.hod_cms_user_id = None
        
        await db.commit()
        
        return HODActionResponse(
            success=True,
            message=f"HOD removed from {department.name} department",
            departmentId=department_id,
            cmsUserId=hod_user.id if hod_user else None,
            hodName=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error removing HOD: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while removing HOD"
        )


@router.delete("/{department_id}", response_model=DepartmentActionResponse)
async def delete_department(
    department_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_cms_user)
):
    """
    Delete a department. Only Principal and College Admin can delete departments.
    Cannot delete department if it has assigned users.
    """
    try:
        # Check permissions
        if current_user.cms_role not in ['principal', 'college_admin']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can delete departments"
            )
        
        # Get department
        result = await db.execute(
            select(Department).where(
                and_(Department.id == department_id, Department.college_id == current_user.college_id)
            )
        )
        department = result.scalar_one_or_none()
        
        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found"
            )
        
        # Check if department has assigned users
        users_result = await db.execute(
            select(func.count(User.id)).where(User.department_id == department_id)
        )
        user_count = users_result.scalar() or 0
        
        if user_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete department. {user_count} users are assigned to this department. Remove users first."
            )
        
        # Remove HOD assignment if exists
        if department.hod_cms_user_id:
            hod_result = await db.execute(
                select(User).where(User.id == department.hod_cms_user_id)
            )
            hod_user = hod_result.scalar_one_or_none()
            if hod_user:
                hod_user.is_hod = False
        
        # Delete department
        department_name = department.name
        await db.delete(department)
        await db.commit()
        
        return DepartmentActionResponse(
            success=True,
            message=f"Department '{department_name}' deleted successfully",
            departmentId=department_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error deleting department: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting department"
        )