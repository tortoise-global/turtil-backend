"""
Student Authentication API
Mobile app authentication endpoints with single-device session management
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.database import get_db
from app.models.student import Student
from app.core.student_auth import student_auth
from app.core.student_session_manager import student_session_manager
from app.core.cms_otp import CMSOTPManager
from app.core.aws import EmailService
from app.config import settings
from app.api.student.deps import get_current_student_session, get_client_ip
from app.schemas.student_auth_schemas import (
    StudentSignupRequest, StudentSignupResponse,
    StudentVerifyOTPRequest, StudentVerifyOTPResponse,
    StudentSetupProfileRequest, StudentSetupProfileResponse,
    StudentSigninRequest, StudentSigninResponse,
    StudentRefreshTokenRequest, StudentRefreshTokenResponse,
    StudentCurrentSessionResponse, StudentLogoutResponse,
    StudentForgotPasswordRequest, StudentForgotPasswordResponse,
    StudentResetPasswordRequest, StudentResetPasswordResponse,
    StudentRegistrationStatusResponse, StudentRegistrationProgress,
    StudentProfileResponse, StudentUpdateProfileRequest
)
import logging

router = APIRouter(prefix="/auth", tags=["Student Authentication"])
logger = logging.getLogger(__name__)


@router.post("/signup", response_model=StudentSignupResponse)
async def send_student_signup_otp(
    request: StudentSignupRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Step 1: Send OTP for student account creation
    - Check if student already exists
    - Generate and send OTP via email
    """
    try:
        email = request.email.lower().strip()

        # Check if student already exists and is verified
        result = await db.execute(select(Student).where(Student.email == email))
        existing_student = result.scalar_one_or_none()
        
        if existing_student and existing_student.is_verified and existing_student.hashed_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account already exists. Please use sign in instead."
            )

        # Generate OTP
        otp = CMSOTPManager.generate_otp()
        
        # Get client IP address
        ip_address = get_client_ip(http_request)
        
        # Store OTP in Redis with purpose and IP tracking
        otp_stored = await CMSOTPManager.store_otp(email, otp, purpose="student_signup", ip_address=ip_address)
        
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
        if settings.debug:
            logger.info(f"🔑 [DEV MODE] Student Signup OTP for {email}: {otp}")

        logger.info(f"Student signup OTP sent to {email}")
        
        return StudentSignupResponse()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Student signup error for {request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


@router.post("/verify-otp", response_model=StudentVerifyOTPResponse)
async def verify_student_signup_otp(
    request: StudentVerifyOTPRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Step 2: Verify OTP and create temporary student record
    - Verify OTP with attempt tracking
    - Create or update student record
    - Return temporary token for profile setup
    """
    try:
        email = request.email.lower().strip()
        otp = request.otp.strip()

        # Get client IP address
        ip_address = get_client_ip(http_request)
        
        # Verify OTP with purpose and IP validation
        verification_result = await CMSOTPManager.verify_otp(email, otp, purpose="student_signup", ip_address=ip_address)
        
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

        # Check if student already exists
        result = await db.execute(select(Student).where(Student.email == email))
        existing_student = result.scalar_one_or_none()
        
        if existing_student and existing_student.is_verified and existing_student.hashed_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account already exists. Please use sign in instead."
            )

        # Create new student record if doesn't exist
        if not existing_student:
            student = Student(
                email=email,
                full_name="",  # Will be filled in next step
                hashed_password="",  # Will be filled in next step
                is_verified=True,  # Email is verified via OTP
                registration_details={"current_step": "profile_setup"}
            )
            db.add(student)
            await db.commit()
            await db.refresh(student)
        else:
            # Update existing unverified student
            student = existing_student
            student.is_verified = True
            student.email_verified_at = datetime.now(timezone.utc)
            await db.commit()

        # Mark OTP as verified in Redis
        await CMSOTPManager.mark_otp_verified(email)

        # Generate secure temporary token for profile setup
        temp_token = CMSOTPManager.generate_secure_temp_token()
        await CMSOTPManager.store_temp_token(temp_token, email, ttl=300)  # 5 minutes

        logger.info(f"Student OTP verified for {email}, student record created/updated")

        return StudentVerifyOTPResponse(tempToken=temp_token)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Student OTP verification error for {request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


@router.post("/setup-profile", response_model=StudentSetupProfileResponse)
async def setup_student_profile(
    request: StudentSetupProfileRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Step 3: Complete profile setup with password and personal details
    - Verify temporary token
    - Set password and full name
    - Complete basic account setup
    """
    try:
        temp_token = request.tempToken.strip()
        password = request.password.strip()
        full_name = request.fullName.strip()

        # Validate temporary token and get email
        email = await CMSOTPManager.validate_temp_token(temp_token)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired temporary token. Please verify your email again."
            )

        # Get client IP address
        ip_address = get_client_ip(http_request)

        # Get student from database
        result = await db.execute(select(Student).where(Student.email == email))
        student = result.scalar_one_or_none()
        
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found. Please complete email verification first."
            )

        # Validate OTP for action
        otp_validation = await CMSOTPManager.validate_otp_for_action(email, "student_signup", ip_address)
        if not otp_validation["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=otp_validation["reason"]
            )

        # Hash password
        hashed_password = student_auth.get_password_hash(password)

        # Update student with password and profile
        student.hashed_password = hashed_password
        student.full_name = full_name
        student.update_registration_step("college_selection", {"profile_completed": True})
        
        await db.commit()

        # Consume OTP after successful profile setup
        await CMSOTPManager.consume_otp(email, "student_signup")
        
        # Clear temporary token
        await CMSOTPManager.clear_temp_token(temp_token)

        logger.info(f"Student profile setup completed for {email}")

        return StudentSetupProfileResponse()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Student profile setup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


@router.post("/signin", response_model=StudentSigninResponse)
async def student_signin(
    request: StudentSigninRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Student sign in with single-device enforcement
    - Validates email and password
    - Automatically logs out from all other devices
    - Creates new session with device tracking
    """
    try:
        email = request.email.lower().strip()
        
        # Find student by email
        result = await db.execute(select(Student).where(Student.email == email))
        student = result.scalar_one_or_none()
        
        if not student:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Authenticate student
        if not student_auth.authenticate_student(email, request.password, student):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Get device information
        user_agent = http_request.headers.get("User-Agent", "")
        ip_address = get_client_ip(http_request)
        
        # Create session with single-device enforcement
        session_data = await student_session_manager.create_student_session(
            student=student,
            user_agent=user_agent,
            ip_address=ip_address,
            db=db
        )
        
        # Update login tracking and expo push token
        student.record_login()
        student.update_expo_push_token(request.expoPushToken)
        await db.commit()
        
        logger.info(f"Student signin successful for {email} from {ip_address}")
        
        # Send login notification email (non-blocking)
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
            await EmailService.send_login_notification_email(
                email=email,
                full_name=student.full_name,
                device_info=session_data["device_info"],
                ip_address=ip_address,
                timestamp=timestamp
            )
        except Exception as e:
            logger.warning(f"Failed to send login notification email to {email}: {e}")
        
        return StudentSigninResponse(
            accessToken=session_data["access_token"],
            refreshToken=session_data["refresh_token"],
            expiresIn=session_data["expires_in"],
            deviceInfo=session_data["device_info"],
            student=student.to_dict(),
            registrationRequired=not student.registration_completed
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Student signin error for {request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sign in"
        )


@router.post("/refresh", response_model=StudentRefreshTokenResponse)
async def refresh_student_tokens(
    request: StudentRefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh student access token using refresh token
    Mandatory token rotation for security
    """
    try:
        refresh_token = request.refreshToken
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No refresh token found. Please sign in again."
            )
        
        # Extract session_id from refresh token JWT payload
        try:
            from jose import jwt
            payload = jwt.decode(refresh_token, key="", options={"verify_signature": False})
            session_id = payload.get("session_id")
            
            if not session_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid token format. Please sign in again."
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid refresh token format"
            )
        
        # Refresh session with mandatory token rotation
        token_data = await student_session_manager.refresh_student_session(
            session_id=session_id,
            refresh_token=refresh_token,
            db=db
        )
        
        logger.info(f"Student token refreshed for session {session_id}")
        
        return StudentRefreshTokenResponse(
            accessToken=token_data["access_token"],
            refreshToken=token_data["refresh_token"],
            expiresIn=token_data["expires_in"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Student token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh tokens"
        )


@router.get("/current-session", response_model=StudentCurrentSessionResponse)
async def get_student_current_session(
    current_session: dict = Depends(get_current_student_session)
):
    """Get current student session information"""
    try:
        session_info = current_session["session_info"]
        
        return StudentCurrentSessionResponse(
            sessionId=current_session["session_id"],
            deviceInfo=session_info["device_info"],
            createdAt=int(session_info.get("created_at", 0)),
            lastUsed=int(session_info.get("last_used", 0)),
            ipAddress=session_info.get("ip_address")
        )
        
    except Exception as e:
        logger.error(f"Get student current session error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get session info"
        )


@router.post("/signout", response_model=StudentLogoutResponse)
async def student_signout(
    current_session: dict = Depends(get_current_student_session),
    db: AsyncSession = Depends(get_db)
):
    """Sign out student from current session"""
    try:
        student = current_session["student"]
        session_id = current_session["session_id"]
        
        # Invalidate current session
        success = await student_session_manager.invalidate_student_session(
            session_id, str(student.student_id), db
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to sign out"
            )
        
        logger.info(f"Student {student.email} signed out from session {session_id}")
        
        return StudentLogoutResponse()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Student signout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sign out"
        )


@router.get("/registration-status", response_model=StudentRegistrationStatusResponse)
async def get_student_registration_status(
    current_session: dict = Depends(get_current_student_session)
):
    """Get student's current academic registration status"""
    try:
        student = current_session["student"]
        progress = student.get_registration_progress()
        
        return StudentRegistrationStatusResponse(
            registrationCompleted=student.registration_completed,
            progress=StudentRegistrationProgress(
                currentStep=progress["current_step"],
                progressPercentage=progress["progress_percentage"],
                details=progress["details"],
                canAccessApp=student.can_access_app()
            )
        )
        
    except Exception as e:
        logger.error(f"Get student registration status error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get registration status"
        )