"""
Student Profile API
Profile management for students
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.student.deps import get_current_student_session
from app.schemas.student_auth_schemas import (
    StudentProfileResponse,
    StudentUpdateProfileRequest
)
import logging

router = APIRouter(prefix="/profile", tags=["Student Profile"])
logger = logging.getLogger(__name__)


@router.get("/me", response_model=StudentProfileResponse)
async def get_student_profile(
    current_session: dict = Depends(get_current_student_session)
):
    """Get current student profile"""
    try:
        student = current_session["student"]
        
        return StudentProfileResponse(
            studentId=str(student.student_id),
            email=student.email,
            fullName=student.full_name,
            isActive=student.is_active,
            isVerified=student.is_verified,
            registrationCompleted=student.registration_completed,
            collegeId=str(student.college_id) if student.college_id else None,
            sectionId=str(student.section_id) if student.section_id else None,
            admissionNumber=student.admission_number,
            rollNumber=student.roll_number,
            lastLoginAt=student.last_login_at,
            loginCount=student.login_count,
            createdAt=student.created_at
        )
        
    except Exception as e:
        logger.error(f"Get student profile error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get profile"
        )


@router.put("/update", response_model=StudentProfileResponse)
async def update_student_profile(
    request: StudentUpdateProfileRequest,
    current_session: dict = Depends(get_current_student_session),
    db: AsyncSession = Depends(get_db)
):
    """Update student profile"""
    try:
        student = current_session["student"]
        
        # Update fields if provided
        if request.fullName:
            student.full_name = request.fullName
        
        await db.commit()
        
        logger.info(f"Student profile updated for {student.student_id}")
        
        return StudentProfileResponse(
            studentId=str(student.student_id),
            email=student.email,
            fullName=student.full_name,
            isActive=student.is_active,
            isVerified=student.is_verified,
            registrationCompleted=student.registration_completed,
            collegeId=str(student.college_id) if student.college_id else None,
            sectionId=str(student.section_id) if student.section_id else None,
            admissionNumber=student.admission_number,
            rollNumber=student.roll_number,
            lastLoginAt=student.last_login_at,
            loginCount=student.login_count,
            createdAt=student.created_at
        )
        
    except Exception as e:
        logger.error(f"Update student profile error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )