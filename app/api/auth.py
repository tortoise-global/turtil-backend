from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.auth import (
    SignupInitRequest,
    SignupVerifyRequest,
    StaffLoginRequest,
    LoginResponse,
    LogoutResponse,
    AuthResponse,
    TokenResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
    ChangePasswordRequest,
    RefreshTokenRequest,
    SignupInitResponse,
    SignupVerifyResponse,
)
from app.models.staff import Staff
from app.core.auth import auth
from app.core.otp import otp_manager
from app.core.aws import EmailService
from app.api.deps import get_current_staff, get_current_verified_staff
from app.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/signup/init", response_model=SignupInitResponse)
async def signup_init(request: SignupInitRequest, db: AsyncSession = Depends(get_db)):
    """
    Initialize signup process - send OTP to email
    """
    try:
        # Check if staff already exists
        existing_staff = await auth.get_staff_by_email(db, request.email)
        if existing_staff:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Staff with this email already exists",
            )

        # Generate OTP and signup token
        otp_code = otp_manager.generate_otp()
        signup_token = otp_manager.generate_signup_token()

        # Store signup data temporarily in Redis (don't hash password yet)
        signup_data = {
            "first_name": request.first_name,
            "last_name": request.last_name,
            "password": request.password,  # Store plain password temporarily
        }

        # Store in Redis with expiration
        success = await otp_manager.store_signup_otp(
            email=request.email,
            otp=otp_code,
            signup_data=signup_data,
            signup_token=signup_token,
            expiry_minutes=settings.otp_expiry_minutes,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initiate signup process",
            )

        # Send OTP email
        await EmailService.send_signup_otp_email(request.email, otp_code)

        logger.info(f"Signup OTP sent to: {request.email}")

        return SignupInitResponse(
            message="Signup OTP sent to your email address",
            success=True,
            signup_token=signup_token,
            expires_in_minutes=settings.otp_expiry_minutes,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in signup_init: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/signup/verify", response_model=SignupVerifyResponse)
async def signup_verify(
    request: SignupVerifyRequest, db: AsyncSession = Depends(get_db)
):
    """
    Verify OTP and complete staff registration (hash password only here)
    """
    try:
        # Verify OTP and get signup data
        verified_data = await otp_manager.verify_signup_otp(request.email, request.otp)

        if not verified_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP"
            )

        # Validate signup token if provided
        if hasattr(request, "signup_token") and request.signup_token:
            if verified_data.get("signup_token") != request.signup_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid signup token",
                )

        signup_data = verified_data["signup_data"]

        # Now create the staff - password gets hashed here
        staff = await auth.create_staff(
            db=db,
            email=request.email,
            password=signup_data["password"],  # This will be hashed in create_staff
            first_name=signup_data["first_name"],
            last_name=signup_data["last_name"],
            is_verified=True,  # Mark as verified since they verified OTP
        )

        # Clean up Redis data
        await otp_manager.cleanup_signup_otp(
            request.email, verified_data["signup_token"]
        )

        # Create tokens for immediate login
        token_data = staff.to_token_payload()
        access_token = auth.create_access_token(token_data)
        refresh_token = auth.create_refresh_token(token_data)

        # Record login
        staff.record_login()
        await db.commit()

        logger.info(f"Staff signup completed and logged in: {request.email}")

        # Prepare token response
        tokens = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            staff=staff.to_dict(),
        )

        return SignupVerifyResponse(
            message="Signup completed successfully. You are now logged in.",
            success=True,
            staff=staff.to_dict(),
            tokens=tokens,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in signup_verify: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/login", response_model=LoginResponse)
async def login_staff(request: StaffLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Authenticate staff with email and password
    """
    try:
        # Authenticate staff
        staff = await auth.authenticate_staff(db, request.email, request.password)

        if not staff:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        # Check if staff is active
        if not staff.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Staff account is inactive"
            )

        # Create tokens
        token_data = staff.to_token_payload()
        access_token = auth.create_access_token(token_data)
        refresh_token = auth.create_refresh_token(token_data)

        logger.info(f"Staff logged in: {request.email}")

        # Prepare token response
        tokens = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            staff=staff.to_dict(),
        )

        return LoginResponse(message="Login successful", success=True, tokens=tokens)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in login_staff: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout_staff(current_staff: Staff = Depends(get_current_staff)):
    """
    Logout staff (token blacklisting can be implemented here)
    """
    try:
        logger.info(f"Staff logged out: {current_staff.email}")

        return LogoutResponse(message="Logout successful", success=True)

    except Exception as e:
        logger.error(f"Error in logout_staff: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    try:
        # Verify refresh token
        payload = auth.verify_token(request.refresh_token)

        # Check token type
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )

        # Get staff UUID from token
        staff_uuid = payload.get("sub")
        if not staff_uuid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )

        # Get staff from database
        staff = await auth.get_staff_by_token(db, request.refresh_token)
        if not staff:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Staff not found or inactive",
            )

        # Create new access token
        token_data = staff.to_token_payload()
        new_access_token = auth.create_access_token(token_data)

        logger.info(f"Token refreshed for staff: {staff.email}")

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=request.refresh_token,  # Keep same refresh token
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            staff=staff.to_dict(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in refresh_token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/forgot-password", response_model=AuthResponse)
async def forgot_password(
    request: PasswordResetRequest, db: AsyncSession = Depends(get_db)
):
    """
    Send password reset OTP to staff's email
    """
    try:
        # Check if staff exists
        staff = await auth.get_staff_by_email(db, request.email)

        if not staff:
            # Don't reveal if email exists for security
            return AuthResponse(
                message="If an account with this email exists, you will receive a password reset code.",
                success=True,
            )

        # Generate OTP
        otp_code = otp_manager.generate_otp()

        # Store OTP in Redis
        success = await otp_manager.store_login_otp(
            email=request.email,
            otp=otp_code,
            expiry_minutes=settings.otp_expiry_minutes,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate password reset code",
            )

        # Send password reset email
        await EmailService.send_password_reset_email(request.email, otp_code)

        logger.info(f"Password reset OTP sent to: {request.email}")

        return AuthResponse(
            message="Password reset code sent to your email address", success=True
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in forgot_password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/reset-password", response_model=AuthResponse)
async def reset_password(
    request: PasswordResetConfirm, db: AsyncSession = Depends(get_db)
):
    """
    Reset password using OTP
    """
    try:
        # Verify OTP
        is_valid = await otp_manager.verify_login_otp(request.email, request.otp)

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset code",
            )

        # Find staff
        staff = await auth.get_staff_by_email(db, request.email)

        if not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found"
            )

        # Update password (hash it)
        staff.hashed_password = auth.hash_password(request.new_password)
        await db.commit()

        logger.info(f"Password reset successful for: {request.email}")

        return AuthResponse(
            message="Password reset successful", success=True, staff=staff.to_dict()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in reset_password: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/change-password", response_model=AuthResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_staff: Staff = Depends(get_current_verified_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Change password for authenticated staff
    """
    try:
        # Verify current password
        if not auth.verify_password(
            request.current_password, current_staff.hashed_password
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        # Update password (hash it)
        current_staff.hashed_password = auth.hash_password(request.new_password)
        await db.commit()

        logger.info(f"Password changed for staff: {current_staff.email}")

        return AuthResponse(
            message="Password changed successfully",
            success=True,
            staff=current_staff.to_dict(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in change_password: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/me", response_model=AuthResponse)
async def get_current_staff_info(current_staff: Staff = Depends(get_current_staff)):
    """
    Get current authenticated staff information
    """
    return AuthResponse(
        message="Staff information retrieved successfully",
        success=True,
        staff=current_staff.to_dict(),
    )
