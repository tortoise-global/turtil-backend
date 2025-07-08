"""
Simplified Signup API
Account creation with OTP verification and profile setup
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.database import get_db
from app.models.staff import Staff
from app.models.college import College
from app.core.cms_auth import cms_auth
from app.core.cms_otp import CMSOTPManager, get_client_ip
from app.config import settings
from app.core.aws import EmailService
from app.schemas.signup_schemas import (
    SignupRequest,
    SignupResponse,
    VerifyOTPRequest,
    VerifySignupResponse,
    SetupProfileRequest,
    VerifyPasswordResetOTPRequest,
    ResetPasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
)
import logging

router = APIRouter(prefix="/auth/signup", tags=["CMS Authentication - Signup"])
logger = logging.getLogger(__name__)


@router.post("/", response_model=SignupResponse)
async def send_signup_otp(
    request: SignupRequest,
    http_request: Request,
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
        
        # Get client IP address
        ip_address = get_client_ip(http_request)
        
        # Store OTP in Redis with purpose and IP tracking
        otp_stored = await CMSOTPManager.store_otp(email, otp, purpose="signup", ip_address=ip_address)
        
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
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Signup", {"user_email": request.email}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/verify-otp", response_model=VerifySignupResponse)
async def verify_signup_otp(
    request: VerifyOTPRequest,
    http_request: Request,
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

        # Get client IP address
        ip_address = get_client_ip(http_request)
        
        # Verify OTP with purpose and IP validation
        verification_result = await CMSOTPManager.verify_otp(email, otp, purpose="signup", ip_address=ip_address)
        
        if verification_result["expired"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired. Please request a new one."
            )
        
        if verification_result["purpose_mismatch"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification flow. Please request a new OTP for signup."
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

        # Generate secure temporary token for profile setup
        temp_token = CMSOTPManager.generate_secure_temp_token()
        await CMSOTPManager.store_temp_token(temp_token, email, ttl=300)  # 5 minutes

        logger.info(f"OTP verified for {email}, staff record created/updated")

        return VerifySignupResponse(
            success=True,
            message="Email verified successfully. Please set up your profile to continue.",
            nextStep="profile_setup",
            tempToken=temp_token  # Secure cryptographic token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OTP verification error for {request.email}: {e}", extra={
            "user_email": request.email,
            "operation": "verify_otp",
            "error_type": type(e).__name__
        })
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OTP verification failed due to {type(e).__name__}: {str(e)}"
        )


@router.post("/setup-profile", response_model=SignupResponse)
async def setup_profile(
    request: SetupProfileRequest,
    http_request: Request,
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
        temp_token = request.temp_token.strip()
        password = request.password.strip()

        # Validate temporary token and get email
        email = await CMSOTPManager.validate_temp_token(temp_token)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired temporary token. Please verify your email again."
            )

        # Get client IP address
        ip_address = get_client_ip(http_request)

        # Get staff from database
        result = await db.execute(select(Staff).where(Staff.email == email))
        staff = result.scalar_one_or_none()
        
        if not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found. Please complete email verification first."
            )

        # Comprehensive OTP validation for consumption
        otp_validation = await CMSOTPManager.validate_otp_for_action(email, "signup", ip_address)
        if not otp_validation["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=otp_validation["reason"]
            )

        # Hash password
        hashed_password = cms_auth.get_password_hash(password)

        # Update staff with password and profile
        staff.hashed_password = hashed_password
        staff.full_name = request.full_name
        staff.contact_number = request.contact_number
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
                principal_staff_id=staff.staff_id,
                contact_number=request.contact_number,
                contact_staff_id=staff.staff_id,
            )
            db.add(college)
            await db.commit()
            await db.refresh(college)
            
            # Update staff with college and role
            staff.college_id = college.college_id
            staff.cms_role = "principal"
            staff.can_assign_department = True
        else:
            # Update existing college contact info
            result = await db.execute(
                select(College).where(College.college_id == staff.college_id)
            )
            college = result.scalar_one_or_none()
            if college:
                college.contact_number = request.contact_number
                college.contact_staff_id = staff.staff_id
        
        await db.commit()

        # Consume OTP after successful profile setup (one-time use enforcement)
        await CMSOTPManager.consume_otp(email, "signup")
        
        # Clear temporary token
        if temp_token:
            await CMSOTPManager.clear_temp_token(temp_token)

        logger.info(f"Profile setup completed for {email}")

        # Send signup confirmation email
        try:
            college_name = college.name if college and college.name else None
            await EmailService.send_signup_confirmation_email(
                email=email,
                full_name=staff.full_name,
                college_name=college_name
            )
        except Exception as e:
            # Don't fail signup if confirmation email fails
            logger.warning(f"Failed to send signup confirmation email to {email}: {e}")

        return SignupResponse(
            success=True,
            message="Account created successfully. Please sign in with your new password.",
            attemptsRemaining=3
        )

    except HTTPException:
        raise
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Profile setup", {"user_email": request.email}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def send_forgot_password_otp(
    request: ForgotPasswordRequest,
    http_request: Request,
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
        
        # Get client IP address
        ip_address = get_client_ip(http_request)
        
        # Store OTP in Redis with password reset purpose and IP tracking
        otp_stored = await CMSOTPManager.store_otp(email, otp, purpose="password_reset", ip_address=ip_address)
        
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
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Forgot password", {"user_email": request.email}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/verify-forgot-password", response_model=VerifySignupResponse)
async def verify_password_reset_otp(
    request: VerifyPasswordResetOTPRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify OTP for password reset (shared with signup verification)
    - This reuses the same OTP verification logic as signup
    - Returns temporary token for password reset completion
    """
    try:
        email = request.email.lower().strip()
        otp = request.otp.strip()

        # Get client IP address
        ip_address = get_client_ip(http_request)
        
        # Verify OTP with password reset purpose and IP validation
        verification_result = await CMSOTPManager.verify_otp(email, otp, purpose="password_reset", ip_address=ip_address)
        
        if verification_result["expired"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired. Please request a new one."
            )
        
        if verification_result["purpose_mismatch"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification flow. Please request a new OTP for password reset."
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

        # Check if staff exists and is verified
        result = await db.execute(select(Staff).where(Staff.email == email))
        staff = result.scalar_one_or_none()
        
        if not staff or not staff.is_verified:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found or not verified"
            )

        # Mark OTP as verified in Redis
        await CMSOTPManager.mark_otp_verified(email)

        # Generate secure temporary token for password reset
        temp_token = CMSOTPManager.generate_secure_temp_token()
        await CMSOTPManager.store_temp_token(temp_token, email, ttl=300)  # 5 minutes

        logger.info(f"Password reset OTP verified for {email}")

        return VerifySignupResponse(
            success=True,
            message="OTP verified successfully. You can now reset your password.",
            nextStep="password_reset",
            tempToken=temp_token  # Secure cryptographic token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Password reset OTP verification", {"user_email": request.email}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/reset-password", response_model=SignupResponse)
async def reset_password(
    request: ResetPasswordRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Reset password with OTP verification
    - Verify OTP for password reset
    - Update password and clear temporary flags
    - Invalidate all user sessions for security
    """
    try:
        temp_token = request.temp_token.strip()
        new_password = request.password.strip()

        # Validate temporary token and get email
        email = await CMSOTPManager.validate_temp_token(temp_token)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired temporary token. Please verify your OTP again."
            )

        # Get client IP address
        ip_address = get_client_ip(http_request)

        # Get staff from database
        result = await db.execute(select(Staff).where(Staff.email == email))
        staff = result.scalar_one_or_none()
        
        if not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )

        # Comprehensive OTP validation for consumption
        otp_validation = await CMSOTPManager.validate_otp_for_action(email, "password_reset", ip_address)
        if not otp_validation["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=otp_validation["reason"]
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
        await CacheManager.invalidate_all_user_sessions(staff.staff_id)

        # Consume OTP after successful password reset (one-time use enforcement)
        await CMSOTPManager.consume_otp(email, "password_reset")
        
        # Clear temporary token
        await CMSOTPManager.clear_temp_token(temp_token)

        logger.info(f"Password reset completed for {email}, all sessions invalidated")

        # Send password reset confirmation email
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
            await EmailService.send_password_reset_confirmation_email(
                email=email,
                full_name=staff.full_name,
                timestamp=timestamp,
                ip_address=ip_address
            )
        except Exception as e:
            # Don't fail password reset if confirmation email fails
            logger.warning(f"Failed to send password reset confirmation email to {email}: {e}")

        return SignupResponse(
            success=True,
            message="Password reset successful. Please sign in with your new password.",
            attemptsRemaining=3
        )
        
    except HTTPException:
        raise
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Password reset", {"user_email": getattr(request, 'email', 'unknown')}, status.HTTP_500_INTERNAL_SERVER_ERROR)