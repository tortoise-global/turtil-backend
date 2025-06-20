from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.database import get_db
from app.models.staff import Staff
from app.models.college import College
from app.core.cms_auth import cms_auth
from app.core.cms_otp import CMSOTPManager
from app.core.aws import EmailService
from app.schemas.cms_auth import (
    CMSSigninRequest,
    CMSVerifySigninRequest,
    CMSPasswordSetupRequest,
    CMSPersonalDetailsRequest,
    CMSCollegeDetailsRequest,
    CMSAddressDetailsRequest,
    CMSResetPasswordRequest,
    CMSSigninResponse,
    CMSTokenResponse,
    CMSVerifySigninResponse,
    CMSRegistrationStepResponse,
    StaffProfileResponse,
    CMSRefreshTokenRequest,
    CMSRefreshTokenResponse,
)

router = APIRouter(prefix="/cms/auth", tags=["CMS Authentication"])

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


async def get_current_staff(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Staff:
    """
    Get current authenticated staff from JWT token with blacklist validation
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Check if token is blacklisted
        is_blacklisted = await cms_auth.is_token_blacklisted(credentials.credentials)
        if is_blacklisted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )

        # Decode token
        payload = cms_auth.decode_token(credentials.credentials)

        # Validate token type
        if payload.get("type") != "access":
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
        print(f"Error getting current CMS staff: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )


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
                detail="Invalid token type for this endpoint",
            )

        # Get staff UUID from token
        staff_uuid = payload.get("sub")
        if not staff_uuid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )

        # Get staff from database
        result = await db.execute(select(Staff).where(Staff.uuid == staff_uuid))
        staff = result.scalar_one_or_none()

        if not staff:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Staff not found"
            )

        return staff

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting current CMS staff from temp token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid temporary token"
        )


@router.post("/signin", response_model=CMSSigninResponse)
async def signin(request: CMSSigninRequest, db: AsyncSession = Depends(get_db)):
    """
    Combined Sign-in: Send OTP for both new and existing staffs
    - Generate 6-digit OTP
    - Store in Redis with 3 attempts and 5-minute expiry
    - Send via AWS SES
    - Return whether staff already exists
    """
    try:
        # Check if staff already exists
        result = await db.execute(
            select(Staff).where(Staff.email == request.email.lower())
        )
        existing_staff = result.scalar_one_or_none()
        staff_exists = existing_staff is not None and existing_staff.is_verified

        # Generate OTP
        otp = CMSOTPManager.generate_otp()

        # Store OTP in Redis
        otp_stored = await CMSOTPManager.store_otp(request.email.lower(), otp)

        if not otp_stored:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate OTP. Please try again.",
            )

        # Send OTP via email
        email_result = await EmailService.send_otp_email(request.email, otp)
        email_sent = email_result.get("success", False)

        if not email_sent:
            # Clear OTP if email failed
            await CMSOTPManager.clear_otp(request.email.lower())
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send OTP email. Please try again.",
            )

        message = "OTP sent successfully to your email address."
        if staff_exists:
            message += " You will be logged in after verification."
        else:
            message += " Complete registration after verification."

        return CMSSigninResponse(
            success=True,
            message=message,
            attemptsRemaining=3,
            canResend=True,
            staffExists=staff_exists,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error sending OTP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        )


@router.post("/verify-signin", response_model=CMSVerifySigninResponse)
async def verify_signin(
    request: CMSVerifySigninRequest, db: AsyncSession = Depends(get_db)
):
    """
    Verify Sign-in OTP: Handle both login and registration flows
    - Verify OTP with attempt tracking
    - If staff exists: return JWT tokens (login)
    - If staff doesn't exist: return temp token for registration
    """
    try:
        # Verify OTP
        verification_result = await CMSOTPManager.verify_otp(
            request.email.lower(), request.otp
        )

        if verification_result["expired"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired. Please request a new one.",
            )

        if verification_result["exceeded"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Maximum OTP attempts exceeded. Please request a new OTP.",
            )

        if not verification_result["valid"]:
            attempts_remaining = 3 - verification_result["attempts"]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid OTP. {attempts_remaining} attempts remaining.",
            )

        # Check if staff already exists and is verified
        result = await db.execute(
            select(Staff).where(Staff.email == request.email.lower())
        )
        staff = result.scalar_one_or_none()

        if staff:
            # USER EXISTS - Handle different staff states

            # Case 1: Invited staff with temporary password (first time login)
            if staff.temporary_password and staff.invitation_status == "pending":
                # Update invitation status to 'accepted' on first login
                staff.invitation_status = "accepted"
                staff.is_verified = True  # Email is now verified
                await db.commit()

                # Return temporary token for password reset
                temp_token = cms_auth.create_temp_token(staff, "password_reset")
                return CMSVerifySigninResponse(
                    success=True,
                    message="Welcome! Please set up your new password to complete registration.",
                    staffExists=True,
                    accessToken=temp_token,
                    tokenType="temp",
                    expiresIn=30 * 60,  # 30 minutes
                    requiresPasswordReset=True,
                )

            # Case 2: Existing staff who must reset password
            elif staff.must_reset_password:
                temp_token = cms_auth.create_temp_token(staff, "password_reset")
                return CMSVerifySigninResponse(
                    success=True,
                    message="Login successful. Please reset your password.",
                    staffExists=True,
                    accessToken=temp_token,
                    tokenType="temp",
                    expiresIn=30 * 60,  # 30 minutes
                    requiresPasswordReset=True,
                )

            # Case 3: Regular staff login
            elif staff.is_verified and staff.hashed_password:
                # Generate JWT tokens for regular login
                access_token = cms_auth.create_access_token(staff)
                refresh_token = cms_auth.create_refresh_token(staff)

                # Update login tracking and status
                staff.record_login()
                if staff.invitation_status == "accepted":
                    staff.invitation_status = "active"  # Mark as active staff
                await db.commit()

                # Create staff session in Redis
                await cms_auth.create_staff_session(staff, access_token)

                return CMSVerifySigninResponse(
                    success=True,
                    message="Login successful.",
                    staffExists=True,
                    accessToken=access_token,
                    refreshToken=refresh_token,
                    tokenType="bearer",
                    expiresIn=cms_auth.access_token_expire_minutes * 60,
                )

            # Case 4: Unverified staff - should go through registration
            else:
                # Update staff as verified since OTP was verified
                staff.is_verified = True
                await db.commit()

                # Return temp token for registration completion
                temp_token = cms_auth.create_temp_token(staff, "registration")
                return CMSVerifySigninResponse(
                    success=True,
                    message="Email verified. Please complete your registration.",
                    staffExists=False,
                    nextStep="password_setup",
                    tempToken=temp_token,
                )

        else:
            # NEW USER REGISTRATION FLOW
            if not staff:
                # Create new staff record for registration
                staff = Staff(
                    email=request.email.lower(),
                    first_name="",  # Will be filled in step 3
                    last_name="",  # Will be filled in step 3
                    hashed_password="",  # Will be filled in step 2
                    is_verified=True,  # Email is verified
                    invitation_status="pending",
                )
                db.add(staff)
                await db.commit()
                await db.refresh(staff)
            else:
                # Update existing staff
                staff.is_verified = True
                staff.email_verified_at = datetime.now(timezone.utc)
                await db.commit()

            # Generate temporary token for registration steps
            temp_token = cms_auth.create_temp_token(staff, "registration")

            return CMSVerifySigninResponse(
                success=True,
                message="OTP verified successfully. Please complete registration.",
                staffExists=False,
                nextStep="password_setup",
                tempToken=temp_token,
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error verifying sign-in: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        )


@router.post("/refresh-token", response_model=CMSRefreshTokenResponse)
async def refresh_token(
    request: CMSRefreshTokenRequest, db: AsyncSession = Depends(get_db)
):
    """
    Refresh Access Token: Get new access token from refresh token
    - Validates refresh token
    - Checks if staff still exists and is active
    - Returns new access token with updated staff data
    - Automatically logs out deleted/deactivated staffs
    """
    try:
        # Decode refresh token
        payload = cms_auth.decode_token(request.refreshToken)

        # Validate token type
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
        result = await db.execute(select(Staff).where(Staff.uuid == staff_uuid))
        staff = result.scalar_one_or_none()

        # Check if staff still exists and is active
        if not staff:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Staff not found"
            )

        if not staff.is_active:
            # Staff has been deactivated - invalidate all sessions
            await cms_auth.invalidate_staff_sessions(staff.id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Staff account has been deactivated",
            )

        # Optional: Validate staff ID if provided
        if request.cmsStaffId and request.cmsStaffId != staff.id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Staff ID mismatch"
            )

        # Generate new access token with updated staff data
        new_access_token = cms_auth.create_access_token(staff)

        # Update session in Redis
        await cms_auth.create_staff_session(staff, new_access_token)

        return CMSRefreshTokenResponse(
            success=True,
            message="Token refreshed successfully",
            accessToken=new_access_token,
            tokenType="bearer",
            expiresIn=cms_auth.access_token_expire_minutes * 60,
            staff=StaffProfileResponse(
                cmsStaffId=staff.id,
                uuid=str(staff.uuid),
                email=staff.email,
                firstName=staff.first_name,
                lastName=staff.last_name,
                fullName=staff.full_name,
                cmsRole=staff.cms_role,
                collegeId=staff.college_id,
                departmentId=staff.department_id,
                invitationStatus=staff.invitation_status,
                mustResetPassword=staff.must_reset_password,
                isHod=staff.is_hod,
                createdAt=staff.created_at,
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error refreshing token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )


@router.post(
    "/password-setup",
    response_model=CMSRegistrationStepResponse,
    dependencies=[Depends(security)],
)
async def password_setup(
    request: CMSPasswordSetupRequest,
    current_staff: Staff = Depends(get_current_staff_from_temp_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Step 2: Set password for the staff
    - Validate temporary token
    - Hash and store password
    """
    try:
        # Validate staff from temp token matches request email
        if current_staff.email.lower() != request.email.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email mismatch with authenticated staff",
            )

        if not current_staff.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Staff email not verified",
            )

        # Hash password
        hashed_password = cms_auth.get_password_hash(request.password)

        # Update staff password
        current_staff.hashed_password = hashed_password
        current_staff.temporary_password = False
        current_staff.must_reset_password = False
        await db.commit()

        # Generate new temp token for next step
        temp_token = cms_auth.create_temp_token(current_staff, "registration")

        return CMSRegistrationStepResponse(
            success=True,
            message="Password set successfully.",
            nextStep="personal_details",
            tempToken=temp_token,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error setting password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        )


@router.post(
    "/reset-password", response_model=CMSTokenResponse, dependencies=[Depends(security)]
)
async def reset_password(
    request: CMSResetPasswordRequest,
    current_staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Reset Password: For staffs who must reset their password (invited staffs, etc.)
    """
    try:
        # Hash new password
        hashed_password = cms_auth.get_password_hash(request.newPassword)

        # Update staff password
        current_staff.hashed_password = hashed_password
        current_staff.must_reset_password = False
        current_staff.temporary_password = False
        await db.commit()

        # Generate fresh tokens for the staff
        access_token = cms_auth.create_access_token(current_staff)
        refresh_token = cms_auth.create_refresh_token(current_staff)

        # Create staff session in Redis
        await cms_auth.create_staff_session(current_staff, access_token)

        return CMSTokenResponse(
            accessToken=access_token,
            refreshToken=refresh_token,
            tokenType="bearer",
            expiresIn=cms_auth.access_token_expire_minutes * 60,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error resetting password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        )


@router.post(
    "/personal-details",
    response_model=CMSRegistrationStepResponse,
    dependencies=[Depends(security)],
)
async def personal_details(
    request: CMSPersonalDetailsRequest,
    current_staff: Staff = Depends(get_current_staff_from_temp_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Step 3: Set personal details for registration
    """
    try:
        # Update personal details for authenticated staff
        current_staff.first_name = request.firstName
        current_staff.last_name = request.lastName
        await db.commit()

        # Generate new temp token for next step
        temp_token = cms_auth.create_temp_token(current_staff, "registration")

        return CMSRegistrationStepResponse(
            success=True,
            message="Personal details saved successfully.",
            nextStep="college_details",
            tempToken=temp_token,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error saving personal details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        )


@router.post(
    "/college-details",
    response_model=CMSRegistrationStepResponse,
    dependencies=[Depends(security)],
)
async def college_details(
    request: CMSCollegeDetailsRequest,
    current_staff: Staff = Depends(get_current_staff_from_temp_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Step 4: Set college details
    - Create new college record
    - Link staff as principal
    """
    try:
        # Validate staff doesn't already have a college
        if current_staff.college_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Staff already has a college assigned",
            )

        # Create college record
        college = College(
            name=request.name,
            short_name=request.shortName,
            college_reference_id=request.collegeReferenceId,
            phone_number=request.phoneNumber,
            area="",  # Will be filled in next step
            city="",  # Will be filled in next step
            district="",  # Will be filled in next step
            state="",  # Will be filled in next step
            pincode="000000",  # Will be filled in next step
            principal_staff_id=current_staff.id,
        )

        db.add(college)
        await db.commit()
        await db.refresh(college)

        # Update staff with college and role
        current_staff.college_id = college.id
        current_staff.cms_role = "principal"
        current_staff.can_assign_department = True
        await db.commit()

        # Generate new temp token for final step
        temp_token = cms_auth.create_temp_token(current_staff, "registration")

        return CMSRegistrationStepResponse(
            success=True,
            message="College details saved successfully.",
            nextStep="address_details",
            tempToken=temp_token,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error saving college details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        )


@router.post(
    "/address-details",
    response_model=CMSTokenResponse,
    dependencies=[Depends(security)],
)
async def address_details(
    request: CMSAddressDetailsRequest,
    current_staff: Staff = Depends(get_current_staff_from_temp_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Step 5: Set address details (final registration step)
    - Complete college address
    - Generate final JWT tokens
    """
    try:
        # Validate staff has a college
        if current_staff.college_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Staff must have a college before setting address details",
            )

        # Get college
        college_result = await db.execute(
            select(College).where(College.id == current_staff.college_id)
        )
        college = college_result.scalar_one_or_none()

        if not college:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="College not found."
            )

        # Update college address
        college.area = request.area
        college.city = request.city
        college.district = request.district
        college.state = request.state
        college.pincode = request.pincode
        college.latitude = request.latitude
        college.longitude = request.longitude

        # Mark staff as active
        current_staff.invitation_status = "active"

        await db.commit()

        # Generate final JWT tokens
        access_token = cms_auth.create_access_token(current_staff)
        refresh_token = cms_auth.create_refresh_token(current_staff)

        # Create staff session in Redis
        await cms_auth.create_staff_session(current_staff, access_token)

        return CMSTokenResponse(
            accessToken=access_token,
            refreshToken=refresh_token,
            tokenType="bearer",
            expiresIn=cms_auth.access_token_expire_minutes * 60,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error saving address details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        )


@router.post("/logout", dependencies=[Depends(security)])
async def logout(
    current_staff: Staff = Depends(get_current_staff),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Logout staff and invalidate session
    """
    try:
        # Invalidate staff session in Redis
        await cms_auth.invalidate_staff_session(current_staff.id, credentials.credentials)

        return {"success": True, "message": "Logged out successfully"}

    except Exception as e:
        print(f"Error during logout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during logout",
        )


@router.get(
    "/me", response_model=StaffProfileResponse, dependencies=[Depends(security)]
)
async def get_current_staff_profile(current_staff: Staff = Depends(get_current_staff)):
    """
    Get current authenticated staff's profile
    """
    return StaffProfileResponse(
        cmsStaffId=current_staff.id,
        uuid=str(current_staff.uuid),
        email=current_staff.email,
        firstName=current_staff.first_name,
        lastName=current_staff.last_name,
        fullName=current_staff.full_name,
        cmsRole=current_staff.cms_role,
        collegeId=current_staff.college_id,
        departmentId=current_staff.department_id,
        invitationStatus=current_staff.invitation_status,
        mustResetPassword=current_staff.must_reset_password,
        isHod=current_staff.is_hod,
        createdAt=current_staff.created_at,
    )
