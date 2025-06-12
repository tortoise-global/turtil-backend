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
        "full_name": "Dr. Rajesh Kumar Sharma",
        "phone": "+91-9876543210",
        "role": "head",
        "department_id": "dept-123e4567-e89b-12d3-a456-426614174000",
        "branch_id": "branch-123e4567-e89b-12d3-a456-426614174001",
        "degree_id": "degree-123e4567-e89b-12d3-a456-426614174002",
        "managed_departments": ["dept-cse", "dept-it"],
        "teaching_subjects": ["subject-algorithms", "subject-data-structures"]
    }
    ```

    ## Indian Context Examples:

    ### Principal Creation (by existing Principal):
    ```json
    {
        "email": "principal@vit.edu.in",
        "full_name": "Dr. Pradeep Kumar Sinha",
        "phone": "+91-9876543210",
        "role": "principal",
        "department_id": null,
        "branch_id": null,
        "degree_id": null,
        "managed_departments": [],
        "teaching_subjects": []
    }
    ```

    ### College Administrator Creation:
    ```json
    {
        "email": "admin@iit.delhi.ac.in",
        "full_name": "श्री अरविंद गुप्ता (Shri Arvind Gupta)",
        "phone": "+91-9876543210",
        "role": "admin",
        "department_id": null,
        "branch_id": null,
        "degree_id": null,
        "managed_departments": ["dept-all"],
        "teaching_subjects": []
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

    ### Department Head - Medicine:
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

    ### Teaching Staff - Engineering:
    ```json
    {
        "email": "rajesh.kumar@college.edu.in",
        "full_name": "Mr. Rajesh Kumar Yadav",
        "phone": "+91-9876543210",
        "role": "staff",
        "department_id": "dept-mechanical-engineering",
        "branch_id": "branch-mechanical",
        "degree_id": "degree-btech",
        "managed_departments": [],
        "teaching_subjects": ["subject-thermodynamics", "subject-fluid-mechanics"]
    }
    ```

    ### Teaching Staff - Arts & Humanities:
    ```json
    {
        "email": "kavita.singh@du.ac.in",
        "full_name": "श्रीमती कविता सिंह (Smt. Kavita Singh)",
        "phone": "+91-9876543210",
        "role": "staff",
        "department_id": "dept-hindi-literature",
        "branch_id": "branch-hindi",
        "degree_id": "degree-ba",
        "managed_departments": [],
        "teaching_subjects": ["subject-hindi-sahitya", "subject-kavya-shastra"]
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

    ### Guest Faculty:
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
        "target_user_id": "admin-123e4567-e89b-12d3-a456-426614174000"
    }
    ```

    ## Indian Context Examples:

    ### Principal Retirement Transfer:
    ```json
    {
        "target_user_id": "admin-dr-sunita-sharma",
        "reason": "Principal retirement - authority transfer to Senior Administrator",
        "effective_date": "2024-07-01"
    }
    ```

    ### Emergency Authority Transfer:
    ```json
    {
        "target_user_id": "admin-prof-rajesh-kumar",
        "reason": "Medical leave - temporary authority transfer",
        "temporary": true,
        "duration_months": 6
    }
    ```

    ### Promotion-based Transfer:
    ```json
    {
        "target_user_id": "admin-dr-priya-singh",
        "reason": "Promotion to Principal position",
        "ceremony_date": "2024-08-15",
        "announcement": true
    }
    ```

    ## Response Example:
    ```json
    {
        "message": "Authority transferred successfully",
        "former_principal": "user-dr-pradeep-sinha",
        "new_principal": "user-dr-sunita-sharma",
        "transferred_at": 1706764200
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
        "department_id": "dept-123e4567-e89b-12d3-a456-426614174000",
        "head_user_id": "head-123e4567-e89b-12d3-a456-426614174001"
    }
    ```

    ## Indian Context Examples:

    ### Computer Science Department Delegation:
    ```json
    {
        "department_id": "dept-computer-science",
        "head_user_id": "head-dr-rajesh-kumar",
        "effective_from": "2024-07-01",
        "delegation_scope": [
            "faculty_management",
            "curriculum_updates",
            "student_affairs",
            "budget_approval_upto_50000"
        ]
    }
    ```

    ### Medical Department Delegation:
    ```json
    {
        "department_id": "dept-general-medicine",
        "head_user_id": "head-dr-priya-sharma",
        "effective_from": "2024-08-01",
        "delegation_scope": [
            "clinical_operations",
            "resident_supervision",
            "equipment_procurement",
            "patient_care_protocols"
        ]
    }
    ```

    ### Commerce Department Delegation:
    ```json
    {
        "department_id": "dept-commerce",
        "head_user_id": "head-prof-suresh-gupta",
        "effective_from": "2024-06-15",
        "delegation_scope": [
            "industry_partnerships",
            "placement_coordination",
            "guest_faculty_management",
            "seminar_organization"
        ]
    }
    ```

    ### Multi-Department Delegation:
    ```json
    {
        "department_id": "dept-humanities",
        "head_user_id": "head-prof-kavita-singh",
        "sub_departments": [
            "dept-hindi-literature",
            "dept-english-literature",
            "dept-philosophy",
            "dept-history"
        ],
        "effective_from": "2024-07-15"
    }
    ```

    ## Response Example:
    ```json
    {
        "message": "Department management delegated successfully",
        "department_id": "dept-computer-science",
        "head_user_id": "head-dr-rajesh-kumar"
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
        "user_id": "staff-123e4567-e89b-12d3-a456-426614174000",
        "module_name": "student_management",
        "actions": ["read", "write", "delete"]
    }
    ```

    ## Indian Context Examples:

    ### Grant Attendance Management Permission:
    ```json
    {
        "user_id": "staff-prof-anita-singh",
        "module_name": "attendance_management",
        "actions": ["read", "write"],
        "scope": {
            "sections": ["btech-cse-a", "btech-cse-b"],
            "subjects": ["subject-data-structures", "subject-algorithms"]
        },
        "valid_until": "2024-12-31"
    }
    ```

    ### Grant Grade Management Permission:
    ```json
    {
        "user_id": "staff-dr-rajesh-kumar",
        "module_name": "grade_management",
        "actions": ["read", "write", "approve"],
        "scope": {
            "semesters": ["2024-spring", "2024-fall"],
            "departments": ["dept-computer-science"]
        },
        "delegation_allowed": true
    }
    ```

    ### Grant Library Management Permission:
    ```json
    {
        "user_id": "staff-librarian-meera-patel",
        "module_name": "library_management",
        "actions": ["read", "write", "delete", "issue_books", "collect_fines"],
        "scope": {
            "sections": ["all"],
            "book_categories": ["computer-science", "mathematics", "physics"]
        },
        "special_permissions": ["bulk_operations", "report_generation"]
    }
    ```

    ### Grant Hostel Management Permission:
    ```json
    {
        "user_id": "staff-warden-suresh-gupta",
        "module_name": "hostel_management",
        "actions": ["read", "write", "delete", "room_allocation"],
        "scope": {
            "hostels": ["boys-hostel-1", "boys-hostel-2"],
            "facilities": ["mess", "sports", "medical"]
        },
        "emergency_access": true
    }
    ```

    ### Grant Examination Management Permission:
    ```json
    {
        "user_id": "staff-exam-controller",
        "module_name": "examination_management",
        "actions": ["read", "write", "delete", "schedule_exams", "publish_results"],
        "scope": {
            "exam_types": ["internal", "external", "practical"],
            "departments": ["dept-computer-science", "dept-electronics"]
        },
        "time_restrictions": {
            "exam_period_only": true,
            "working_hours": "09:00-18:00"
        }
    }
    ```

    ### Grant Placement Cell Permission:
    ```json
    {
        "user_id": "staff-placement-officer",
        "module_name": "placement_management",
        "actions": ["read", "write", "schedule_interviews", "send_notifications"],
        "scope": {
            "student_years": ["final-year", "pre-final"],
            "companies": ["tier-1", "tier-2", "startups"]
        },
        "company_interaction": true
    }
    ```

    ## Response Example:
    ```json
    {
        "message": "Module permission granted successfully",
        "user_id": "staff-prof-anita-singh",
        "module": "attendance_management",
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
