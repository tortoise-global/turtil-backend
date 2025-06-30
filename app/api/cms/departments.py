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

        # Execute query to get all departments
        result = await db.execute(query)
        departments = result.scalars().all()

        # Transform departments to response objects with stats
        department_responses = []
        for department in departments:
            # Count total staff in department
            total_staff_result = await db.execute(
                select(func.count(Staff.staff_id)).where(Staff.department_id == department.department_id)
            )
            total_staff = total_staff_result.scalar() or 0

            # Count active staff in department
            active_staff_result = await db.execute(
                select(func.count(Staff.staff_id)).where(
                    and_(Staff.department_id == department.department_id, Staff.is_active)
                )
            )
            active_staff = active_staff_result.scalar() or 0

            # Get HOD information
            hod_name = None
            if department.head_staff_id:
                hod_result = await db.execute(
                    select(Staff).where(Staff.staff_id == department.head_staff_id)
                )
                hod_staff = hod_result.scalar_one_or_none()
                if hod_staff:
                    hod_name = hod_staff.full_name

            department_responses.append(
                DepartmentWithStatsResponse(
                    id=str(department.department_id),
                    uuid=str(department.department_id),
                    name=department.name,
                    code=department.code,
                    description=department.description,
                    collegeId=str(department.college_id),
                    hodCmsStaffId=str(department.head_staff_id) if department.head_staff_id else None,
                    hodName=hod_name,
                    totalStaffs=total_staff,
                    activeStaffs=active_staff,
                    createdAt=department.created_at,
                    updatedAt=department.updated_at,
                )
            )

        # Use fastapi-pagination to paginate the transformed data
        from fastapi_pagination import paginate
        return paginate(department_responses)

    except HTTPException:
        raise
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Get departments", {"staff_id": str(current_staff.staff_id), "college_id": str(current_staff.college_id)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


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
            departmentId=str(new_department.department_id),
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Create department", {"staff_id": str(current_staff.staff_id), "department_name": request.name, "department_code": request.code}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.put(
    "/{departmentId}",
    response_model=DepartmentActionResponse,
    dependencies=[Depends(security)],
)
async def update_department(
    departmentId: str,
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
                    Department.department_id == departmentId,
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
                        Department.department_id != departmentId,
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
            departmentId=str(departmentId),
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Update department", {"staff_id": str(current_staff.staff_id), "department_id": departmentId}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.put(
    "/{departmentId}/assign-hod",
    response_model=HODActionResponse,
    dependencies=[Depends(security)],
)
async def assign_hod_to_department(
    departmentId: str,
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
                    Department.department_id == departmentId,
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
                    Staff.staff_id == request.staffId,
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
                select(Department).where(Department.head_staff_id == staff.staff_id)
            )
            existing_dept = existing_hod_dept_result.scalar_one_or_none()
            if existing_dept and str(existing_dept.department_id) != departmentId:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Staff is already HOD of {existing_dept.name} department",
                )

        # Remove current HOD if exists
        if department.head_staff_id:
            current_hod_result = await db.execute(
                select(Staff).where(Staff.staff_id == department.head_staff_id)
            )
            current_hod = current_hod_result.scalar_one_or_none()
            if current_hod:
                current_hod.is_hod = False

        # Assign new HOD
        department.head_staff_id = staff.staff_id
        staff.is_hod = True
        staff.department_id = departmentId  # Ensure HOD is assigned to the department

        await db.commit()

        return HODActionResponse(
            success=True,
            message=f"{staff.full_name} assigned as HOD of {department.name} department",
            departmentId=str(departmentId),
            staffId=str(staff.staff_id),
            hodName=staff.full_name,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Assign HOD", {"staff_id": str(current_staff.staff_id), "department_id": departmentId, "hod_staff_id": str(request.staffId)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.put(
    "/{departmentId}/remove-hod",
    response_model=HODActionResponse,
    dependencies=[Depends(security)],
)
async def remove_hod_from_department(
    departmentId: str,
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
                    Department.department_id == departmentId,
                    Department.college_id == current_staff.college_id,
                )
            )
        )
        department = dept_result.scalar_one_or_none()

        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Department not found"
            )

        if not department.head_staff_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Department does not have an assigned HOD",
            )

        # Get current HOD
        hod_result = await db.execute(
            select(Staff).where(Staff.staff_id == department.head_staff_id)
        )
        hod_staff = hod_result.scalar_one_or_none()

        # Remove HOD assignment
        if hod_staff:
            hod_staff.is_hod = False
        department.head_staff_id = None

        await db.commit()

        return HODActionResponse(
            success=True,
            message=f"HOD removed from {department.name} department",
            departmentId=str(departmentId),
            staffId=str(hod_staff.staff_id) if hod_staff else None,
            hodName=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Remove HOD", {"staff_id": str(current_staff.staff_id), "department_id": departmentId}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.delete(
    "/{departmentId}",
    response_model=DepartmentActionResponse,
    dependencies=[Depends(security)],
)
async def delete_department(
    departmentId: str,
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
                    Department.department_id == departmentId,
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
            select(func.count(Staff.staff_id)).where(Staff.department_id == departmentId)
        )
        staff_count = staff_result.scalar() or 0

        if staff_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete department. {staff_count} staff are assigned to this department. Remove staff first.",
            )

        # Remove HOD assignment if exists
        if department.head_staff_id:
            hod_result = await db.execute(
                select(Staff).where(Staff.staff_id == department.head_staff_id)
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
            departmentId=str(departmentId),
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Delete department", {"staff_id": str(current_staff.staff_id), "department_id": departmentId}, status.HTTP_500_INTERNAL_SERVER_ERROR)
