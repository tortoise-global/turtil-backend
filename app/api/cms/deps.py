"""
CMS Dependencies
Shared authentication and dependency injection functions for CMS modules
"""

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.staff import Staff
from app.core.cms_auth import cms_auth
from app.core.session_manager import SessionManager


# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


async def get_current_staff(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Staff:
    """
    Get current authenticated staff from JWT bearer token
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Use security manager for simple JWT validation
        from app.core.security import SecurityManager
        payload = SecurityManager.verify_token(credentials.credentials, "access")
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get staff ID from token
        staff_id = payload.get("sub")
        if not staff_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid token payload"
            )

        # Get staff from database
        result = await db.execute(select(Staff).where(Staff.staff_id == staff_id))
        staff = result.scalar_one_or_none()

        if not staff or not staff.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Staff not found or inactive",
            )

        return staff

    except HTTPException:
        raise
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Get current staff authentication", {"has_credentials": bool(credentials)}, status.HTTP_401_UNAUTHORIZED)


async def get_current_staff_from_temp_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Staff:
    """
    Get current CMS staff from temporary token (for registration flow)
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Decode token
        payload = cms_auth.decode_token(credentials.credentials)

        # Validate token type (temp tokens for registration or password reset)
        token_type = payload.get("type")
        if token_type not in ["temp", "registration", "password_reset"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid token type for registration"
            )

        # Get staff ID from token
        staff_id = payload.get("sub")
        if not staff_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid token payload"
            )

        # Get staff from database
        result = await db.execute(select(Staff).where(Staff.staff_id == staff_id))
        staff = result.scalar_one_or_none()

        if not staff:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Staff not found",
            )

        return staff

    except HTTPException:
        raise
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Get current staff from temp token", {"has_credentials": bool(credentials)}, status.HTTP_401_UNAUTHORIZED)


