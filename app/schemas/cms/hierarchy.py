from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.cms.users import CMSUserRole


# Hierarchical User Creation
class HierarchicalUserCreate(BaseModel):
    """
    Hierarchical user creation schema for Indian academic system

    ## Examples:

    ### Principal Creation:
    ```json
    {
        "email": "principal@vit.edu.in",
        "full_name": "Dr. Pradeep Kumar Sinha",
        "phone": "+91-9876543210",
        "role": "principal"
    }
    ```

    ### Department Head - Computer Science:
    ```json
    {
        "email": "hod.cse@nit.ac.in",
        "full_name": "Prof. (Dr.) Sunita Sharma",
        "phone": "+91-9876543210",
        "role": "head",
        "department_id": "dept-computer-science",
        "branch_id": "branch-cse",
        "degree_id": "degree-btech",
        "managed_departments": ["dept-computer-science"],
        "teaching_subjects": ["subject-software-engineering", "subject-dbms"]
    }
    ```

    ### Department Head - Medicine (Hindi Name):
    ```json
    {
        "email": "hod.medicine@aiims.edu.in",
        "full_name": "डॉ. प्रिया देवी शर्मा (Dr. Priya Devi Sharma)",
        "phone": "+91-9876543210",
        "role": "head",
        "department_id": "dept-general-medicine",
        "branch_id": "branch-medicine",
        "degree_id": "degree-mbbs",
        "managed_departments": ["dept-general-medicine"],
        "teaching_subjects": ["subject-pathology", "subject-internal-medicine"]
    }
    ```

    ### Multi-Department Teaching Staff:
    ```json
    {
        "email": "mathematics.prof@college.edu.in",
        "full_name": "Prof. Suresh Chandra Gupta",
        "phone": "+91-9876543210",
        "role": "staff",
        "department_id": "dept-mathematics",
        "branch_id": "branch-pure-mathematics",
        "degree_id": "degree-msc",
        "managed_departments": ["dept-mathematics", "dept-computer-science", "dept-physics"],
        "teaching_subjects": [
            "subject-calculus",
            "subject-discrete-mathematics",
            "subject-statistics",
            "subject-numerical-methods"
        ]
    }
    ```

    ### Guest Faculty (Industry Expert):
    ```json
    {
        "email": "guest.faculty@industry.com",
        "full_name": "CA Meera Patel (Chartered Accountant)",
        "phone": "+91-9876543210",
        "role": "staff",
        "department_id": "dept-commerce",
        "branch_id": "branch-accounting",
        "degree_id": "degree-bcom",
        "managed_departments": ["dept-commerce", "dept-management"],
        "teaching_subjects": [
            "subject-financial-accounting",
            "subject-cost-accounting",
            "subject-taxation",
            "subject-auditing"
        ]
    }
    ```
    """

    email: EmailStr = Field(..., description="User email address")
    password: Optional[str] = Field(
        None, description="User password (optional - temp generated if not provided)"
    )
    full_name: str = Field(
        ...,
        description="Full name with designation (supports Hindi/regional languages)",
    )
    phone: Optional[str] = Field(
        None, description="Phone number with country code (+91)"
    )
    role: CMSUserRole = Field(..., description="User role")
    department_id: Optional[UUID] = Field(None, description="Department UUID")
    branch_id: Optional[UUID] = Field(None, description="Branch UUID")
    degree_id: Optional[UUID] = Field(None, description="Degree UUID")
    managed_departments: Optional[List[str]] = Field(
        [], description="Additional department UUIDs for cross-department access"
    )
    teaching_subjects: Optional[List[str]] = Field(
        [], description="Subject UUIDs for teaching assignments"
    )


class HierarchicalUserResponse(BaseModel):
    """
    Hierarchical user response with Indian context

    ## Example Response:
    ```json
    {
        "id": "user-123e4567-e89b-12d3-a456-426614174000",
        "email": "hod.cse@nit.ac.in",
        "full_name": "Prof. (Dr.) Sunita Sharma",
        "role": "head",
        "department_id": "dept-computer-science",
        "department_name": "कंप्यूटर विज्ञान विभाग (Computer Science Department)",
        "branch_id": "branch-cse",
        "branch_name": "Computer Science & Engineering",
        "created_by": "user-principal-123",
        "created_by_name": "Dr. Pradeep Kumar Sinha (Principal)",
        "managed_departments": ["dept-computer-science"],
        "teaching_subjects": ["subject-software-engineering", "subject-dbms"],
        "is_active": true,
        "created_at": 1706764200,
        "last_login": 1706850600
    }
    ```
    """

    id: UUID
    email: str
    full_name: str
    role: str
    department_id: Optional[UUID]
    department_name: Optional[str] = Field(
        None, description="Department name (supports regional languages)"
    )
    branch_id: Optional[UUID]
    branch_name: Optional[str] = Field(None, description="Branch name")
    created_by: Optional[UUID]
    created_by_name: Optional[str] = Field(
        None, description="Creator's full name with designation"
    )
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
    """
    Authority transfer schema for Indian academic hierarchy

    ## Examples:

    ### Principal Retirement Transfer:
    ```json
    {
        "target_user_id": "admin-dr-sunita-sharma",
        "confirmation": true,
        "reason": "Principal retirement - authority transfer to Senior Administrator",
        "effective_date": "2024-07-01"
    }
    ```

    ### Emergency Authority Transfer:
    ```json
    {
        "target_user_id": "admin-prof-rajesh-kumar",
        "confirmation": true,
        "reason": "Medical leave - temporary authority transfer",
        "temporary": true,
        "duration_months": 6
    }
    ```

    ### Promotion-based Transfer:
    ```json
    {
        "target_user_id": "admin-dr-priya-singh",
        "confirmation": true,
        "reason": "Promotion to Principal position",
        "ceremony_date": "2024-08-15",
        "announcement": true
    }
    ```
    """

    target_user_id: UUID = Field(..., description="User to transfer authority to")
    confirmation: bool = Field(..., description="Confirmation of transfer")
    reason: Optional[str] = Field(None, description="Reason for authority transfer")
    effective_date: Optional[str] = Field(
        None, description="Effective date of transfer"
    )
    temporary: Optional[bool] = Field(
        False, description="Whether this is a temporary transfer"
    )
    duration_months: Optional[int] = Field(
        None, description="Duration in months for temporary transfers"
    )


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
    """
    Module permission granting for Indian academic system

    ## Examples:

    ### Grant Attendance Management Permission:
    ```json
    {
        "user_id": "staff-prof-anita-singh",
        "module_name": "attendance_management",
        "actions": ["read", "write"],
        "scope": "department",
        "constraints": {
            "sections": ["btech-cse-a", "btech-cse-b"],
            "subjects": ["subject-data-structures", "subject-algorithms"]
        },
        "valid_until": "2024-12-31"
    }
    ```

    ### Grant Examination Management Permission:
    ```json
    {
        "user_id": "staff-exam-controller",
        "module_name": "examination_management",
        "actions": ["read", "write", "delete", "schedule_exams", "publish_results"],
        "scope": "college",
        "constraints": {
            "exam_types": ["internal", "external", "practical"],
            "departments": ["dept-computer-science", "dept-electronics"]
        },
        "time_restrictions": {
            "exam_period_only": true,
            "working_hours": "09:00-18:00"
        }
    }
    ```

    ### Grant Hostel Management Permission:
    ```json
    {
        "user_id": "staff-warden-suresh-gupta",
        "module_name": "hostel_management",
        "actions": ["read", "write", "delete", "room_allocation"],
        "scope": "hostel",
        "constraints": {
            "hostels": ["boys-hostel-1", "boys-hostel-2"],
            "facilities": ["mess", "sports", "medical"]
        },
        "emergency_access": true
    }
    ```
    """

    user_id: UUID = Field(..., description="User to grant permission to")
    module_name: str = Field(..., description="Module name")
    actions: List[str] = Field(
        ..., description="Actions to grant (read, write, delete, etc.)"
    )
    scope: Optional[str] = Field(
        "department", description="Permission scope (department, college, hostel)"
    )
    constraints: Optional[dict] = Field(
        None, description="Additional constraints for the permission"
    )
    valid_until: Optional[str] = Field(None, description="Permission expiry date")
    time_restrictions: Optional[dict] = Field(
        None, description="Time-based access restrictions"
    )
    emergency_access: Optional[bool] = Field(False, description="Emergency access flag")


class ModulePermissionResponse(BaseModel):
    message: str
    user_id: UUID
    module: str
    actions: List[str]
    granted_by: UUID
    granted_at: int


# Hierarchy Tree
class HierarchyTreeNode(BaseModel):
    """
    Hierarchy tree node for Indian academic system

    ## Example Tree Structure:
    ```json
    {
        "id": "user-principal-123",
        "email": "principal@vit.edu.in",
        "full_name": "Dr. Pradeep Kumar Sinha (Principal)",
        "role": "principal",
        "level": 0,
        "department_name": null,
        "children": [
            {
                "id": "user-admin-456",
                "email": "admin@vit.edu.in",
                "full_name": "श्री अरविंद गुप्ता (Shri Arvind Gupta)",
                "role": "admin",
                "level": 1,
                "department_name": "Administration",
                "children": [
                    {
                        "id": "user-head-789",
                        "email": "hod.cse@vit.edu.in",
                        "full_name": "Prof. (Dr.) Sunita Sharma",
                        "role": "head",
                        "level": 2,
                        "department_name": "कंप्यूटर विज्ञान विभाग (Computer Science Department)",
                        "children": [
                            {
                                "id": "user-staff-101",
                                "email": "rajesh.kumar@vit.edu.in",
                                "full_name": "Mr. Rajesh Kumar Yadav",
                                "role": "staff",
                                "level": 3,
                                "department_name": "कंप्यूटर विज्ञान विभाग (Computer Science Department)",
                                "children": []
                            }
                        ]
                    }
                ]
            }
        ]
    }
    ```
    """

    id: UUID
    email: str
    full_name: str
    role: str
    level: int
    department_name: Optional[str] = Field(
        None, description="Department name (supports regional languages)"
    )
    phone: Optional[str] = Field(None, description="Phone number")
    last_login: Optional[int] = Field(None, description="Last login timestamp")
    children: List["HierarchyTreeNode"] = []

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
    module_permissions: List[ModulePermissionGrant] = Field(
        ..., description="Permissions to grant"
    )


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
    """
    User creation success response for Indian academic system

    ## Example Response:
    ```json
    {
        "id": "user-123e4567-e89b-12d3-a456-426614174000",
        "email": "hod.cse@nit.ac.in",
        "full_name": "Prof. (Dr.) Sunita Sharma",
        "role": "head",
        "department_name": "कंप्यूटर विज्ञान विभाग (Computer Science Department)",
        "created_by": "user-principal-123",
        "created_by_name": "Dr. Pradeep Kumar Sinha (Principal)",
        "temporary_password": "CSE@Temp123",
        "login_instructions": {
            "change_password_required": true,
            "first_login_setup": true,
            "contact_it_support": "+91-8000123456"
        },
        "message": "Department Head created successfully"
    }
    ```
    """

    id: UUID
    email: str
    full_name: Optional[str] = Field(None, description="Full name with designation")
    role: str
    department_name: Optional[str] = Field(
        None, description="Department name (supports regional languages)"
    )
    created_by: UUID
    created_by_name: Optional[str] = Field(
        None, description="Creator's full name with designation"
    )
    temporary_password: Optional[str]
    login_instructions: Optional[dict] = Field(
        None, description="Login setup instructions"
    )
    message: str

    model_config = ConfigDict(from_attributes=True)


# Fix forward reference
HierarchyTreeNode.model_rebuild()
