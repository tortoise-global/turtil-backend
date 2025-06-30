"""
Student Authentication API - Phone-Based
Mobile app authentication endpoints with phone-based single-device session management
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.database import get_db
from app.models.student import Student
from app.core.student_auth import student_auth
from app.core.student_session_manager import student_session_manager
from app.core.mock_sms import PhoneOTPManager, MockSMSService
from app.config import settings
from app.api.student.deps import get_current_student_session, get_client_ip
from app.schemas.student_auth_schemas import (
    StudentSigninRequest, StudentSigninResponse,
    StudentVerifyOTPRequest, StudentVerifyOTPResponse,
    StudentRefreshTokenRequest, StudentRefreshTokenResponse,
    StudentCurrentSessionResponse, StudentLogoutResponse
)
import logging

router = APIRouter(prefix="/auth", tags=["Student Authentication"])
logger = logging.getLogger(__name__)


@router.post("/signin", response_model=StudentSigninResponse)
async def student_signin_send_otp(
    request: StudentSigninRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Step 1: Send OTP to phone number for authentication
    - Format and validate phone number
    - Send OTP via mock SMS service
    - Create or update student record if needed
    """
    try:
        phone_number = request.phoneNumber.strip()
        
        # Format phone number to consistent format
        formatted_phone = MockSMSService.format_phone_number(phone_number)
        
        # Send OTP via mock SMS service
        otp_result = await PhoneOTPManager.send_phone_otp(formatted_phone, purpose="signin")
        
        if not otp_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send OTP: {otp_result.get('error', 'Unknown error')}"
            )
        
        # Check if student exists, create if not
        result = await db.execute(select(Student).where(Student.phone_number == formatted_phone))
        existing_student = result.scalar_one_or_none()
        
        if not existing_student:
            # Create new student record with minimal data
            student = Student(
                phone_number=formatted_phone,
                is_verified=False,  # Will be verified after OTP
                registration_details={"current_step": "college_selection"}
            )
            db.add(student)
            await db.commit()
            logger.info(f"New student record created for phone: {formatted_phone}")
        else:
            logger.info(f"Existing student found for phone: {formatted_phone}")

        # Development mode: Include OTP in response for easier testing
        response_data = {
            "phoneNumber": formatted_phone,
        }
        
        if settings.debug and otp_result.get("otp"):
            logger.info(f"🔑 [DEV MODE] Phone OTP for {formatted_phone}: {otp_result['otp']}")

        return StudentSigninResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Student signin OTP error for {request.phoneNumber}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


@router.post("/verify-otp", response_model=StudentVerifyOTPResponse)
async def student_verify_otp_and_authenticate(
    request: StudentVerifyOTPRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Step 2: Verify OTP and authenticate student
    - Verify OTP with mock service
    - Create session with device tracking
    - Return JWT tokens for authenticated access
    """
    try:
        phone_number = request.phoneNumber.strip()
        otp = request.otp.strip()
        expo_push_token = request.expoPushToken.strip()
        
        # Format phone number
        formatted_phone = MockSMSService.format_phone_number(phone_number)
        
        # Verify OTP with mock service
        verification_result = PhoneOTPManager.verify_phone_otp(formatted_phone, otp)
        
        if not verification_result["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=verification_result.get("message", "Invalid OTP")
            )
        
        # Get student record
        result = await db.execute(select(Student).where(Student.phone_number == formatted_phone))
        student = result.scalar_one_or_none()
        
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student account not found. Please try signing in again."
            )
        
        # Mark phone as verified
        if not student.is_verified:
            student.verify_phone()
        
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
        student.update_expo_push_token(expo_push_token)
        await db.commit()
        
        logger.info(f"Student authentication successful for {formatted_phone} from {ip_address}")
        
        return StudentVerifyOTPResponse(
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
        logger.error(f"Student OTP verification error for {request.phoneNumber}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed. Please try again."
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
        
        logger.info(f"Student {student.phone_number} signed out from session {session_id}")
        
        return StudentLogoutResponse()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Student signout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sign out"
        )