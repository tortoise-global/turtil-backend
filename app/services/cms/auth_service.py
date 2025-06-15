"""Authentication and user management service.

This module provides business logic for authentication operations including:
- User authentication and authorization
- Password management
- Profile completion
- Admin user management
"""

import logging
import time
from typing import Dict, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth_manager import auth_manager
from app.core.security import (
    generate_user_id,
    get_password_hash,
    send_email_otp,
    verify_otp,
    verify_password,
)
from app.models.cms.models import CMSUser
from app.schemas.cms.auth import (
    CompleteProfileRequest,
    CompleteSignupRequest,
    LoginRequest,
    SendSignupOTPRequest,
    VerifySignupOTPRequest,
)
from app.schemas.cms.users import CMSUserCreate, CMSUserUpdate
from app.services.base import BaseService


class AuthService(BaseService):
    """Authentication service with business logic."""

    def __init__(self):
        super().__init__(CMSUser)
        self.logger = logging.getLogger(__name__)

    def send_signup_otp(
        self, db: Session, request: SendSignupOTPRequest
    ) -> Dict[str, any]:
        """Send OTP for new user signup.

        Args:
            db: Database session
            request: Signup OTP request

        Returns:
            Success response

        Raises:
            HTTPException: If email already exists
        """
        # Check if user already exists
        existing_user = db.query(CMSUser).filter(CMSUser.email == request.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Send OTP for signup
        try:
            otp = send_email_otp(request.email)
            self.logger.info("Signup OTP sent to %s", request.email)
            return {
                "message": "OTP sent successfully to your email address",
                "success": True,
            }
        except Exception as e:
            self.logger.error(
                "Failed to send signup OTP to %s: %s", request.email, str(e)
            )
            raise HTTPException(
                status_code=500, detail="Failed to send OTP. Please try again."
            )

    def verify_signup_otp(self, request: VerifySignupOTPRequest) -> Dict[str, any]:
        """Verify signup OTP.

        Args:
            request: OTP verification request

        Returns:
            Success response

        Raises:
            HTTPException: If OTP is invalid
        """
        if not verify_otp(request.email, str(request.otp), consume=False):
            raise HTTPException(status_code=400, detail="Invalid or expired OTP")

        return {
            "message": "OTP verified successfully. You can now set your password.",
            "success": True,
            "verified": True,
        }

    def complete_signup(
        self, db: Session, request: CompleteSignupRequest
    ) -> Dict[str, any]:
        """Complete user signup by creating account.

        Args:
            db: Database session
            request: Signup completion request

        Returns:
            User creation response

        Raises:
            HTTPException: If OTP invalid or email exists
        """
        # Verify OTP one final time
        if not verify_otp(request.email, str(request.otp)):
            raise HTTPException(status_code=400, detail="Invalid or expired OTP")

        # Check if user was created in the meantime
        existing_user = db.query(CMSUser).filter(CMSUser.email == request.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Create minimal user record
        user_id = generate_user_id()
        db_user = CMSUser(
            id=user_id,
            email=request.email,
            password_hash=get_password_hash(request.password),
            email_verified=True,
            profile_completed=False,
        )

        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        self.logger.info("User signup completed: %s", request.email)
        return {
            "message": "Signup completed successfully. Please login to complete your profile.",
            "success": True,
            "user_id": str(user_id),
        }

    def authenticate_user(
        self, db: Session, credentials: LoginRequest
    ) -> Optional[CMSUser]:
        """Authenticate user credentials.

        Args:
            db: Database session
            credentials: Login credentials

        Returns:
            User instance if authenticated, None otherwise
        """
        user = auth_manager.authenticate_user(
            credentials.userName, credentials.password, db
        )

        if user:
            self.logger.info("User authenticated: %s", user.username)
        else:
            self.logger.warning("Authentication failed for: %s", credentials.userName)

        return user

    def create_user_token(self, user: CMSUser) -> Dict[str, any]:
        """Create access token for authenticated user.

        Args:
            user: Authenticated user

        Returns:
            Token response data
        """
        user_data = {
            "user_id": str(user.id),
            "email": user.email,
            "role": user.role,
            "college_id": str(user.college_id),
            "username": user.username,
        }

        token_response = auth_manager.create_access_token(user_data)

        return {
            "access_token": token_response["access_token"],
            "token_type": token_response["token_type"],
            "cms_user_id": str(user.id),
            "role": user.role,
            "profile_completed": user.profile_completed or False,
        }

    def change_password(
        self, db: Session, user_email: str, old_password: str, new_password: str
    ) -> Dict[str, str]:
        """Change user password.

        Args:
            db: Database session
            user_email: User email
            old_password: Current password
            new_password: New password

        Returns:
            Success message

        Raises:
            HTTPException: If user not found or password invalid
        """
        user = db.query(CMSUser).filter(CMSUser.email == user_email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not verify_password(old_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Invalid current password")

        user.hashed_password = get_password_hash(new_password)
        db.commit()

        self.logger.info("Password changed for user: %s", user_email)
        return {"message": "Password changed successfully"}

    def complete_profile(
        self, db: Session, user_id: str, profile_data: CompleteProfileRequest
    ) -> Dict[str, any]:
        """Complete user profile after signup.

        Args:
            db: Database session
            user_id: User ID
            profile_data: Profile completion data

        Returns:
            Success response

        Raises:
            HTTPException: If user not found or profile already completed
        """
        user = db.query(CMSUser).filter(CMSUser.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.profile_completed:
            raise HTTPException(status_code=400, detail="Profile already completed")

        # Update user profile
        user.full_name = profile_data.full_name
        user.phone = profile_data.phone
        user.college_id = profile_data.college_id
        user.role = profile_data.role
        user.department_id = profile_data.department_id
        user.branch_id = profile_data.branch_id
        user.degree_id = profile_data.degree_id
        user.username = user.email  # Set username to email
        user.profile_completed = True

        db.commit()
        db.refresh(user)

        self.logger.info("Profile completed for user: %s", user.email)
        return {"message": "Profile completed successfully", "profile_completed": True}

    def revoke_admin_access(
        self, db: Session, admin_id: str, reason: str, current_user_id: str
    ) -> Dict[str, any]:
        """Revoke admin user access.

        Args:
            db: Database session
            admin_id: Admin user ID
            reason: Revocation reason
            current_user_id: Current user ID

        Returns:
            Action response

        Raises:
            HTTPException: If admin not found or operation fails
        """
        admin_user = db.query(CMSUser).filter(CMSUser.id == admin_id).first()
        if not admin_user:
            raise HTTPException(status_code=404, detail="Admin user not found")

        if admin_user.role not in ["admin", "head", "staff"]:
            raise HTTPException(
                status_code=400, detail="Can only revoke admin/head/staff access"
            )

        # Immediately revoke access using Redis blacklist
        success = auth_manager.revoke_user_access(admin_id, reason)
        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to revoke access - Redis unavailable"
            )

        # Deactivate user in database
        admin_user.is_active = False
        db.commit()

        self.logger.info("Admin access revoked: %s by %s", admin_id, current_user_id)
        return {
            "message": "Admin access revoked immediately",
            "user_id": admin_id,
            "revoked_at": int(time.time()),
            "reason": reason,
        }

    def restore_admin_access(
        self, db: Session, admin_id: str, current_user_id: str
    ) -> Dict[str, any]:
        """Restore admin user access.

        Args:
            db: Database session
            admin_id: Admin user ID
            current_user_id: Current user ID

        Returns:
            Action response

        Raises:
            HTTPException: If admin not found or operation fails
        """
        admin_user = db.query(CMSUser).filter(CMSUser.id == admin_id).first()
        if not admin_user:
            raise HTTPException(status_code=404, detail="Admin user not found")

        # Restore access using Redis
        success = auth_manager.restore_user_access(admin_id)
        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to restore access - Redis unavailable"
            )

        # Reactivate user in database
        admin_user.is_active = True
        db.commit()

        self.logger.info("Admin access restored: %s by %s", admin_id, current_user_id)
        return {
            "message": "Admin access restored",
            "user_id": admin_id,
            "restored_at": int(time.time()),
        }

    def get_auth_status(self, user: CMSUser) -> Dict[str, any]:
        """Get authentication status for user.

        Args:
            user: Current user

        Returns:
            Authentication status
        """
        auth_status = auth_manager.get_authentication_status(str(user.id))

        return {
            "user_id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "college_id": str(user.college_id),
            "is_active": user.is_active,
            "last_login": user.last_login,
            "token_valid": True,
        }

    def logout_user(self, user: CMSUser) -> Dict[str, any]:
        """Logout user and invalidate cache.

        Args:
            user: Current user

        Returns:
            Logout response
        """
        auth_manager.redis.invalidate_user_cache(str(user.id))
        self.logger.info("User logged out: %s", user.username)

        return {"message": "Logged out successfully", "user_id": str(user.id)}

    def get_cache_stats(self) -> Dict[str, any]:
        """Get cache statistics.

        Returns:
            Cache statistics
        """
        cache_stats = auth_manager.redis.get_cache_stats()

        return {
            "cache_available": auth_manager.redis.is_available(),
            "total_keys": cache_stats.get("total_keys"),
            "memory_usage": cache_stats.get("memory_usage"),
            "hit_rate": cache_stats.get("hit_rate"),
        }


# Create service instance
auth_service = AuthService()
