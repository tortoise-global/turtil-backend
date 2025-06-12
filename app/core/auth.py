import logging
from typing import Callable, List, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.auth_manager import auth_manager
from app.db.database import get_db
from app.models.cms.models import CMSUser
from app.services.cms.permission_service import get_permission_service

logger = logging.getLogger(__name__)
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> CMSUser:
    token = credentials.credentials

    # Verify token with Redis validation
    payload = auth_manager.verify_token(token)

    user_id = payload.get("sub")
    if user_id is None:
        logger.warning("Token missing user ID")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user with cache-first approach
    user = auth_manager.get_user_from_cache_or_db(user_id, db)
    if user is None:
        logger.warning(f"User not found: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: CMSUser = Depends(get_current_user),
) -> CMSUser:
    if not current_user.is_active:
        logger.warning(f"Inactive user attempted access: {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Account deactivated"
        )
    return current_user


async def get_admin_user(
    current_user: CMSUser = Depends(get_current_active_user),
) -> CMSUser:
    if current_user.role not in ["admin", "principal"]:
        logger.warning(f"Insufficient permissions for user: {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    return current_user


async def get_principal_user(
    current_user: CMSUser = Depends(get_current_active_user),
) -> CMSUser:
    if current_user.role != "principal":
        logger.warning(f"Principal access denied for user: {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Principal access required"
        )
    return current_user


async def get_super_admin_user(
    current_user: CMSUser = Depends(get_current_active_user),
) -> CMSUser:
    if current_user.role != "super_admin":
        logger.warning(f"Super admin access denied for user: {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Super admin access required"
        )
    return current_user


async def get_lecturer_user(
    current_user: CMSUser = Depends(get_current_active_user),
) -> CMSUser:
    if current_user.role not in ["staff", "head", "admin", "principal"]:
        logger.warning(f"Lecturer access denied for user: {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Lecturer access required"
        )
    return current_user


def require_roles(allowed_roles: List[str]):
    async def role_checker(
        current_user: CMSUser = Depends(get_current_active_user),
    ) -> CMSUser:
        if current_user.role not in allowed_roles:
            logger.warning(
                f"Role {current_user.role} not in allowed roles: {allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {', '.join(allowed_roles)}",
            )
        return current_user

    return role_checker


def require_college_access(current_user: CMSUser = Depends(get_current_active_user)):
    async def college_checker(college_id: str) -> CMSUser:
        if (
            str(current_user.college_id) != college_id
            and current_user.role != "super_admin"
        ):
            logger.warning(
                f"College access denied for user {current_user.id} to college {college_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this college",
            )
        return current_user

    return college_checker


# Advanced Permission-Based Dependencies


def require_module_access(module_name: str, action: str = "read"):
    """Require access to specific module with given action"""

    async def module_checker(
        current_user: CMSUser = Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ) -> CMSUser:
        permission_service = get_permission_service(db)

        if not permission_service.has_module_access(current_user, module_name, action):
            logger.warning(
                f"Module access denied for user {current_user.id} to {module_name}:{action}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to {module_name} module",
            )
        return current_user

    return module_checker


def require_department_access(target_department_id: Optional[UUID] = None):
    """Require access to specific department data"""

    async def department_checker(
        current_user: CMSUser = Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ) -> CMSUser:
        permission_service = get_permission_service(db)

        # If no specific department provided, check if user has any department access
        if target_department_id is None:
            accessible_departments = permission_service.get_accessible_departments(
                current_user
            )
            if not accessible_departments:
                logger.warning(f"No department access for user {current_user.id}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="No department access"
                )
        else:
            if not permission_service.can_access_department_data(
                current_user, target_department_id
            ):
                logger.warning(
                    f"Department access denied for user {current_user.id} to dept {target_department_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this department",
                )
        return current_user

    return department_checker


def require_branch_access(target_branch_id: Optional[UUID] = None):
    """Require access to specific branch data"""

    async def branch_checker(
        current_user: CMSUser = Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ) -> CMSUser:
        permission_service = get_permission_service(db)

        # If no specific branch provided, check if user has any branch access
        if target_branch_id is None:
            accessible_branches = permission_service.get_accessible_branches(
                current_user
            )
            if not accessible_branches:
                logger.warning(f"No branch access for user {current_user.id}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="No branch access"
                )
        else:
            if not permission_service.can_access_branch_data(
                current_user, target_branch_id
            ):
                logger.warning(
                    f"Branch access denied for user {current_user.id} to branch {target_branch_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this branch",
                )
        return current_user

    return branch_checker


def require_module_and_scope_access(
    module_name: str, action: str = "read", scope_check: str = None
):
    """Require both module access and appropriate scope (department/branch) access"""

    async def combined_checker(
        current_user: CMSUser = Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ) -> CMSUser:
        permission_service = get_permission_service(db)

        # Check module access first
        if not permission_service.has_module_access(current_user, module_name, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to {module_name} module",
            )

        # Check scope access if specified
        if scope_check == "department":
            accessible_departments = permission_service.get_accessible_departments(
                current_user
            )
            if not accessible_departments:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No department access for this module",
                )
        elif scope_check == "branch":
            accessible_branches = permission_service.get_accessible_branches(
                current_user
            )
            if not accessible_branches:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No branch access for this module",
                )

        return current_user

    return combined_checker


# Data Filtering Dependencies


async def get_accessible_department_filter(
    current_user: CMSUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[UUID]:
    """Get list of department IDs user can access for filtering queries"""
    permission_service = get_permission_service(db)
    return permission_service.get_accessible_departments(current_user)


async def get_accessible_branch_filter(
    current_user: CMSUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[UUID]:
    """Get list of branch IDs user can access for filtering queries"""
    permission_service = get_permission_service(db)
    return permission_service.get_accessible_branches(current_user)


# Convenience Dependencies for Common Module Operations

# Students Module
students_read_access = require_module_access("students", "read")
students_write_access = require_module_access("students", "write")
students_manage_access = require_module_access("students", "manage")

# Attendance Module
attendance_read_access = require_module_access("attendance", "read")
attendance_write_access = require_module_access("attendance", "write")
attendance_import_access = require_module_access("attendance", "import")

# Results Module
results_read_access = require_module_access("results", "read")
results_write_access = require_module_access("results", "write")

# Assignments Module
assignments_read_access = require_module_access("assignments", "read")
assignments_write_access = require_module_access("assignments", "write")

# Timetable Module
timetable_read_access = require_module_access("timetable", "read")
timetable_write_access = require_module_access("timetable", "write")

# Events Module
events_read_access = require_module_access("events", "read")
events_write_access = require_module_access("events", "write")

# Placements Module
placements_read_access = require_module_access("placements", "read")
placements_write_access = require_module_access("placements", "write")

# Document Requests Module
document_requests_read_access = require_module_access("document_request", "read")
document_requests_write_access = require_module_access("document_request", "write")

# Programs & Structure Module
programs_read_access = require_module_access("programs_structure", "read")
programs_write_access = require_module_access("programs_structure", "write")
programs_manage_access = require_module_access("programs_structure", "manage")
