from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from uuid import UUID

from app.core.auth import (
    get_current_active_user, 
    get_principal_user,
    require_module_access
)
from app.db.database import get_db
from app.models.cms.models import CMSUser, CMSSystemModule
from app.services.cms.permission_service import get_permission_service

router = APIRouter()


@router.get("/modules/accessible", response_model=List[Dict[str, Any]])
async def get_accessible_modules(
    current_user: CMSUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all modules user has access to with their permissions"""
    permission_service = get_permission_service(db)
    accessible_modules = permission_service.get_user_accessible_modules(current_user)
    
    return [
        {
            "id": str(module_info["module"].id),
            "name": module_info["module"].name,
            "display_name": module_info["module"].display_name,
            "description": module_info["module"].description,
            "permissions": module_info["permissions"]
        }
        for module_info in accessible_modules
    ]


@router.get("/modules/for-role/{role}")
async def get_modules_for_role_creation(
    role: str,
    current_user: CMSUser = Depends(get_principal_user),
    db: Session = Depends(get_db)
):
    """Get modules visible when creating sub-accounts for a specific role"""
    if role not in ['admin', 'head', 'staff']:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    permission_service = get_permission_service(db)
    modules = permission_service.get_modules_for_role_creation(current_user, role)
    
    return [
        {
            "id": str(module["module"].id),
            "name": module["module"].name,
            "display_name": module["module"].display_name,
            "description": module["module"].description,
            "default_access": module["default_access"],
            "default_actions": module["default_actions"],
            "default_scope": module["default_scope"],
            "can_modify": module["can_modify"]
        }
        for module in modules
    ]


@router.get("/check/{module_name}/{action}")
async def check_module_access(
    module_name: str,
    action: str,
    current_user: CMSUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Check if current user has specific module access"""
    permission_service = get_permission_service(db)
    has_access = permission_service.has_module_access(current_user, module_name, action)
    
    return {
        "module": module_name,
        "action": action,
        "has_access": has_access,
        "user_role": current_user.role
    }


@router.get("/accessible-departments")
async def get_accessible_departments(
    current_user: CMSUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get departments user can access"""
    permission_service = get_permission_service(db)
    department_ids = permission_service.get_accessible_departments(current_user)
    
    return {
        "accessible_department_ids": [str(dept_id) for dept_id in department_ids],
        "user_role": current_user.role,
        "user_department_id": str(current_user.department_id) if current_user.department_id else None
    }


@router.get("/accessible-branches")
async def get_accessible_branches(
    current_user: CMSUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get branches user can access"""
    permission_service = get_permission_service(db)
    branch_ids = permission_service.get_accessible_branches(current_user)
    
    return {
        "accessible_branch_ids": [str(branch_id) for branch_id in branch_ids],
        "user_role": current_user.role,
        "user_branch_id": str(current_user.branch_id) if current_user.branch_id else None
    }


@router.post("/initialize-defaults")
async def initialize_default_permissions(
    current_user: CMSUser = Depends(get_principal_user),
    db: Session = Depends(get_db)
):
    """Initialize default module permissions for a user (Principal only)"""
    permission_service = get_permission_service(db)
    success = permission_service.create_default_permissions_for_user(current_user)
    
    if success:
        return {"message": "Default permissions initialized successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to initialize permissions")


@router.get("/system-modules")
async def get_all_system_modules(
    current_user: CMSUser = Depends(get_principal_user),
    db: Session = Depends(get_db)
):
    """Get all system modules (Principal only)"""
    modules = db.query(CMSSystemModule).all()
    
    return [
        {
            "id": str(module.id),
            "name": module.name,
            "display_name": module.display_name,
            "description": module.description,
            "is_core": module.is_core,
            "created_at": module.created_at
        }
        for module in modules
    ]