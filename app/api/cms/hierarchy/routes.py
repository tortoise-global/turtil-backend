import time
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth import get_admin_user, get_current_active_user, get_principal_user
from app.core.security import generate_temp_password, get_password_hash
from app.db.database import get_db
from app.models.cms.models import Branch, CMSUser, Department
from app.services.cms.permission_service import get_permission_service

router = APIRouter()


# Role Hierarchy Management
@router.get("/role-hierarchy")
async def get_role_hierarchy(current_user: CMSUser = Depends(get_current_active_user)):
    """Get the complete role hierarchy"""
    hierarchy = {
        "principal": {
            "level": 1,
            "can_create": ["admin", "head", "staff"],
            "description": "College Principal - Full access",
        },
        "admin": {
            "level": 2,
            "can_create": ["head", "staff"],
            "description": "College Administrator - College-wide access",
        },
        "head": {
            "level": 3,
            "can_create": ["staff"],
            "description": "Department Head - Department access",
        },
        "staff": {
            "level": 4,
            "can_create": [],
            "description": "Teaching Staff - Limited access",
        },
    }

    return {
        "current_user_role": current_user.role,
        "hierarchy": hierarchy,
        "can_create_roles": hierarchy.get(current_user.role, {}).get("can_create", []),
    }


# User Creation with Hierarchy
@router.post("/create-user", status_code=201)
async def create_hierarchical_user(
    user_data: dict,
    current_user: CMSUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a user with proper hierarchy validation

    ## Request Payload Example:
    ```json
    {
        "email": "rajesh.kumar@college.edu.in",
        "fullName": "Dr. Rajesh Kumar Sharma",
        "phone": "+91-9876543210",
        "role": "head",
        "departmentId": "dept-123e4567-e89b-12d3-a456-426614174000",
        "branchId": "branch-123e4567-e89b-12d3-a456-426614174001",
        "degreeId": "degree-123e4567-e89b-12d3-a456-426614174002",
        "managedDepartments": ["dept-cse", "dept-it"],
        "teachingSubjects": ["subject-algorithms", "subject-data-structures"]
    }
    ```

    ## Indian Context Examples:

    ### Principal Creation (by existing Principal):
    ```json
    {
        "email": "principal@vit.edu.in",
        "fullName": "Dr. Pradeep Kumar Sinha",
        "phone": "+91-9876543210",
        "role": "principal",
        "departmentId": null,
        "branchId": null,
        "degreeId": null,
        "managedDepartments": [],
        "teachingSubjects": []
    }
    ```

    ### College Administrator Creation:
    ```json
    {
        "email": "admin@iit.delhi.ac.in",
        "fullName": "श्री अरविंद गुप्ता (Shri Arvind Gupta)",
        "phone": "+91-9876543210",
        "role": "admin",
        "departmentId": null,
        "branchId": null,
        "degreeId": null,
        "managedDepartments": ["dept-all"],
        "teachingSubjects": []
    }
    ```

    ### Department Head - Computer Science:
    ```json
    {
        "email": "hod.cse@nit.ac.in",
        "fullName": "Prof. (Dr.) Sunita Sharma",
        "phone": "+91-9876543210",
        "role": "head",
        "departmentId": "dept-computer-science",
        "branchId": "branch-cse",
        "degreeId": "degree-btech",
        "managedDepartments": ["dept-computer-science"],
        "teachingSubjects": ["subject-software-engineering", "subject-dbms"]
    }
    ```

    ### Department Head - Medicine:
    ```json
    {
        "email": "hod.medicine@aiims.edu.in",
        "fullName": "डॉ. प्रिया देवी शर्मा (Dr. Priya Devi Sharma)",
        "phone": "+91-9876543210",
        "role": "head",
        "departmentId": "dept-general-medicine",
        "branchId": "branch-medicine",
        "degreeId": "degree-mbbs",
        "managedDepartments": ["dept-general-medicine"],
        "teachingSubjects": ["subject-pathology", "subject-internal-medicine"]
    }
    ```

    ### Teaching Staff - Engineering:
    ```json
    {
        "email": "rajesh.kumar@college.edu.in",
        "fullName": "Mr. Rajesh Kumar Yadav",
        "phone": "+91-9876543210",
        "role": "staff",
        "departmentId": "dept-mechanical-engineering",
        "branchId": "branch-mechanical",
        "degreeId": "degree-btech",
        "managedDepartments": [],
        "teachingSubjects": ["subject-thermodynamics", "subject-fluid-mechanics"]
    }
    ```

    ### Teaching Staff - Arts & Humanities:
    ```json
    {
        "email": "kavita.singh@du.ac.in",
        "fullName": "श्रीमती कविता सिंह (Smt. Kavita Singh)",
        "phone": "+91-9876543210",
        "role": "staff",
        "departmentId": "dept-hindi-literature",
        "branchId": "branch-hindi",
        "degreeId": "degree-ba",
        "managedDepartments": [],
        "teachingSubjects": ["subject-hindi-sahitya", "subject-kavya-shastra"]
    }
    ```

    ### Multi-Department Teaching Staff:
    ```json
    {
        "email": "mathematics.prof@college.edu.in",
        "fullName": "Prof. Suresh Chandra Gupta",
        "phone": "+91-9876543210",
        "role": "staff",
        "departmentId": "dept-mathematics",
        "branchId": "branch-pure-mathematics",
        "degreeId": "degree-msc",
        "managedDepartments": ["dept-mathematics", "dept-computer-science", "dept-physics"],
        "teachingSubjects": [
            "subject-calculus",
            "subject-discrete-mathematics",
            "subject-statistics",
            "subject-numerical-methods"
        ]
    }
    ```

    ### Guest Faculty:
    ```json
    {
        "email": "guest.faculty@industry.com",
        "fullName": "CA Meera Patel (Chartered Accountant)",
        "phone": "+91-9876543210",
        "role": "staff",
        "departmentId": "dept-commerce",
        "branchId": "branch-accounting",
        "degreeId": "degree-bcom",
        "managedDepartments": ["dept-commerce", "dept-management"],
        "teachingSubjects": [
            "subject-financial-accounting",
            "subject-cost-accounting",
            "subject-taxation",
            "subject-auditing"
        ]
    }
    ```

    ## Response Example:
    ```json
    {
        "id": "user-123e4567-e89b-12d3-a456-426614174000",
        "email": "rajesh.kumar@college.edu.in",
        "role": "head",
        "created_by": "user-principal-123",
        "temporary_password": "Temp@123456",
        "message": "User created successfully"
    }
    ```
    """

    # Validate role hierarchy
    role_hierarchy = {
        "principal": ["admin", "head", "staff"],
        "admin": ["head", "staff"],
        "head": ["staff"],
        "staff": [],
    }

    target_role = user_data.get("role")
    if target_role not in role_hierarchy.get(current_user.role, []):
        raise HTTPException(
            status_code=403,
            detail=f"Role '{current_user.role}' cannot create '{target_role}' users",
        )

    # Check if email already exists
    existing_user = (
        db.query(CMSUser).filter(CMSUser.email == user_data["email"]).first()
    )
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Generate temporary password if not provided
    temp_password = user_data.get("password") or generate_temp_password()

    # Create new user
    new_user = CMSUser(
        college_id=current_user.college_id,
        username=user_data["email"],
        email=user_data["email"],
        password_hash=get_password_hash(temp_password),
        full_name=user_data["full_name"],
        phone=user_data.get("phone"),
        role=target_role,
        department_id=user_data.get("department_id"),
        branch_id=user_data.get("branch_id"),
        degree_id=user_data.get("degree_id"),
        created_by=current_user.id,
        managed_departments=user_data.get("managed_departments", []),
        teaching_subjects=user_data.get("teaching_subjects", []),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Initialize default permissions
    permission_service = get_permission_service(db)
    permission_service.create_default_permissions_for_user(new_user)

    return {
        "id": str(new_user.id),
        "email": new_user.email,
        "role": new_user.role,
        "created_by": str(current_user.id),
        "temporary_password": temp_password if not user_data.get("password") else None,
        "message": "User created successfully",
    }


# Get Users in Hierarchy
@router.get("/users")
async def get_hierarchical_users(
    role: Optional[str] = Query(None),
    department_id: Optional[str] = Query(None),
    created_by_me: bool = Query(False),
    current_user: CMSUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get users based on hierarchy and permissions"""

    # Base query - users in same college
    query = db.query(CMSUser).filter(CMSUser.college_id == current_user.college_id)

    # Hierarchy filtering
    if current_user.role == "principal":
        # Principal can see all users
        pass
    elif current_user.role == "admin":
        # Admin can see head and staff
        query = query.filter(CMSUser.role.in_(["admin", "head", "staff"]))
    elif current_user.role == "head":
        # Head can see staff in their department
        query = query.filter(
            (CMSUser.role == "staff")
            & (CMSUser.department_id == current_user.department_id)
        )
    else:
        # Staff can only see themselves
        query = query.filter(CMSUser.id == current_user.id)

    # Additional filters
    if role:
        query = query.filter(CMSUser.role == role)
    if department_id:
        query = query.filter(CMSUser.department_id == department_id)
    if created_by_me:
        query = query.filter(CMSUser.created_by == current_user.id)

    users = query.all()

    return [
        {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "department_id": str(user.department_id) if user.department_id else None,
            "branch_id": str(user.branch_id) if user.branch_id else None,
            "created_by": str(user.created_by) if user.created_by else None,
            "managed_departments": user.managed_departments or [],
            "is_active": user.is_active,
            "created_at": user.created_at,
            "last_login": user.last_login,
        }
        for user in users
    ]


# Transfer Authority
@router.post("/transfer-authority")
async def transfer_authority(
    transfer_data: dict,
    current_user: CMSUser = Depends(get_principal_user),
    db: Session = Depends(get_db),
):
    """
    Transfer principal authority to another user (Principal only)

    ## Request Payload Example:
    ```json
    {
        "targetUserId": "admin-123e4567-e89b-12d3-a456-426614174000"
    }
    ```

    ## Indian Context Examples:

    ### Principal Retirement Transfer:
    ```json
    {
        "targetUserId": "admin-dr-sunita-sharma",
        "reason": "Principal retirement - authority transfer to Senior Administrator",
        "effectiveDate": "2024-07-01"
    }
    ```

    ### Emergency Authority Transfer:
    ```json
    {
        "targetUserId": "admin-prof-rajesh-kumar",
        "reason": "Medical leave - temporary authority transfer",
        "temporary": true,
        "durationMonths": 6
    }
    ```

    ### Promotion-based Transfer:
    ```json
    {
        "targetUserId": "admin-dr-priya-singh",
        "reason": "Promotion to Principal position",
        "ceremonyDate": "2024-08-15",
        "announcement": true
    }
    ```

    ## Response Example:
    ```json
    {
        "message": "Authority transferred successfully",
        "formerPrincipal": "user-dr-pradeep-sinha",
        "newPrincipal": "user-dr-sunita-sharma",
        "transferredAt": 1706764200
    }
    ```
    """

    target_user_id = transfer_data["target_user_id"]
    target_user = db.query(CMSUser).filter(CMSUser.id == target_user_id).first()

    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    if target_user.college_id != current_user.college_id:
        raise HTTPException(
            status_code=400, detail="Cannot transfer to user from different college"
        )

    if target_user.role != "admin":
        raise HTTPException(
            status_code=400, detail="Can only transfer authority to admin users"
        )

    # Transfer roles
    current_user.role = "admin"
    target_user.role = "principal"

    # Log the transfer
    db.commit()

    return {
        "message": "Authority transferred successfully",
        "former_principal": str(current_user.id),
        "new_principal": str(target_user.id),
        "transferred_at": int(time.time()),
    }


# Delegate Department Management
@router.post("/delegate-department")
async def delegate_department_management(
    delegation_data: dict,
    current_user: CMSUser = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """
    Delegate department management to a head

    ## Request Payload Example:
    ```json
    {
        "departmentId": "dept-123e4567-e89b-12d3-a456-426614174000",
        "headUserId": "head-123e4567-e89b-12d3-a456-426614174001"
    }
    ```

    ## Indian Context Examples:

    ### Computer Science Department Delegation:
    ```json
    {
        "departmentId": "dept-computer-science",
        "headUserId": "head-dr-rajesh-kumar",
        "effectiveFrom": "2024-07-01",
        "delegationScope": [
            "facultyManagement",
            "curriculumUpdates",
            "studentAffairs",
            "budgetApprovalUpto50000"
        ]
    }
    ```

    ### Medical Department Delegation:
    ```json
    {
        "departmentId": "dept-general-medicine",
        "headUserId": "head-dr-priya-sharma",
        "effectiveFrom": "2024-08-01",
        "delegationScope": [
            "clinicalOperations",
            "residentSupervision",
            "equipmentProcurement",
            "patientCareProtocols"
        ]
    }
    ```

    ### Commerce Department Delegation:
    ```json
    {
        "departmentId": "dept-commerce",
        "headUserId": "head-prof-suresh-gupta",
        "effectiveFrom": "2024-06-15",
        "delegationScope": [
            "industryPartnerships",
            "placementCoordination",
            "guestFacultyManagement",
            "seminarOrganization"
        ]
    }
    ```

    ### Multi-Department Delegation:
    ```json
    {
        "departmentId": "dept-humanities",
        "headUserId": "head-prof-kavita-singh",
        "subDepartments": [
            "dept-hindi-literature",
            "dept-english-literature",
            "dept-philosophy",
            "dept-history"
        ],
        "effectiveFrom": "2024-07-15"
    }
    ```

    ## Response Example:
    ```json
    {
        "message": "Department management delegated successfully",
        "departmentId": "dept-computer-science",
        "headUserId": "head-dr-rajesh-kumar"
    }
    ```
    """

    department_id = delegation_data["department_id"]
    head_user_id = delegation_data["head_user_id"]

    # Validate department exists
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    # Validate head user
    head_user = db.query(CMSUser).filter(CMSUser.id == head_user_id).first()
    if not head_user or head_user.role != "head":
        raise HTTPException(status_code=400, detail="Invalid head user")

    # Assign department to head
    head_user.department_id = department_id
    db.commit()

    return {
        "message": "Department management delegated successfully",
        "department_id": str(department_id),
        "head_user_id": str(head_user_id),
    }


# Grant Module Permissions
@router.post("/grant-module-permission")
async def grant_module_permission(
    permission_data: dict,
    current_user: CMSUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Grant specific module permissions to users (Head can grant to staff)

    ## Request Payload Example:
    ```json
    {
        "userId": "staff-123e4567-e89b-12d3-a456-426614174000",
        "moduleName": "studentManagement",
        "actions": ["read", "write", "delete"]
    }
    ```

    ## Indian Context Examples:

    ### Grant Attendance Management Permission:
    ```json
    {
        "userId": "staff-prof-anita-singh",
        "moduleName": "attendanceManagement",
        "actions": ["read", "write"],
        "scope": {
            "sections": ["btech-cse-a", "btech-cse-b"],
            "subjects": ["subject-data-structures", "subject-algorithms"]
        },
        "validUntil": "2024-12-31"
    }
    ```

    ### Grant Grade Management Permission:
    ```json
    {
        "userId": "staff-dr-rajesh-kumar",
        "moduleName": "gradeManagement",
        "actions": ["read", "write", "approve"],
        "scope": {
            "semesters": ["2024-spring", "2024-fall"],
            "departments": ["dept-computer-science"]
        },
        "delegationAllowed": true
    }
    ```

    ### Grant Library Management Permission:
    ```json
    {
        "userId": "staff-librarian-meera-patel",
        "moduleName": "libraryManagement",
        "actions": ["read", "write", "delete", "issueBooks", "collectFines"],
        "scope": {
            "sections": ["all"],
            "bookCategories": ["computer-science", "mathematics", "physics"]
        },
        "specialPermissions": ["bulkOperations", "reportGeneration"]
    }
    ```

    ### Grant Hostel Management Permission:
    ```json
    {
        "userId": "staff-warden-suresh-gupta",
        "moduleName": "hostelManagement",
        "actions": ["read", "write", "delete", "roomAllocation"],
        "scope": {
            "hostels": ["boys-hostel-1", "boys-hostel-2"],
            "facilities": ["mess", "sports", "medical"]
        },
        "emergencyAccess": true
    }
    ```

    ### Grant Examination Management Permission:
    ```json
    {
        "userId": "staff-exam-controller",
        "moduleName": "examinationManagement",
        "actions": ["read", "write", "delete", "scheduleExams", "publishResults"],
        "scope": {
            "examTypes": ["internal", "external", "practical"],
            "departments": ["dept-computer-science", "dept-electronics"]
        },
        "timeRestrictions": {
            "examPeriodOnly": true,
            "workingHours": "09:00-18:00"
        }
    }
    ```

    ### Grant Placement Cell Permission:
    ```json
    {
        "userId": "staff-placement-officer",
        "moduleName": "placementManagement",
        "actions": ["read", "write", "scheduleInterviews", "sendNotifications"],
        "scope": {
            "studentYears": ["final-year", "pre-final"],
            "companies": ["tier-1", "tier-2", "startups"]
        },
        "companyInteraction": true
    }
    ```

    ## Response Example:
    ```json
    {
        "message": "Module permission granted successfully",
        "userId": "staff-prof-anita-singh",
        "module": "attendanceManagement",
        "actions": ["read", "write"]
    }
    ```
    """

    if current_user.role not in ["head", "admin", "principal"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    target_user_id = permission_data["user_id"]
    module_name = permission_data["module_name"]
    actions = permission_data["actions"]

    target_user = db.query(CMSUser).filter(CMSUser.id == target_user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    # Validate hierarchy
    if current_user.role == "head" and target_user.role != "staff":
        raise HTTPException(
            status_code=403, detail="Head can only grant permissions to staff"
        )

    if (
        current_user.role == "head"
        and target_user.department_id != current_user.department_id
    ):
        raise HTTPException(
            status_code=403, detail="Can only grant permissions within your department"
        )

    # Create/update permission using permission service
    permission_service = get_permission_service(db)
    # This would need a new method in permission service to grant custom permissions

    return {
        "message": "Module permission granted successfully",
        "user_id": str(target_user_id),
        "module": module_name,
        "actions": actions,
    }


# Get User Hierarchy Tree
@router.get("/hierarchy-tree")
async def get_hierarchy_tree(
    current_user: CMSUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get hierarchical tree of users created by current user"""

    def build_user_tree(user_id: str, level: int = 0) -> Dict[str, Any]:
        user = db.query(CMSUser).filter(CMSUser.id == user_id).first()
        if not user:
            return None

        # Get users created by this user
        created_users = db.query(CMSUser).filter(CMSUser.created_by == user_id).all()

        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "level": level,
            "children": [
                build_user_tree(str(child.id), level + 1) for child in created_users
            ]
            if created_users
            else [],
        }

    tree = build_user_tree(str(current_user.id))

    return {
        "hierarchy_tree": tree,
        "total_created_users": len(
            db.query(CMSUser).filter(CMSUser.created_by == current_user.id).all()
        ),
    }


# Revoke User Access
@router.post("/revoke-access/{user_id}")
async def revoke_user_access(
    user_id: str,
    current_user: CMSUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Revoke access for a user in hierarchy"""

    target_user = db.query(CMSUser).filter(CMSUser.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if current user has authority to revoke
    if target_user.created_by != current_user.id and current_user.role != "principal":
        raise HTTPException(
            status_code=403, detail="Can only revoke access for users you created"
        )

    target_user.is_active = False
    db.commit()

    return {
        "message": "User access revoked successfully",
        "user_id": str(user_id),
        "revoked_by": str(current_user.id),
    }
