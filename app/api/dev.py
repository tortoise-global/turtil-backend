"""
Development API endpoints for testing and data cleanup.
Only available in development mode (debug=True).
"""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from pydantic import BaseModel
from app.core.utils import CamelCaseModel
import logging
from typing import Dict, Any

from app.config import settings
from app.database import get_db
from app.redis_client import redis_client
from app.models.staff import Staff
from app.models.student import Student
from app.models.college import College
from app.models.department import Department
from app.models.session import UserSession
from app.models.notification import Notification

# Only create router if in development mode
if not settings.debug:
    raise RuntimeError("Development API is only available in debug mode")

router = APIRouter(
    prefix="/dev",
    tags=["Development"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)


class CleanupAccountRequest(CamelCaseModel):
    email: str
    account_type: str = "auto"  # "auto", "staff", "student"


class CleanupAccountResponse(CamelCaseModel):
    success: bool
    message: str
    deleted_records: Dict[str, int]
    details: Dict[str, Any]


@router.delete("/cleanup-account", response_model=CleanupAccountResponse)
async def cleanup_account_data(
    request: CleanupAccountRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    🚨 DEVELOPMENT ONLY: Delete all data associated with an email account.
    
    For Staff accounts, this will delete:
    - Staff record for the email
    - College data (if staff is principal)
    - All other staff in the same college
    - All departments in the college
    - Redis cache entries
    
    For Student accounts, this will delete:
    - Student record for the email
    - Student registration data
    - Student sessions
    - Student notification history
    - Redis cache entries
    
    account_type: "auto" (detect), "staff" (force staff), "student" (force student)
    """
    
    if not settings.debug:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Development endpoints are only available in debug mode"
        )
    
    email = request.email.lower().strip()
    deleted_records = {
        "staff": 0,
        "students": 0,
        "colleges": 0,
        "departments": 0,
        "user_sessions": 0,
        "notifications": 0,
        "redis_keys": 0
    }
    
    details = {
        "target_email": email,
        "operations": []
    }
    
    try:
        # Begin transaction
        async with db.begin():
            logger.info(f"🧹 Starting cleanup for email: {email} (type: {request.account_type})")
            
            # 1. Determine account type and find the target record
            target_staff = None
            target_student = None
            
            if request.account_type in ["auto", "staff"]:
                staff_result = await db.execute(
                    select(Staff).where(Staff.email == email)
                )
                target_staff = staff_result.scalar_one_or_none()
            
            if request.account_type in ["auto", "student"]:
                student_result = await db.execute(
                    select(Student).where(Student.email == email)
                )
                target_student = student_result.scalar_one_or_none()
            
            # Handle case where no records are found
            if not target_staff and not target_student:
                details["operations"].append(f"No accounts found for email: {email}")
                return CleanupAccountResponse(
                    success=True,
                    message=f"No data found for email: {email}",
                    deleted_records=deleted_records,
                    details=details
                )
            
            # Clean up staff account if found
            if target_staff:
                await cleanup_staff_account(target_staff, db, deleted_records, details)
            
            # Clean up student account if found 
            if target_student:
                await cleanup_student_account(target_student, db, deleted_records, details)
            
            # 6. Clean up Redis cache entries
            staff_id = target_staff.staff_id if target_staff else None
            student_id = target_student.student_id if target_student else None
            redis_keys_deleted = await cleanup_redis_cache(email, staff_id, student_id)
            deleted_records["redis_keys"] = redis_keys_deleted
            
            if redis_keys_deleted > 0:
                details["operations"].append(f"Deleted {redis_keys_deleted} Redis cache entries")
        
        # Log successful cleanup
        total_deleted = sum(deleted_records.values())
        logger.info(f"✅ Cleanup completed for {email}. Total records deleted: {total_deleted}")
        
        return CleanupAccountResponse(
            success=True,
            message=f"Successfully cleaned up all data for {email}",
            deleted_records=deleted_records,
            details=details
        )
        
    except Exception as e:
        logger.error(f"❌ Cleanup failed for {email}: {str(e)}")
        # Transaction will be rolled back automatically
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Cleanup account data", {"email": email, "account_type": request.account_type}, status.HTTP_500_INTERNAL_SERVER_ERROR)


async def cleanup_staff_account(staff: Staff, db: AsyncSession, deleted_records: Dict[str, int], details: Dict[str, Any]):
    """Clean up all data associated with a staff account"""
    staff_id = staff.staff_id
    college_id = staff.college_id
    
    details["operations"].append(
        f"Found staff: {staff.full_name} (ID: {staff_id}, Role: {staff.cms_role})"
    )
    
    # 1. If staff has a college, clean up college-related data
    if college_id:
        # Get college info for logging
        college_result = await db.execute(
            select(College).where(College.college_id == college_id)
        )
        college = college_result.scalar_one_or_none()
        
        if college:
            details["operations"].append(
                f"Found college: {college.name} (ID: {college_id})"
            )
            
            # 1a. Delete all other staff in the college (except target staff)
            other_staff_result = await db.execute(
                select(Staff).where(
                    Staff.college_id == college_id,
                    Staff.staff_id != staff_id
                )
            )
            other_staff_list = other_staff_result.scalars().all()
            
            if other_staff_list:
                staff_names = [s.full_name for s in other_staff_list]
                details["operations"].append(
                    f"Deleting {len(other_staff_list)} other staff: {', '.join(staff_names)}"
                )
                
                # Delete other staff
                delete_other_staff = delete(Staff).where(
                    Staff.college_id == college_id,
                    Staff.staff_id != staff_id
                )
                result = await db.execute(delete_other_staff)
                deleted_records["staff"] += result.rowcount
            
            # 1b. Delete all departments in the college
            dept_result = await db.execute(
                select(Department).where(Department.college_id == college_id)
            )
            departments = dept_result.scalars().all()
            
            if departments:
                dept_names = [d.name for d in departments]
                details["operations"].append(
                    f"Deleting {len(departments)} departments: {', '.join(dept_names)}"
                )
                
                delete_departments = delete(Department).where(
                    Department.college_id == college_id
                )
                result = await db.execute(delete_departments)
                deleted_records["departments"] += result.rowcount
            
            # 1c. Delete all notifications sent by staff in this college
            notifications_result = await db.execute(
                select(Notification).where(Notification.college_id == college_id)
            )
            notifications = notifications_result.scalars().all()
            
            if notifications:
                details["operations"].append(
                    f"Deleting {len(notifications)} notifications from college"
                )
                delete_notifications = delete(Notification).where(
                    Notification.college_id == college_id
                )
                result = await db.execute(delete_notifications)
                deleted_records["notifications"] += result.rowcount
            
    # 2. Clean up foreign key references before deleting target staff
    
    # 2a. Delete all user sessions for the target staff
    user_sessions_result = await db.execute(
        select(UserSession).where(UserSession.staff_id == staff_id)
    )
    user_sessions = user_sessions_result.scalars().all()
    
    if user_sessions:
        details["operations"].append(
            f"Deleting {len(user_sessions)} user sessions for staff"
        )
        delete_user_sessions = delete(UserSession).where(UserSession.staff_id == staff_id)
        result = await db.execute(delete_user_sessions)
        deleted_records["user_sessions"] += result.rowcount
    
    # 2b. Update college to remove all staff references
    if college_id and college:
        college_updates = {}
        if college.contact_staff_id == staff_id:
            college_updates["contact_staff_id"] = None
            details["operations"].append(
                f"Removing staff reference from college contact_staff_id"
            )
        if college.principal_staff_id == staff_id:
            college_updates["principal_staff_id"] = None
            details["operations"].append(
                f"Removing staff reference from college principal_staff_id"
            )
        
        if college_updates:
            update_college = update(College).where(College.college_id == college_id).values(
                **college_updates
            )
            await db.execute(update_college)
    
    # 2c. Update any staff records that reference target staff as inviter
    invited_staff_result = await db.execute(
        select(Staff).where(Staff.invited_by_staff_id == staff_id)
    )
    invited_staff = invited_staff_result.scalars().all()
    
    if invited_staff:
        details["operations"].append(
            f"Removing inviter reference from {len(invited_staff)} staff records"
        )
        update_invited_staff = update(Staff).where(
            Staff.invited_by_staff_id == staff_id
        ).values(invited_by_staff_id=None)
        await db.execute(update_invited_staff)
    
    # 3. Now safely delete the target staff record (no more FK references)
    delete_target_staff = delete(Staff).where(Staff.staff_id == staff_id)
    result = await db.execute(delete_target_staff)
    deleted_records["staff"] += result.rowcount
    
    details["operations"].append(f"Deleted target staff: {staff.full_name}")
    
    # 4. Finally delete the college (no more foreign key references)
    if college_id and college:
        delete_college = delete(College).where(College.college_id == college_id)
        result = await db.execute(delete_college)
        deleted_records["colleges"] += result.rowcount
        
        details["operations"].append(f"Deleted college: {college.name}")


async def cleanup_student_account(student: Student, db: AsyncSession, deleted_records: Dict[str, int], details: Dict[str, Any]):
    """Clean up all data associated with a student account"""
    student_id = student.student_id
    
    details["operations"].append(
        f"Found student: {student.full_name} (ID: {student_id}, Email: {student.email})"
    )
    
    # 1. Remove student from notification targets
    from sqlalchemy import func
    notifications_targeting_student = await db.execute(
        select(Notification).where(
            func.json_array_length(Notification.target_student_ids) > 0
        )
    )
    notifications = notifications_targeting_student.scalars().all()
    
    if notifications:
        details["operations"].append(
            f"Updating {len(notifications)} notifications to remove student from targets"
        )
        for notification in notifications:
            # Remove student from target lists
            if notification.target_student_ids:
                notification.target_student_ids = [
                    sid for sid in notification.target_student_ids if sid != str(student_id)
                ]
            if notification.successful_student_ids:
                notification.successful_student_ids = [
                    sid for sid in notification.successful_student_ids if sid != str(student_id)
                ]
            if notification.failed_student_ids:
                notification.failed_student_ids = [
                    sid for sid in notification.failed_student_ids if sid != str(student_id)
                ]
        await db.commit()
    
    # 2. Delete student user sessions first (to avoid foreign key constraint)
    student_sessions_result = await db.execute(
        select(UserSession).where(UserSession.student_id == student_id)
    )
    student_sessions = student_sessions_result.scalars().all()
    
    if student_sessions:
        details["operations"].append(
            f"Deleting {len(student_sessions)} user sessions for student"
        )
        delete_student_sessions = delete(UserSession).where(UserSession.student_id == student_id)
        result = await db.execute(delete_student_sessions)
        deleted_records["user_sessions"] += result.rowcount
    
    # 3. Delete the student record
    delete_student = delete(Student).where(Student.student_id == student_id)
    result = await db.execute(delete_student)
    deleted_records["students"] += result.rowcount
    
    details["operations"].append(f"Deleted student: {student.full_name}")


async def cleanup_redis_cache(email: str, staff_id: str = None, student_id: str = None) -> int:
    """Clean up Redis cache entries for the given email and staff ID"""
    try:
        keys_deleted = 0
        
        # Common Redis key patterns for the email
        patterns = [
            f"otp:{email}",
            f"otp:{email}:*",
            f"cms_otp:{email}",
            f"cms_otp:{email}:*",
            f"session:{email}",
            f"session:{email}:*",
            f"user_session:{email}",
            f"user_session:{email}:*",
        ]
        
        # Add staff-specific session patterns if staff_id is provided
        if staff_id:
            patterns.extend([
                f"session:*:{staff_id}",
                f"user_sessions:{staff_id}",
                f"user_sessions:{staff_id}:*",
                f"blacklist:*:{staff_id}",
                f"blacklist:*:{staff_id}:*",
            ])
        
        # Add student-specific session patterns if student_id is provided
        if student_id:
            patterns.extend([
                f"student_session:*:{student_id}",
                f"student_sessions:{student_id}",
                f"student_sessions:{student_id}:*",
                f"student_blacklist:*:{student_id}",
                f"student_blacklist:*:{student_id}:*",
            ])
        
        for pattern in patterns:
            # Get keys matching pattern
            if "*" in pattern:
                keys = await redis_client.scan_keys(pattern)
            else:
                # Check if single key exists
                exists = await redis_client.exists(pattern)
                keys = [pattern] if exists else []
            
            # Delete found keys
            if keys:
                deleted = await redis_client.delete_keys(keys)
                keys_deleted += deleted
                logger.info(f"Deleted {deleted} Redis keys matching pattern: {pattern}")
        
        return keys_deleted
        
    except Exception as e:
        logger.error(f"Redis cleanup failed for {email}: {str(e)}")
        return 0


@router.get("/info")
async def dev_info():
    """Information about development endpoints"""
    
    if not settings.debug:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Development endpoints are only available in debug mode"
        )
    
    return {
        "message": "Development API endpoints",
        "environment": settings.environment,
        "debug_mode": settings.debug,
        "available_endpoints": {
            "cleanup_account": {
                "method": "DELETE",
                "path": "/api/dev/cleanup-account", 
                "description": "Delete all data associated with an email account (staff or student)",
                "parameters": {
                    "email": "Email address of account to delete",
                    "account_type": "auto (detect), staff (force staff), student (force student)"
                },
                "warning": "⚠️ This action is irreversible and will delete all college data if user is principal"
            }
        },
        "warning": "🚨 These endpoints are for development only and will delete data permanently"
    }