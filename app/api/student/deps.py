"""
Student API Dependencies
Authentication and authorization dependencies for student mobile app
"""

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.student import Student
from app.core.student_session_manager import student_session_manager
import logging
import time

logger = logging.getLogger(__name__)

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


async def get_current_student_session(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Dependency to get current student and session information from JWT token
    Used for protected student endpoints
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials"
        )
    
    try:
        # Decode JWT token to get session information
        from app.core.student_auth import student_auth
        payload = student_auth.validate_access_token(credentials.credentials)
        
        student_id = payload.get("sub")
        session_id = payload.get("session_id")
        
        if not student_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Get student information
        result = await db.execute(select(Student).where(Student.student_id == student_id))
        student = result.scalar_one_or_none()
        if not student:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Student not found"
            )
        
        # Check if student account is active
        if not student.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is not active"
            )
        
        # If session_id is present in token, validate session
        session_info = None
        if session_id:
            session_info = await student_session_manager.validate_student_session_token(
                session_id, credentials.credentials
            )
            if not session_info:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired session"
                )
        
        return {
            "student": student,
            "session_id": session_id,
            "session_info": session_info,
            "token_payload": payload
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Student session validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


async def get_current_student(
    current_session: dict = Depends(get_current_student_session)
) -> Student:
    """
    Dependency to get current student (simplified version)
    Returns only the Student object
    """
    return current_session["student"]


async def require_registration_completed(
    current_session: dict = Depends(get_current_student_session)
) -> dict:
    """
    Dependency that requires student to have completed academic registration
    Used for endpoints that need full registration
    """
    student = current_session["student"]
    
    if not student.registration_completed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Academic registration must be completed to access this feature"
        )
    
    if not student.can_access_app():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not eligible for app access"
        )
    
    return current_session


async def require_verified_student(
    current_session: dict = Depends(get_current_student_session)
) -> dict:
    """
    Dependency that requires student to be verified (email confirmed)
    Used for registration flow endpoints
    """
    student = current_session["student"]
    
    if not student.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    
    return current_session


async def check_registration_in_progress(
    current_session: dict = Depends(get_current_student_session)
) -> dict:
    """
    Dependency for registration endpoints - allows access during registration flow
    """
    student = current_session["student"]
    
    if not student.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required to start registration"
        )
    
    # Allow access if registration is in progress or completed
    return current_session


def get_client_ip(request) -> str:
    """Extract client IP address from request (same as CMS)"""
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        return x_real_ip.strip()
    return request.client.host if request.client else "unknown"


# Health check dependency for student app
async def check_student_system_health() -> dict:
    """Student-specific health check"""
    try:
        # Check Redis connection
        from app.redis_client import redis_client
        redis_healthy = await redis_client.ping()
        
        # Check database connection
        from app.database import check_db_health
        db_healthy = await check_db_health()
        
        return {
            "status": "healthy" if (redis_healthy and db_healthy) else "unhealthy",
            "redis": "healthy" if redis_healthy else "unhealthy",
            "database": "healthy" if db_healthy else "unhealthy",
            "student_api": "active",
            "timestamp": int(time.time())
        }
    except Exception as e:
        logger.error(f"Student health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": int(time.time())
        }