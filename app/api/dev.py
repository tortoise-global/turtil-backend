"""
Development API endpoints for testing and data cleanup.
Only available in development mode (debug=True).
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from pydantic import BaseModel
import logging
from typing import Dict, Any

from app.config import settings
from app.database import get_db
from app.redis_client import redis_client
from app.models.staff import Staff
from app.models.college import College
from app.models.department import Department
from app.models.session import UserSession

# Only create router if in development mode
if not settings.debug:
    raise RuntimeError("Development API is only available in debug mode")

router = APIRouter(
    prefix="/dev",
    tags=["Development"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)


class CleanupAccountRequest(BaseModel):
    email: str


class CleanupAccountResponse(BaseModel):
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
    
    This endpoint will delete:
    - Staff record for the email
    - College data (if staff is principal)
    - All other staff in the same college
    - All departments in the college
    - Redis cache entries
    """
    
    if not settings.debug:
        raise HTTPException(
            status_code=403, 
            detail="Development endpoints are only available in debug mode"
        )
    
    email = request.email.lower().strip()
    deleted_records = {
        "staff": 0,
        "colleges": 0,
        "departments": 0,
        "user_sessions": 0,
        "redis_keys": 0
    }
    
    details = {
        "target_email": email,
        "operations": []
    }
    
    try:
        # Begin transaction
        async with db.begin():
            logger.info(f"🧹 Starting cleanup for email: {email}")
            
            # 1. Find the target staff record
            result = await db.execute(
                select(Staff).where(Staff.email == email)
            )
            target_staff = result.scalar_one_or_none()
            
            if not target_staff:
                details["operations"].append(f"No staff found for email: {email}")
                return CleanupAccountResponse(
                    success=True,
                    message=f"No data found for email: {email}",
                    deleted_records=deleted_records,
                    details=details
                )
            
            college_id = target_staff.college_id
            staff_id = target_staff.id
            cms_role = target_staff.cms_role
            
            details["operations"].append(
                f"Found staff: {target_staff.full_name} (ID: {staff_id}, Role: {cms_role})"
            )
            
            # 2. If staff has a college, clean up college-related data
            if college_id:
                # Get college info for logging
                college_result = await db.execute(
                    select(College).where(College.id == college_id)
                )
                college = college_result.scalar_one_or_none()
                
                if college:
                    details["operations"].append(
                        f"Found college: {college.name} (ID: {college_id})"
                    )
                    
                    # 2a. Delete all other staff in the college (except target staff)
                    other_staff_result = await db.execute(
                        select(Staff).where(
                            Staff.college_id == college_id,
                            Staff.id != staff_id
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
                            Staff.id != staff_id
                        )
                        result = await db.execute(delete_other_staff)
                        deleted_records["staff"] += result.rowcount
                    
                    # 2b. Delete all departments in the college
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
                    
            # 3. Clean up foreign key references before deleting target staff
            
            # 3a. Delete all user sessions for the target staff
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
            
            # 3b. Update college to remove staff reference (if this staff is contact)
            if college_id and college:
                if college.contact_staff_id == staff_id:
                    details["operations"].append(
                        f"Removing staff reference from college contact_staff_id"
                    )
                    update_college = update(College).where(College.id == college_id).values(
                        contact_staff_id=None
                    )
                    await db.execute(update_college)
            
            # 3c. Update any staff records that reference target staff as inviter
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
            
            # 4. Now safely delete the target staff record (no more FK references)
            delete_target_staff = delete(Staff).where(Staff.id == staff_id)
            result = await db.execute(delete_target_staff)
            deleted_records["staff"] += result.rowcount
            
            details["operations"].append(f"Deleted target staff: {target_staff.full_name}")
            
            # 5. Finally delete the college (no more foreign key references)
            if college_id and college:
                delete_college = delete(College).where(College.id == college_id)
                result = await db.execute(delete_college)
                deleted_records["colleges"] += result.rowcount
                
                details["operations"].append(f"Deleted college: {college.name}")
            
            # 6. Clean up Redis cache entries
            redis_keys_deleted = await cleanup_redis_cache(email, staff_id)
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
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cleanup account data: {str(e)}"
        )


async def cleanup_redis_cache(email: str, staff_id: int = None) -> int:
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
            status_code=403,
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
                "description": "Delete all data associated with an email account",
                "warning": "⚠️ This action is irreversible and will delete all college data if user is principal"
            }
        },
        "warning": "🚨 These endpoints are for development only and will delete data permanently"
    }