import logging
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.cms.models import (
    Branch,
    CMSCollegeModule,
    CMSRoleModuleAccess,
    CMSSystemModule,
    CMSUser,
    CMSUserModulePermission,
    Department,
)

logger = logging.getLogger(__name__)


class PermissionService:
    """Comprehensive permission service for role-based access control"""

    # Define role hierarchy for inheritance
    ROLE_HIERARCHY = {
        "principal": ["principal", "admin", "head", "staff"],
        "admin": ["admin", "head", "staff"],
        "head": ["head", "staff"],
        "staff": ["staff"],
    }

    # Default permissions by role and module
    DEFAULT_PERMISSIONS = {
        "principal": {
            "programs_structure": {
                "actions": ["read", "write", "delete", "manage"],
                "scope": "all",
            },
            "students": {
                "actions": ["read", "write", "delete", "manage", "export", "import"],
                "scope": "all",
            },
            "lists": {"actions": ["read", "write", "delete"], "scope": "all"},
            "alerts": {"actions": ["read", "write", "delete"], "scope": "all"},
            "attendance": {
                "actions": ["read", "write", "delete", "manage", "export", "import"],
                "scope": "all",
            },
            "timetable": {
                "actions": ["read", "write", "delete", "manage"],
                "scope": "all",
            },
            "results": {
                "actions": ["read", "write", "delete", "manage"],
                "scope": "all",
            },
            "assignments": {
                "actions": ["read", "write", "delete", "manage"],
                "scope": "all",
            },
            "academic_calendar": {
                "actions": ["read", "write", "delete", "manage"],
                "scope": "all",
            },
            "document_request": {
                "actions": ["read", "write", "delete", "manage"],
                "scope": "all",
            },
            "events": {
                "actions": ["read", "write", "delete", "manage"],
                "scope": "all",
            },
            "placements": {
                "actions": ["read", "write", "delete", "manage"],
                "scope": "all",
            },
            "account": {"actions": ["read", "write", "manage"], "scope": "all"},
        },
        "admin": {
            "programs_structure": {
                "actions": ["read", "write", "delete", "manage"],
                "scope": "college",
            },
            "students": {
                "actions": ["read", "write", "delete", "manage", "export", "import"],
                "scope": "college",
            },
            "lists": {"actions": ["read", "write", "delete"], "scope": "college"},
            "alerts": {"actions": ["read", "write", "delete"], "scope": "college"},
            "attendance": {
                "actions": ["read", "write", "delete", "manage", "export", "import"],
                "scope": "college",
            },
            "timetable": {
                "actions": ["read", "write", "delete", "manage"],
                "scope": "college",
            },
            "results": {
                "actions": ["read", "write", "delete", "manage"],
                "scope": "college",
            },
            "assignments": {
                "actions": ["read", "write", "delete", "manage"],
                "scope": "college",
            },
            "academic_calendar": {
                "actions": ["read", "write", "delete", "manage"],
                "scope": "college",
            },
            "document_request": {
                "actions": ["read", "write", "delete", "manage"],
                "scope": "college",
            },
            "events": {
                "actions": ["read", "write", "delete", "manage"],
                "scope": "college",
            },
            "placements": {
                "actions": ["read", "write", "delete", "manage"],
                "scope": "college",
            },
            "account": {"actions": ["read", "write"], "scope": "self"},
        },
        "head": {
            "programs_structure": {"actions": ["read", "write"], "scope": "department"},
            "students": {"actions": ["read", "write", "export"], "scope": "department"},
            "lists": {"actions": ["read", "write"], "scope": "self"},
            "alerts": {"actions": ["read", "write"], "scope": "department"},
            "attendance": {
                "actions": ["read", "write", "export", "import"],
                "scope": "department",
            },
            "timetable": {"actions": ["read", "write"], "scope": "department"},
            "results": {"actions": ["read", "write"], "scope": "department"},
            "assignments": {"actions": ["read", "write"], "scope": "department"},
            "academic_calendar": {"actions": ["read", "write"], "scope": "department"},
            "events": {"actions": ["read", "write"], "scope": "department"},
            "placements": {"actions": ["read", "write"], "scope": "department"},
            "account": {"actions": ["read"], "scope": "self"},
        },
        "staff": {
            "students": {"actions": ["read"], "scope": "branch"},
            "lists": {"actions": ["read", "write"], "scope": "self"},
            "alerts": {"actions": ["read", "write"], "scope": "branch"},
            "attendance": {
                "actions": ["read", "write", "export", "import"],
                "scope": "branch",
            },
            "results": {"actions": ["read", "write"], "scope": "branch"},
            "assignments": {"actions": ["read", "write"], "scope": "branch"},
            "academic_calendar": {"actions": ["read", "write"], "scope": "branch"},
            "account": {"actions": ["read"], "scope": "self"},
        },
    }

    # Modules not visible for specific roles during account creation
    ROLE_MODULE_VISIBILITY = {
        "admin": [],  # All modules visible
        "head": ["document_request"],  # Limited access
        "staff": [
            "programs_structure",
            "timetable",
            "document_request",
            "events",
            "placements",
        ],
        "principal": [],  # All modules visible
    }

    def __init__(self, db: Session):
        self.db = db

    def has_module_access(
        self, user: CMSUser, module_name: str, action: str = "read"
    ) -> bool:
        """Check if user has access to a specific module with given action"""
        try:
            # Principal always has access
            if user.role == "principal":
                return True

            # Check if module is enabled for college
            if not self._is_module_enabled_for_college(user.college_id, module_name):
                return False

            # Get user's specific permissions
            user_permission = self._get_user_module_permission(user.id, module_name)

            if user_permission:
                return user_permission.has_access and action in (
                    user_permission.allowed_actions or []
                )

            # Fall back to default role permissions
            return self._has_default_role_permission(user.role, module_name, action)

        except Exception as e:
            logger.error(f"Error checking module access for user {user.id}: {e}")
            return False

    def get_user_accessible_modules(self, user: CMSUser) -> List[Dict[str, Any]]:
        """Get all modules user has access to with their permissions"""
        try:
            accessible_modules = []

            # Get all system modules
            modules = self.db.query(CMSSystemModule).all()

            for module in modules:
                if self.has_module_access(user, module.name):
                    permission_details = self._get_module_permission_details(
                        user, module.name
                    )
                    accessible_modules.append(
                        {"module": module, "permissions": permission_details}
                    )

            return accessible_modules

        except Exception as e:
            logger.error(f"Error getting accessible modules for user {user.id}: {e}")
            return []

    def can_access_department_data(
        self, user: CMSUser, target_department_id: UUID
    ) -> bool:
        """Check if user can access data from specific department"""
        try:
            if user.role == "principal":
                return True

            if user.role == "admin":
                return user.college_id == self._get_department_college_id(
                    target_department_id
                )

            if user.role == "head":
                return user.department_id == target_department_id

            if user.role == "staff":
                # Staff can access their department's data and cross-department subjects
                if user.department_id == target_department_id:
                    return True
                # Check if they teach subjects in this department
                managed_depts = user.managed_departments or []
                return str(target_department_id) in managed_depts

            return False

        except Exception as e:
            logger.error(f"Error checking department access for user {user.id}: {e}")
            return False

    def can_access_branch_data(self, user: CMSUser, target_branch_id: UUID) -> bool:
        """Check if user can access data from specific branch"""
        try:
            if user.role in ["principal", "admin"]:
                return True

            if user.role == "head":
                # Can access branches within their department
                branch_dept_id = self._get_branch_department_id(target_branch_id)
                return user.department_id == branch_dept_id

            if user.role == "staff":
                # Can access their assigned branch and cross-department branches for teaching
                if user.branch_id == target_branch_id:
                    return True
                # Check cross-department access
                branch_dept_id = self._get_branch_department_id(target_branch_id)
                managed_depts = user.managed_departments or []
                return str(branch_dept_id) in managed_depts

            return False

        except Exception as e:
            logger.error(f"Error checking branch access for user {user.id}: {e}")
            return False

    def get_accessible_departments(self, user: CMSUser) -> List[UUID]:
        """Get list of department IDs user can access"""
        try:
            if user.role == "principal":
                # All departments in any college
                return [dept.id for dept in self.db.query(Department).all()]

            if user.role == "admin":
                # All departments in user's college
                return [
                    dept.id
                    for dept in self.db.query(Department)
                    .filter(Department.college_id == user.college_id)
                    .all()
                ]

            if user.role == "head":
                # Only their department
                return [user.department_id] if user.department_id else []

            if user.role == "staff":
                # Their department + managed departments for cross-teaching
                accessible = [user.department_id] if user.department_id else []
                managed_depts = user.managed_departments or []
                accessible.extend([UUID(dept_id) for dept_id in managed_depts])
                return list(set(accessible))  # Remove duplicates

            return []

        except Exception as e:
            logger.error(
                f"Error getting accessible departments for user {user.id}: {e}"
            )
            return []

    def get_accessible_branches(self, user: CMSUser) -> List[UUID]:
        """Get list of branch IDs user can access"""
        try:
            if user.role in ["principal", "admin"]:
                # All branches in user's accessible colleges
                accessible_dept_ids = self.get_accessible_departments(user)
                return [
                    branch.id
                    for branch in self.db.query(Branch)
                    .filter(Branch.department_id.in_(accessible_dept_ids))
                    .all()
                ]

            if user.role == "head":
                # All branches in their department
                return [
                    branch.id
                    for branch in self.db.query(Branch)
                    .filter(Branch.department_id == user.department_id)
                    .all()
                ]

            if user.role == "staff":
                # Their branch + branches in managed departments
                accessible_dept_ids = self.get_accessible_departments(user)
                return [
                    branch.id
                    for branch in self.db.query(Branch)
                    .filter(Branch.department_id.in_(accessible_dept_ids))
                    .all()
                ]

            return []

        except Exception as e:
            logger.error(f"Error getting accessible branches for user {user.id}: {e}")
            return []

    def get_modules_for_role_creation(
        self, creating_user: CMSUser, target_role: str
    ) -> List[Dict[str, Any]]:
        """Get modules visible when creating sub-accounts for a specific role"""
        try:
            # Get all enabled modules for the college
            college_modules = (
                self.db.query(CMSSystemModule, CMSCollegeModule)
                .join(
                    CMSCollegeModule, CMSSystemModule.id == CMSCollegeModule.module_id
                )
                .filter(CMSCollegeModule.college_id == creating_user.college_id)
                .filter(CMSCollegeModule.is_enabled == True)
                .all()
            )

            visible_modules = []
            hidden_modules = self.ROLE_MODULE_VISIBILITY.get(target_role, [])

            for system_module, college_module in college_modules:
                if system_module.name not in hidden_modules:
                    # Get default permissions for this role-module combination
                    default_perms = self.DEFAULT_PERMISSIONS.get(target_role, {}).get(
                        system_module.name, {}
                    )

                    visible_modules.append(
                        {
                            "module": system_module,
                            "default_access": bool(default_perms),
                            "default_actions": default_perms.get("actions", []),
                            "default_scope": default_perms.get("scope", "self"),
                            "can_modify": creating_user.role
                            in [
                                "principal",
                                "admin",
                            ],  # Principal and admin can modify permissions
                        }
                    )

            return visible_modules

        except Exception as e:
            logger.error(f"Error getting modules for role creation: {e}")
            return []

    def create_default_permissions_for_user(self, user: CMSUser) -> bool:
        """Create default module permissions when user is created"""
        try:
            role_permissions = self.DEFAULT_PERMISSIONS.get(user.role, {})

            for module_name, permissions in role_permissions.items():
                module = (
                    self.db.query(CMSSystemModule)
                    .filter(CMSSystemModule.name == module_name)
                    .first()
                )
                if module:
                    # Check if permission already exists
                    existing = (
                        self.db.query(CMSUserModulePermission)
                        .filter(CMSUserModulePermission.user_id == user.id)
                        .filter(CMSUserModulePermission.module_id == module.id)
                        .first()
                    )

                    if not existing:
                        permission = CMSUserModulePermission(
                            user_id=user.id,
                            module_id=module.id,
                            has_access=True,
                            allowed_actions=permissions["actions"],
                            access_scope=permissions["scope"],
                        )
                        self.db.add(permission)

            self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Error creating default permissions for user {user.id}: {e}")
            self.db.rollback()
            return False

    # Private helper methods
    def _is_module_enabled_for_college(
        self, college_id: UUID, module_name: str
    ) -> bool:
        """Check if module is enabled for the college"""
        return (
            self.db.query(CMSCollegeModule)
            .join(CMSSystemModule, CMSCollegeModule.module_id == CMSSystemModule.id)
            .filter(CMSCollegeModule.college_id == college_id)
            .filter(CMSSystemModule.name == module_name)
            .filter(CMSCollegeModule.is_enabled == True)
            .first()
            is not None
        )

    def _get_user_module_permission(
        self, user_id: UUID, module_name: str
    ) -> Optional[CMSUserModulePermission]:
        """Get user's specific module permission"""
        return (
            self.db.query(CMSUserModulePermission)
            .join(
                CMSSystemModule, CMSUserModulePermission.module_id == CMSSystemModule.id
            )
            .filter(CMSUserModulePermission.user_id == user_id)
            .filter(CMSSystemModule.name == module_name)
            .first()
        )

    def _has_default_role_permission(
        self, role: str, module_name: str, action: str
    ) -> bool:
        """Check default role permissions"""
        role_perms = self.DEFAULT_PERMISSIONS.get(role, {})
        module_perms = role_perms.get(module_name, {})
        return action in module_perms.get("actions", [])

    def _get_module_permission_details(
        self, user: CMSUser, module_name: str
    ) -> Dict[str, Any]:
        """Get detailed permission info for user-module combination"""
        user_permission = self._get_user_module_permission(user.id, module_name)

        if user_permission:
            return {
                "actions": user_permission.allowed_actions or [],
                "scope": user_permission.access_scope,
                "custom": True,
            }

        # Return default permissions
        default_perms = self.DEFAULT_PERMISSIONS.get(user.role, {}).get(module_name, {})
        return {
            "actions": default_perms.get("actions", []),
            "scope": default_perms.get("scope", "self"),
            "custom": False,
        }

    def _get_department_college_id(self, department_id: UUID) -> UUID:
        """Get college ID for a department"""
        dept = self.db.query(Department).filter(Department.id == department_id).first()
        return dept.college_id if dept else None

    def _get_branch_department_id(self, branch_id: UUID) -> UUID:
        """Get department ID for a branch"""
        branch = self.db.query(Branch).filter(Branch.id == branch_id).first()
        return branch.department_id if branch else None


# Create global permission service instance
def get_permission_service(db: Session = None) -> PermissionService:
    """Get permission service instance"""
    return PermissionService(db)
