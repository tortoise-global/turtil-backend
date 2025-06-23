"""
Simplified Signup API
Account creation with OTP verification and profile setup
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.database import get_db
from app.models.staff import Staff
from app.models.college import College
from app.core.cms_auth import cms_auth
from app.core.cms_otp import CMSOTPManager
from app.config import settings
from app.core.aws import EmailService
from app.schemas.signup_schemas import (
    SignupRequest,
    SignupResponse,
    VerifyOTPRequest,
    VerifySignupResponse,
    SetupProfileRequest,
    ResetPasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
)
import logging

router = APIRouter(prefix="/auth/signup", tags=["Signup"])
logger = logging.getLogger(__name__)


@router.post("/", response_model=SignupResponse)
async def send_signup_otp(
    request: SignupRequest, 
    db: AsyncSession = Depends(get_db)
):
    """
    Step 1: Send OTP for account creation
    - Check if user already exists
    - Generate and send OTP via email
    """
    try:
        email = request.email.lower().strip()

        # Check if staff already exists and is verified
        result = await db.execute(select(Staff).where(Staff.email == email))
        existing_staff = result.scalar_one_or_none()
        
        if existing_staff and existing_staff.is_verified and existing_staff.hashed_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account already exists. Please use sign in instead."
            )

        # Generate OTP
        otp = CMSOTPManager.generate_otp()
        
        # Store OTP in Redis
        otp_stored = await CMSOTPManager.store_otp(email, otp)
        
        if not otp_stored:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate OTP. Please try again."
            )

        # Send OTP via email
        email_result = await EmailService.send_otp_email(email, otp)
        email_sent = email_result.get("success", False)
        
        if not email_sent:
            # Clear OTP if email failed
            await CMSOTPManager.clear_otp(email)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send OTP email. Please try again."
            )

        # Development mode: Log OTP for easier testing
        if settings.is_development:
            logger.info(f"🔑 [DEV MODE] Signup OTP for {email}: {otp}")

        logger.info(f"Signup OTP sent to {email}")
        
        return SignupResponse(
            success=True,
            message="OTP sent successfully. Please check your email to continue registration.",
            attemptsRemaining=3
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup error for {request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


@router.post("/verify-otp", response_model=VerifySignupResponse)
async def verify_signup_otp(
    request: VerifyOTPRequest, 
    db: AsyncSession = Depends(get_db)
):
    """
    Step 2: Verify OTP and create temporary staff record
    - Verify OTP with attempt tracking
    - Create or update staff record
    - Return next step instructions
    """
    try:
        email = request.email.lower().strip()
        otp = request.otp.strip()

        # Verify OTP
        verification_result = await CMSOTPManager.verify_otp(email, otp)
        
        if verification_result["expired"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired. Please request a new one."
            )
        
        if verification_result["exceeded"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Maximum OTP attempts exceeded. Please request a new OTP."
            )
        
        if not verification_result["valid"]:
            attempts_remaining = 3 - verification_result["attempts"]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid OTP. {attempts_remaining} attempts remaining."
            )

        # Check if staff already exists
        result = await db.execute(select(Staff).where(Staff.email == email))
        existing_staff = result.scalar_one_or_none()
        
        if existing_staff and existing_staff.is_verified and existing_staff.hashed_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account already exists. Please use sign in instead."
            )

        # Create new staff record if doesn't exist
        if not existing_staff:
            staff = Staff(
                email=email,
                full_name="",  # Will be filled in next step
                hashed_password="",  # Will be filled in next step
                is_verified=True,  # Email is verified via OTP
                invitation_status="pending",
            )
            db.add(staff)
            await db.commit()
            await db.refresh(staff)
        else:
            # Update existing unverified staff
            staff = existing_staff
            staff.is_verified = True
            staff.email_verified_at = datetime.now(timezone.utc)
            await db.commit()

        # Mark OTP as verified in Redis
        await CMSOTPManager.mark_otp_verified(email)

        logger.info(f"OTP verified for {email}, staff record created/updated")

        return VerifySignupResponse(
            success=True,
            message="Email verified successfully. Please set up your profile to continue.",
            nextStep="profile_setup",
            tempToken=email  # Simple temp token for profile setup
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OTP verification error for {request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


@router.post("/setup-profile", response_model=SignupResponse)
async def setup_profile(
    request: SetupProfileRequest, 
    db: AsyncSession = Depends(get_db)
):
    """
    Step 3: Complete profile setup with password and personal details
    - Verify OTP was verified for this email
    - Set password and full name
    - Create college record for principal role
    - Complete signup process
    """
    try:
        email = request.email.lower().strip()
        password = request.password.strip()

        # Get staff from database
        result = await db.execute(select(Staff).where(Staff.email == email))
        staff = result.scalar_one_or_none()
        
        if not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found. Please complete email verification first."
            )

        # Verify OTP was verified for this email (check Redis)
        otp_status = await CMSOTPManager.get_otp_status(email)
        if not otp_status["verified"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not verified. Please verify your email with OTP first."
            )

        # Hash password
        hashed_password = cms_auth.get_password_hash(password)

        # Update staff with password and profile
        staff.hashed_password = hashed_password
        staff.full_name = request.full_name
        staff.temporary_password = False
        staff.must_reset_password = False
        
        # For Principal role, also create college and update contact information
        if not staff.college_id:
            # Create college for new principal
            college = College(
                name="",  # Will be filled in college-details step
                short_name="",  # Will be filled in college-details step
                college_reference_id="",  # Will be filled in college-details step
                area="",  # Will be filled in college-address step
                city="",  # Will be filled in college-address step
                district="",  # Will be filled in college-address step
                state="",  # Will be filled in college-address step
                pincode="000000",  # Will be filled in college-address step
                principal_cms_staff_id=staff.id,
                contact_number=request.contact_number,
                contact_staff_id=staff.id,
            )
            db.add(college)
            await db.commit()
            await db.refresh(college)
            
            # Update staff with college and role
            staff.college_id = college.id
            staff.cms_role = "principal"
            staff.can_assign_department = True
        else:
            # Update existing college contact info
            result = await db.execute(
                select(College).where(College.id == staff.college_id)
            )
            college = result.scalar_one_or_none()
            if college:
                college.contact_number = request.contact_number
                college.contact_staff_id = staff.id
        
        await db.commit()

        # Clear OTP after successful profile setup
        await CMSOTPManager.expire_otp(email)

        logger.info(f"Profile setup completed for {email}")

        return SignupResponse(
            success=True,
            message="Account created successfully. Please sign in with your new password.",
            attemptsRemaining=3
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile setup error for {request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def send_forgot_password_otp(
    request: ForgotPasswordRequest, 
    db: AsyncSession = Depends(get_db)
):
    """
    Send OTP for password reset
    - Check if user exists and is verified
    - Generate and send OTP via email
    """
    try:
        email = request.email.lower().strip()

        # Check if staff exists
        result = await db.execute(select(Staff).where(Staff.email == email))
        staff = result.scalar_one_or_none()
        
        if not staff or not staff.is_verified:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found or not verified"
            )

        # Generate OTP
        otp = CMSOTPManager.generate_otp()
        
        # Store OTP in Redis
        otp_stored = await CMSOTPManager.store_otp(email, otp)
        
        if not otp_stored:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate OTP. Please try again."
            )

        # Send OTP via email
        email_result = await EmailService.send_password_reset_otp_email(email, otp)
        email_sent = email_result.get("success", False)
        
        if not email_sent:
            # Clear OTP if email failed
            await CMSOTPManager.clear_otp(email)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send OTP email. Please try again."
            )

        # Development mode: Log OTP for easier testing
        if settings.is_development:
            logger.info(f"🔑 [DEV MODE] Password reset OTP for {email}: {otp}")

        logger.info(f"Password reset OTP sent to {email}")

        return ForgotPasswordResponse(
            success=True,
            message="OTP sent successfully. Please check your email to reset your password.",
            attemptsRemaining=3,
            staffExists=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Forgot password error for {request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


@router.post("/reset-password", response_model=SignupResponse)
async def reset_password(
    request: ResetPasswordRequest, 
    db: AsyncSession = Depends(get_db)
):
    """
    Reset password with OTP verification
    - Verify OTP for password reset
    - Update password and clear temporary flags
    - Invalidate all user sessions for security
    """
    try:
        email = request.email.lower().strip()
        otp = request.otp.strip()
        new_password = request.new_password.strip()

        # Verify OTP
        verification_result = await CMSOTPManager.verify_otp(email, otp)
        
        if verification_result["expired"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired. Please request a new one."
            )
        
        if verification_result["exceeded"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Maximum OTP attempts exceeded. Please request a new OTP."
            )
        
        if not verification_result["valid"]:
            attempts_remaining = 3 - verification_result["attempts"]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid OTP. {attempts_remaining} attempts remaining."
            )

        # Get staff from database
        result = await db.execute(select(Staff).where(Staff.email == email))
        staff = result.scalar_one_or_none()
        
        if not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )

        # Hash new password
        hashed_password = cms_auth.get_password_hash(new_password)

        # Update staff password
        staff.hashed_password = hashed_password
        staff.temporary_password = False
        staff.must_reset_password = False
        await db.commit()

        # SECURITY: Invalidate all user sessions
        from app.redis_client import CacheManager
        await CacheManager.invalidate_all_user_sessions(staff.id)

        # Clear OTP after successful password reset
        await CMSOTPManager.expire_otp(email)

        logger.info(f"Password reset completed for {email}, all sessions invalidated")

        return SignupResponse(
            success=True,
            message="Password reset successful. Please sign in with your new password.",
            attemptsRemaining=3
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset error for {request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )