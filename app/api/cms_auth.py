from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime, timezone

from app.database import get_db
from app.models.staff import Staff
from app.models.college import College
from app.core.cms_auth import cms_auth
from app.core.cms_otp import CMSOTPManager
from app.config import settings
from app.core.aws import EmailService
from app.schemas.cms_auth import (
    CMSSignupRequest,
    CMSSignupResponse,
    CMSVerifySignupRequest,
    CMSVerifySignupResponse,
    CMSSetPasswordRequest,
    CMSResetPasswordRequest,
    CMSLoginRequest,
    CMSLoginResponse,
    CMSSigninRequest,
    CMSSigninResponse,
    CMSTokenResponse,
    StaffProfileResponse,
)

router = APIRouter(prefix="/auth", tags=["CMS Authentication"])

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


# =====================================
# SIGNUP FLOW
# =====================================

@router.post("/signup", response_model=CMSSignupResponse)
async def signup(request: CMSSignupRequest, db: AsyncSession = Depends(get_db)):
    """
    Signup Step 1: Send OTP to email
    - Check if user already exists
    - Generate and send OTP
    - Return success response
    """
    try:
        email = request.email.lower().strip()

        # Check if staff already exists and is verified
        result = await db.execute(
            select(Staff).where(Staff.email == email)
        )
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
            print(f"🔑 [DEV MODE] Signup OTP for {email}: {otp}")

        return CMSSignupResponse(
            success=True,
            message="OTP sent successfully. Please check your email to continue registration.",
            attemptsRemaining=3
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error during signup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


@router.post("/verify-otp", response_model=CMSVerifySignupResponse)
async def verify_otp(request: CMSVerifySignupRequest, db: AsyncSession = Depends(get_db)):
    """
    Signup Step 2: Verify OTP
    - Verify OTP with attempt tracking
    - Create staff record if doesn't exist
    - Return temp token for password setup
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
        result = await db.execute(
            select(Staff).where(Staff.email == email)
        )
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
                full_name="",  # Will be filled later
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

        return CMSVerifySignupResponse(
            success=True,
            message="Email verified successfully. Please set your password to continue.",
            nextStep="password_setup",
            tempToken=email  # Simple temp token for password setup
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error verifying OTP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


@router.post("/set-password", response_model=CMSSignupResponse)
async def set_password(request: CMSSetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """
    Signup Step 3: Set password
    - Verify OTP was verified for this email
    - Hash and store password
    - Complete registration
    """
    try:
        email = request.email.lower().strip()
        password = request.password.strip()

        # Get staff from database
        result = await db.execute(
            select(Staff).where(Staff.email == email)
        )
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

        # Update staff with password
        staff.hashed_password = hashed_password
        staff.temporary_password = False
        staff.must_reset_password = False
        await db.commit()

        # Clear OTP after successful password setup
        await CMSOTPManager.expire_otp(email)

        return CMSSignupResponse(
            success=True,
            message="Account created successfully. Please sign in with your new password.",
            attemptsRemaining=3
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error setting password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


# =====================================
# SIGNIN FLOW
# =====================================

@router.post("/signin", response_model=CMSLoginResponse)
async def signin(request: CMSLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Sign in with email and password
    - Validate email and password
    - Generate JWT tokens
    - Return access and refresh tokens
    """
    try:
        email = request.email.lower().strip()
        password = request.password.strip()

        # Get staff from database
        result = await db.execute(
            select(Staff).where(Staff.email == email)
        )
        staff = result.scalar_one_or_none()
        
        if not staff:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        if not staff.is_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email not verified. Please complete registration first."
            )
        
        if not staff.hashed_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Password not set. Please complete registration first."
            )
        
        # Verify password
        if not cms_auth.verify_password(password, staff.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Generate JWT tokens
        access_token = cms_auth.create_access_token(staff)
        refresh_token = cms_auth.create_refresh_token(staff)
        
        # Update login tracking
        staff.record_login()
        await db.commit()
        
        # Create staff session in Redis
        await cms_auth.create_staff_session(staff, refresh_token)

        return CMSLoginResponse(
            success=True,
            message="Login successful",
            accessToken=access_token,
            refreshToken=refresh_token,
            tokenType="bearer",
            expiresIn=settings.cms_access_token_expire_minutes * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error during signin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


# =====================================
# FORGOT PASSWORD FLOW
# =====================================

@router.post("/forgot-password", response_model=CMSSigninResponse)
async def forgot_password(request: CMSSigninRequest, db: AsyncSession = Depends(get_db)):
    """
    Forgot Password Step 1: Send OTP to email
    - Check if user exists
    - Generate and send OTP for password reset
    """
    try:
        email = request.email.lower().strip()

        # Check if staff exists
        result = await db.execute(
            select(Staff).where(Staff.email == email)
        )
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
            print(f"🔑 [DEV MODE] Password reset OTP for {email}: {otp}")

        return CMSSigninResponse(
            success=True,
            message="OTP sent successfully. Please check your email to reset your password.",
            attemptsRemaining=3,
            staffExists=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error during forgot password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


@router.post("/reset-password", response_model=CMSSignupResponse)
async def reset_password(request: CMSResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """
    Reset Password Step 2: Verify OTP and set new password
    - Verify OTP
    - Update password
    - Clear OTP
    """
    try:
        email = request.email.lower().strip()
        otp = request.otp.strip()
        new_password = request.newPassword.strip()

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
        result = await db.execute(
            select(Staff).where(Staff.email == email)
        )
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

        # Clear OTP after successful password reset
        await CMSOTPManager.expire_otp(email)

        return CMSSignupResponse(
            success=True,
            message="Password reset successful. Please sign in with your new password.",
            attemptsRemaining=3
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error resetting password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


# =====================================
# AUTHENTICATED ROUTES
# =====================================

async def get_current_staff(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Staff:
    """
    Get current authenticated staff from JWT token
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

        # Validate token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid token type"
            )

        # Get staff UUID from token
        staff_uuid = payload.get("sub")
        if not staff_uuid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid token payload"
            )

        # Get staff from database
        result = await db.execute(select(Staff).where(Staff.uuid == staff_uuid))
        staff = result.scalar_one_or_none()

        if not staff or not staff.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Staff not found or inactive",
            )

        # Validate session in Redis
        session_data = await cms_auth.validate_session(staff.id, credentials.credentials)
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired or invalid",
            )

        return staff

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting current staff: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )


@router.get("/me", response_model=StaffProfileResponse, dependencies=[Depends(security)])
async def get_current_user_profile(current_staff: Staff = Depends(get_current_staff)):
    """
    Get current authenticated user profile
    """
    try:
        return StaffProfileResponse(
            staffId=current_staff.id,
            uuid=str(current_staff.uuid),
            email=current_staff.email,
            fullName=current_staff.full_name,
            cmsRole=current_staff.cms_role,
            collegeId=current_staff.college_id,
            departmentId=current_staff.department_id,
            invitationStatus=current_staff.invitation_status,
            mustResetPassword=current_staff.must_reset_password,
            isHod=current_staff.is_hod,
            createdAt=current_staff.created_at,
        )

    except Exception as e:
        print(f"Error getting user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


@router.post("/logout", response_model=CMSSignupResponse, dependencies=[Depends(security)])
async def logout(current_staff: Staff = Depends(get_current_staff)):
    """
    Logout user by clearing Redis session
    """
    try:
        success = await cms_auth.logout_staff(current_staff.id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to logout. Please try again."
            )

        return CMSSignupResponse(
            success=True, 
            message="Logged out successfully",
            attemptsRemaining=3
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error during logout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )