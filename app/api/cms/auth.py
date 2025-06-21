from fastapi import APIRouter, HTTPException, status, Depends, Response, Request, Cookie
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
    CMSProfileSetupRequest,
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
                
                # Refresh staff data
                await db.refresh(staff)

                # Generate JWT tokens for invited staff (they need password reset)
                access_token = cms_auth.create_access_token(staff)
                refresh_token = cms_auth.create_refresh_token(staff)
                
                # Create staff session in Redis
                await cms_auth.create_staff_session(staff, access_token)

                return CMSVerifySigninResponse(
                    success=True,
                    message="Welcome! Please set up your new password to complete registration.",
                    staffExists=True,
                    accessToken=access_token,
                    refreshToken=refresh_token,
                    tokenType="bearer",
                    expiresIn=cms_auth.access_token_expire_minutes * 60,
                )

            # Case 2: Existing staff who must reset password
            elif staff.must_reset_password:
                # Update verification status
                staff.is_verified = True
                await db.commit()
                
                # Refresh staff data
                await db.refresh(staff)

                # Generate JWT tokens (they will have requiresPasswordReset flag)
                access_token = cms_auth.create_access_token(staff)
                refresh_token = cms_auth.create_refresh_token(staff)
                
                # Create staff session in Redis
                await cms_auth.create_staff_session(staff, access_token)

                return CMSVerifySigninResponse(
                    success=True,
                    message="Login successful. Please reset your password.",
                    staffExists=True,
                    accessToken=access_token,
                    refreshToken=refresh_token,
                    tokenType="bearer",
                    expiresIn=cms_auth.access_token_expire_minutes * 60,
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
                
                # Refresh staff data
                await db.refresh(staff)

                # Generate JWT tokens for registration flow
                access_token = cms_auth.create_access_token(staff)
                refresh_token = cms_auth.create_refresh_token(staff)
                
                # Create staff session in Redis
                await cms_auth.create_staff_session(staff, access_token)

                return CMSVerifySigninResponse(
                    success=True,
                    message="Email verified. Please complete your registration.",
                    staffExists=True,  # User exists but needs registration
                    accessToken=access_token,
                    refreshToken=refresh_token,
                    tokenType="bearer",
                    expiresIn=cms_auth.access_token_expire_minutes * 60,
                )

        else:
            # NEW USER REGISTRATION FLOW
            # Create new staff record for registration
            staff = Staff(
                email=request.email.lower(),
                full_name="",  # Will be filled in personal details step
                hashed_password="",  # Will be filled in password setup step
                is_verified=True,  # Email is verified
                invitation_status="pending",
            )
            db.add(staff)
            await db.commit()
            await db.refresh(staff)

            # Generate JWT tokens for new user registration flow
            access_token = cms_auth.create_access_token(staff)
            refresh_token = cms_auth.create_refresh_token(staff)
            
            # Create staff session in Redis
            await cms_auth.create_staff_session(staff, access_token)

            return CMSVerifySigninResponse(
                success=True,
                message="OTP verified successfully. Please complete registration.",
                staffExists=True,  # User exists but needs complete registration
                accessToken=access_token,
                refreshToken=refresh_token,
                tokenType="bearer",
                expiresIn=cms_auth.access_token_expire_minutes * 60,
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
        if request.staffId and request.staffId != staff.id:
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
                staffId=staff.id,
                uuid=str(staff.uuid),
                email=staff.email,
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
    "/setup-profile",
    response_model=CMSTokenResponse,
    dependencies=[Depends(security)],
)
async def setup_profile(
    request: CMSProfileSetupRequest,
    current_staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Set up staff profile during registration - password and full name
    - Hash and store password
    - Update staff's full name (username)
    Returns updated JWT tokens with new registration state
    """
    try:
        # Validate staff from JWT matches request email
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

        # Update staff password and profile
        current_staff.hashed_password = hashed_password
        current_staff.full_name = request.fullName
        current_staff.temporary_password = False
        current_staff.must_reset_password = False
        
        # For Principal role, also update college contact information
        if current_staff.cms_role == "principal":
            # Get or create college for this staff
            if not current_staff.college_id:
                # Create college if it doesn't exist
                college = College(
                    name="",  # Will be filled in college-details step
                    short_name="",  # Will be filled in college-details step
                    college_reference_id="",  # Will be filled in college-details step
                    area="",  # Will be filled in college-address step
                    city="",  # Will be filled in college-address step
                    district="",  # Will be filled in college-address step
                    state="",  # Will be filled in college-address step
                    pincode="000000",  # Will be filled in college-address step
                    principal_cms_staff_id=current_staff.id,
                    contact_number=request.contactNumber,
                    contact_staff_id=current_staff.id,
                )
                db.add(college)
                await db.commit()
                await db.refresh(college)
                
                # Update staff with college
                current_staff.college_id = college.id
            else:
                # Update existing college contact info
                result = await db.execute(
                    select(College).where(College.id == current_staff.college_id)
                )
                college = result.scalar_one_or_none()
                if college:
                    college.contact_number = request.contactNumber
                    college.contact_staff_id = current_staff.id
        
        await db.commit()
        
        # Refresh staff data to get updated state
        await db.refresh(current_staff)

        # Generate new JWT tokens with updated registration state
        token_data = await cms_auth.refresh_user_tokens(current_staff)

        return CMSTokenResponse(
            accessToken=token_data["accessToken"],
            refreshToken=token_data["refreshToken"],
            tokenType=token_data["tokenType"],
            expiresIn=token_data["expiresIn"],
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error setting up profile: {e}")
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


# HTTP-only Cookie-based Authentication Endpoints

@router.post("/signin-cookie", response_model=CMSSigninResponse)
async def signin_cookie(
    request: CMSSigninRequest, 
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Cookie-based Sign-in: Send OTP and prepare for cookie authentication
    Same as regular signin but prepares response for cookie-based flow
    """
    # Use the same logic as regular signin
    return await signin(request, db)


@router.post("/verify-signin-cookie", response_model=CMSVerifySigninResponse)
async def verify_signin_cookie(
    request: CMSVerifySigninRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify Sign-in OTP and set HTTP-only cookies
    Same as regular verify-signin but sets cookies instead of returning tokens
    """
    # Get the regular response first
    signin_response = await verify_signin(request, db)
    
    if signin_response.success and signin_response.accessToken and signin_response.refreshToken:
        # Set HTTP-only cookies
        response.set_cookie(
            key="access_token",
            value=signin_response.accessToken,
            httponly=True,
            secure=True,  # Use HTTPS in production
            samesite="strict",
            max_age=signin_response.expiresIn,
            path="/",
        )
        
        response.set_cookie(
            key="refresh_token", 
            value=signin_response.refreshToken,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=cms_auth.refresh_token_expire_days * 24 * 60 * 60,  # Convert days to seconds
            path="/",
        )
        
        # Return response without tokens (they're in cookies now)
        return CMSVerifySigninResponse(
            success=signin_response.success,
            message=signin_response.message,
            staffExists=signin_response.staffExists,
            tokenType="bearer",
            expiresIn=signin_response.expiresIn,
        )
    
    return signin_response


@router.get("/token")
async def get_access_token(
    access_token: str = Cookie(None, alias="access_token"),
    refresh_token: str = Cookie(None, alias="refresh_token")
):
    """
    Get current access token from HTTP-only cookie
    Used by frontend to retrieve token for API calls
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No access token found in cookies"
        )
    
    try:
        # Verify token is still valid
        payload = cms_auth.decode_token(access_token)
        
        return {
            "accessToken": access_token,
            "tokenType": "bearer",
            "expiresIn": cms_auth.access_token_expire_minutes * 60,
        }
    except HTTPException:
        # Token is invalid/expired
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token is invalid or expired"
        )


@router.post("/refresh-cookie")
async def refresh_token_cookie(
    response: Response,
    refresh_token: str = Cookie(None, alias="refresh_token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token from cookie
    Sets new access token in HTTP-only cookie
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token found in cookies"
        )
    
    # Use existing refresh token logic
    refresh_request = CMSRefreshTokenRequest(refreshToken=refresh_token)
    refresh_response = await refresh_token(refresh_request, db)
    
    if refresh_response.success and refresh_response.accessToken:
        # Set new access token in cookie
        response.set_cookie(
            key="access_token",
            value=refresh_response.accessToken,
            httponly=True,
            secure=True,
            samesite="strict", 
            max_age=refresh_response.expiresIn,
            path="/",
        )
        
        return {
            "accessToken": refresh_response.accessToken,
            "tokenType": refresh_response.tokenType,
            "expiresIn": refresh_response.expiresIn,
        }
    
    # If refresh failed, clear cookies
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Failed to refresh token"
    )


@router.post("/logout-cookie")
async def logout_cookie(
    response: Response,
    access_token: str = Cookie(None, alias="access_token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout and clear HTTP-only cookies
    """
    # If we have an access token, perform server-side logout
    if access_token:
        try:
            # Decode token to get staff info
            payload = cms_auth.decode_token(access_token)
            staff_uuid = payload.get("sub")
            
            if staff_uuid:
                # Get staff from database
                result = await db.execute(select(Staff).where(Staff.uuid == staff_uuid))
                staff = result.scalar_one_or_none()
                
                if staff:
                    # Invalidate session
                    await cms_auth.invalidate_staff_session(staff.id, access_token)
        except Exception as e:
            print(f"Error during cookie logout: {e}")
    
    # Clear cookies regardless of server-side logout success
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    
    return {"success": True, "message": "Logged out successfully"}


# Helper function to get current staff from cookies
async def get_current_staff_from_cookie(
    access_token: str = Cookie(None, alias="access_token"),
    db: AsyncSession = Depends(get_db)
) -> Staff:
    """
    Get current authenticated staff from HTTP-only cookie
    Alternative to get_current_staff for cookie-based auth
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Check if token is blacklisted
        is_blacklisted = await cms_auth.is_token_blacklisted(access_token)
        if is_blacklisted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )

        # Decode token
        payload = cms_auth.decode_token(access_token)

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
        session_data = await cms_auth.validate_session(staff.id, access_token)
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired or invalid",
            )

        return staff

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting current CMS staff from cookie: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
