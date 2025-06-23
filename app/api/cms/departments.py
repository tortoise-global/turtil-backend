from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate as sqlalchemy_paginate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.database import get_db
from app.models.staff import Staff
from app.models.department import Department
from app.schemas.department_schemas import (
    CreateDepartmentRequest,
    UpdateDepartmentRequest,
    DepartmentWithStatsResponse,
    DepartmentActionResponse,
    AssignHODRequest,
    HODActionResponse,
)
from .deps import get_current_staff

router = APIRouter(prefix="/cms/departments", tags=["CMS Department Management"])

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


@router.get(
    "",
    response_model=Page[DepartmentWithStatsResponse],
    dependencies=[Depends(security)],
)
async def get_departments(
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Get paginated list of departments with staff statistics.
    All authenticated staff can view departments in their college.
    """
    try:
        # Build query for departments in current staff's college
        query = select(Department).where(
            Department.college_id == current_staff.college_id
        )
        query = query.order_by(Department.name)

        # Get paginated departments
        paginated_result = await sqlalchemy_paginate(db, query)

        # Add staff statistics for each department
        department_responses = []
        for department in paginated_result.items:
            # Count total staff in department
            total_staff_result = await db.execute(
                select(func.count(Staff.id)).where(Staff.department_id == department.id)
            )
            total_staff = total_staff_result.scalar() or 0

            # Count active staff in department
            active_staff_result = await db.execute(
                select(func.count(Staff.id)).where(
                    and_(Staff.department_id == department.id, Staff.is_active)
                )
            )
            active_staff = active_staff_result.scalar() or 0

            # Get HOD information
            hod_name = None
            if department.hod_cms_staff_id:
                hod_result = await db.execute(
                    select(Staff).where(Staff.id == department.hod_cms_staff_id)
                )
                hod_staff = hod_result.scalar_one_or_none()
                if hod_staff:
                    hod_name = hod_staff.full_name

            dept_dict = department.to_dict()
            department_responses.append(
                DepartmentWithStatsResponse(
                    **dept_dict,
                    totalStaffs=total_staff,
                    activeStaffs=active_staff,
                    hodName=hod_name,
                )
            )

        return Page(
            items=department_responses,
            total=paginated_result.total,
            page=paginated_result.page,
            size=paginated_result.size,
            pages=paginated_result.pages,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting departments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching departments",
        )


@router.post(
    "", response_model=DepartmentActionResponse, dependencies=[Depends(security)]
)
async def create_department(
    request: CreateDepartmentRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Create a new department. Only Principal and College Admin can create departments.
    """
    try:
        # Check permissions
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can create departments",
            )

        # Check if department with same code already exists in college
        existing_dept_result = await db.execute(
            select(Department).where(
                and_(
                    Department.code == request.code,
                    Department.college_id == current_staff.college_id,
                )
            )
        )
        existing_dept = existing_dept_result.scalar_one_or_none()

        if existing_dept:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Department with code '{request.code}' already exists",
            )

        # Create new department
        new_department = Department(
            name=request.name,
            code=request.code,
            description=request.description,
            college_id=current_staff.college_id,
        )

        db.add(new_department)
        await db.commit()
        await db.refresh(new_department)

        return DepartmentActionResponse(
            success=True,
            message=f"Department '{request.name}' created successfully",
            departmentId=new_department.id,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error creating department: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating department",
        )


@router.put(
    "/{departmentId}",
    response_model=DepartmentActionResponse,
    dependencies=[Depends(security)],
)
async def update_department(
    departmentId: int,
    request: UpdateDepartmentRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Update a department. Only Principal and College Admin can update departments.
    """
    try:
        # Check permissions
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can update departments",
            )

        # Get department
        result = await db.execute(
            select(Department).where(
                and_(
                    Department.id == departmentId,
                    Department.college_id == current_staff.college_id,
                )
            )
        )
        department = result.scalar_one_or_none()

        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Department not found"
            )

        # Check if new code conflicts with existing department
        if request.code and request.code != department.code:
            existing_dept_result = await db.execute(
                select(Department).where(
                    and_(
                        Department.code == request.code,
                        Department.college_id == current_staff.college_id,
                        Department.id != departmentId,
                    )
                )
            )
            existing_dept = existing_dept_result.scalar_one_or_none()

            if existing_dept:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Department with code '{request.code}' already exists",
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
            departmentId=departmentId,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error updating department: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating department",
        )


@router.put(
    "/{departmentId}/assign-hod",
    response_model=HODActionResponse,
    dependencies=[Depends(security)],
)
async def assign_hod_to_department(
    departmentId: int,
    request: AssignHODRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Assign a Head of Department (HOD) to a department.
    Only Principal and College Admin can assign HODs.
    """
    try:
        # Check permissions
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can assign HODs",
            )

        # Get department
        dept_result = await db.execute(
            select(Department).where(
                and_(
                    Department.id == departmentId,
                    Department.college_id == current_staff.college_id,
                )
            )
        )
        department = dept_result.scalar_one_or_none()

        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Department not found"
            )

        # Get staff to be assigned as HOD
        staff_result = await db.execute(
            select(Staff).where(
                and_(
                    Staff.id == request.staffId,
                    Staff.college_id == current_staff.college_id,
                    Staff.is_active,
                )
            )
        )
        staff = staff_result.scalar_one_or_none()

        if not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Staff not found or inactive",
            )

        # Check if staff is already HOD of another department
        if staff.is_hod:
            existing_hod_dept_result = await db.execute(
                select(Department).where(Department.hod_cms_staff_id == staff.id)
            )
            existing_dept = existing_hod_dept_result.scalar_one_or_none()
            if existing_dept and existing_dept.id != departmentId:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Staff is already HOD of {existing_dept.name} department",
                )

        # Remove current HOD if exists
        if department.hod_cms_staff_id:
            current_hod_result = await db.execute(
                select(Staff).where(Staff.id == department.hod_cms_staff_id)
            )
            current_hod = current_hod_result.scalar_one_or_none()
            if current_hod:
                current_hod.is_hod = False

        # Assign new HOD
        department.hod_cms_staff_id = staff.id
        staff.is_hod = True
        staff.department_id = departmentId  # Ensure HOD is assigned to the department

        await db.commit()

        return HODActionResponse(
            success=True,
            message=f"{staff.full_name} assigned as HOD of {department.name} department",
            departmentId=departmentId,
            staffId=staff.id,
            hodName=staff.full_name,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error assigning HOD: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while assigning HOD",
        )


@router.put(
    "/{departmentId}/remove-hod",
    response_model=HODActionResponse,
    dependencies=[Depends(security)],
)
async def remove_hod_from_department(
    departmentId: int,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Remove the Head of Department (HOD) from a department.
    Only Principal and College Admin can remove HODs.
    """
    try:
        # Check permissions
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can remove HODs",
            )

        # Get department
        dept_result = await db.execute(
            select(Department).where(
                and_(
                    Department.id == departmentId,
                    Department.college_id == current_staff.college_id,
                )
            )
        )
        department = dept_result.scalar_one_or_none()

        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Department not found"
            )

        if not department.hod_cms_staff_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Department does not have an assigned HOD",
            )

        # Get current HOD
        hod_result = await db.execute(
            select(Staff).where(Staff.id == department.hod_cms_staff_id)
        )
        hod_staff = hod_result.scalar_one_or_none()

        # Remove HOD assignment
        if hod_staff:
            hod_staff.is_hod = False
        department.hod_cms_staff_id = None

        await db.commit()

        return HODActionResponse(
            success=True,
            message=f"HOD removed from {department.name} department",
            departmentId=departmentId,
            staffId=hod_staff.id if hod_staff else None,
            hodName=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error removing HOD: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while removing HOD",
        )


@router.delete(
    "/{departmentId}",
    response_model=DepartmentActionResponse,
    dependencies=[Depends(security)],
)
async def delete_department(
    departmentId: int,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Delete a department. Only Principal and College Admin can delete departments.
    Cannot delete department if it has assigned staff.
    """
    try:
        # Check permissions
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can delete departments",
            )

        # Get department
        result = await db.execute(
            select(Department).where(
                and_(
                    Department.id == departmentId,
                    Department.college_id == current_staff.college_id,
                )
            )
        )
        department = result.scalar_one_or_none()

        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Department not found"
            )

        # Check if department has assigned staff
        staff_result = await db.execute(
            select(func.count(Staff.id)).where(Staff.department_id == departmentId)
        )
        staff_count = staff_result.scalar() or 0

        if staff_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete department. {staff_count} staff are assigned to this department. Remove staff first.",
            )

        # Remove HOD assignment if exists
        if department.hod_cms_staff_id:
            hod_result = await db.execute(
                select(Staff).where(Staff.id == department.hod_cms_staff_id)
            )
            hod_staff = hod_result.scalar_one_or_none()
            if hod_staff:
                hod_staff.is_hod = False

        # Delete department
        department_name = department.name
        await db.delete(department)
        await db.commit()

        return DepartmentActionResponse(
            success=True,
            message=f"Department '{department_name}' deleted successfully",
            departmentId=departmentId,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error deleting department: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting department",
        )
