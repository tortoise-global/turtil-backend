from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List
import logging

from app.core.auth_manager import auth_manager
from app.db.database import get_db
from app.models.cms.models import CMSUser

logger = logging.getLogger(__name__)
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> CMSUser:
    token = credentials.credentials
    
    # Verify token with Redis validation
    payload = auth_manager.verify_token(token)
    
    user_id = payload.get("sub")
    if user_id is None:
        logger.warning("Token missing user ID")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user with cache-first approach
    user = auth_manager.get_user_from_cache_or_db(user_id, db)
    if user is None:
        logger.warning(f"User not found: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(current_user: CMSUser = Depends(get_current_user)) -> CMSUser:
    if not current_user.is_active:
        logger.warning(f"Inactive user attempted access: {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Account deactivated"
        )
    return current_user


async def get_admin_user(current_user: CMSUser = Depends(get_current_active_user)) -> CMSUser:
    if current_user.role not in ["department_admin", "super_admin"]:
        logger.warning(f"Insufficient permissions for user: {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def get_super_admin_user(current_user: CMSUser = Depends(get_current_active_user)) -> CMSUser:
    if current_user.role != "super_admin":
        logger.warning(f"Super admin access denied for user: {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return current_user


async def get_lecturer_user(current_user: CMSUser = Depends(get_current_active_user)) -> CMSUser:
    if current_user.role not in ["lecturer", "department_admin", "super_admin"]:
        logger.warning(f"Lecturer access denied for user: {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Lecturer access required"
        )
    return current_user


def require_roles(allowed_roles: List[str]):
    async def role_checker(current_user: CMSUser = Depends(get_current_active_user)) -> CMSUser:
        if current_user.role not in allowed_roles:
            logger.warning(f"Role {current_user.role} not in allowed roles: {allowed_roles}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker


def require_college_access(current_user: CMSUser = Depends(get_current_active_user)):
    async def college_checker(college_id: str) -> CMSUser:
        if str(current_user.college_id) != college_id and current_user.role != "super_admin":
            logger.warning(f"College access denied for user {current_user.id} to college {college_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this college"
            )
        return current_user
    return college_checker