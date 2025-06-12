from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum

from app.schemas.cms.users import CMSUserRole


# Hierarchical User Creation
class HierarchicalUserCreate(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: Optional[str] = Field(None, description="User password (optional - temp generated if not provided)")
    full_name: str = Field(..., description="Full name")
    phone: Optional[str] = Field(None, description="Phone number")
    role: CMSUserRole = Field(..., description="User role")
    department_id: Optional[UUID] = Field(None, description="Department UUID")
    branch_id: Optional[UUID] = Field(None, description="Branch UUID")
    degree_id: Optional[UUID] = Field(None, description="Degree UUID")
    managed_departments: Optional[List[str]] = Field([], description="Additional department UUIDs for cross-department access")
    teaching_subjects: Optional[List[str]] = Field([], description="Subject UUIDs for teaching assignments")


class HierarchicalUserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    department_id: Optional[UUID]
    branch_id: Optional[UUID]
    created_by: Optional[UUID]
    managed_departments: List[str]
    teaching_subjects: List[str]
    is_active: bool
    created_at: int
    last_login: Optional[int]

    model_config = ConfigDict(from_attributes=True)


# Role Hierarchy
class RoleHierarchyInfo(BaseModel):
    level: int = Field(..., description="Hierarchy level (1=highest)")
    can_create: List[str] = Field(..., description="Roles this role can create")
    description: str = Field(..., description="Role description")


class RoleHierarchyResponse(BaseModel):
    current_user_role: str
    hierarchy: Dict[str, RoleHierarchyInfo]
    can_create_roles: List[str]


# Authority Transfer
class AuthorityTransfer(BaseModel):
    target_user_id: UUID = Field(..., description="User to transfer authority to")
    confirmation: bool = Field(..., description="Confirmation of transfer")


class AuthorityTransferResponse(BaseModel):
    message: str
    former_principal: UUID
    new_principal: UUID
    transferred_at: int


# Department Delegation
class DepartmentDelegation(BaseModel):
    department_id: UUID = Field(..., description="Department to delegate")
    head_user_id: UUID = Field(..., description="Head user to delegate to")


class DepartmentDelegationResponse(BaseModel):
    message: str
    department_id: UUID
    head_user_id: UUID
    delegated_at: int


# Permission Granting
class ModulePermissionGrant(BaseModel):
    user_id: UUID = Field(..., description="User to grant permission to")
    module_name: str = Field(..., description="Module name")
    actions: List[str] = Field(..., description="Actions to grant (read, write, delete, etc.)")
    scope: Optional[str] = Field("department", description="Permission scope")


class ModulePermissionResponse(BaseModel):
    message: str
    user_id: UUID
    module: str
    actions: List[str]
    granted_by: UUID
    granted_at: int


# Hierarchy Tree
class HierarchyTreeNode(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    level: int
    children: List['HierarchyTreeNode'] = []

    model_config = ConfigDict(from_attributes=True)


class HierarchyTreeResponse(BaseModel):
    hierarchy_tree: Optional[HierarchyTreeNode]
    total_created_users: int


# User Access Management
class UserAccessRevocation(BaseModel):
    reason: Optional[str] = Field("access_revoked", description="Reason for revocation")


class UserAccessResponse(BaseModel):
    message: str
    user_id: UUID
    action_by: UUID
    timestamp: int


# Cross-Department Assignment
class CrossDepartmentTeachingAssignment(BaseModel):
    teacher_id: UUID = Field(..., description="Teacher UUID")
    department_id: UUID = Field(..., description="Department UUID")
    subject_ids: List[UUID] = Field(..., description="Subject UUIDs")


class TeachingAssignmentResponse(BaseModel):
    teacher_id: UUID
    primary_department_id: Optional[UUID]
    managed_departments: List[str]
    teaching_subjects: List[Dict[str, Any]]

    model_config = ConfigDict(from_attributes=True)


# User Filtering and Search
class UserFilterParams(BaseModel):
    role: Optional[str] = None
    department_id: Optional[UUID] = None
    created_by_me: Optional[bool] = False
    is_active: Optional[bool] = None
    search_query: Optional[str] = None


# Bulk Operations
class BulkUserStatusUpdate(BaseModel):
    user_ids: List[UUID] = Field(..., description="List of user UUIDs")
    is_active: bool = Field(..., description="New active status")


class BulkPermissionGrant(BaseModel):
    user_ids: List[UUID] = Field(..., description="List of user UUIDs")
    module_permissions: List[ModulePermissionGrant] = Field(..., description="Permissions to grant")


# Statistics
class HierarchyStatistics(BaseModel):
    total_users_created: int
    users_by_role: Dict[str, int]
    active_users: int
    recent_creations: int
    departments_managed: int

    model_config = ConfigDict(from_attributes=True)


# User Creation Success Response
class UserCreationResponse(BaseModel):
    id: UUID
    email: str
    role: str
    created_by: UUID
    temporary_password: Optional[str]
    message: str

    model_config = ConfigDict(from_attributes=True)


# Fix forward reference
HierarchyTreeNode.model_rebuild()