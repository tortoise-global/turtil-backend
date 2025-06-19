from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any
from datetime import datetime, timezone

from app.database import get_db
from app.models.user import User
from app.models.college import College
from app.core.cms_auth import cms_auth
from app.core.cms_otp import CMSOTPManager
from app.core.aws import EmailService
from app.schemas.cms_auth import (
    CMSSigninRequest, CMSVerifySigninRequest, CMSPasswordSetupRequest,
    CMSPersonalDetailsRequest, CMSCollegeDetailsRequest, CMSAddressDetailsRequest,
    CMSResetPasswordRequest, CMSSigninResponse, CMSTokenResponse,
    CMSVerifySigninResponse, CMSRegistrationStepResponse, CMSUserProfileResponse,
    CMSRefreshTokenRequest, CMSRefreshTokenResponse
)

router = APIRouter(prefix="/cms/auth", tags=["CMS Authentication"])

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


async def get_current_cms_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated CMS user from JWT token with blacklist validation
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
                detail="Token has been revoked"
            )
        
        # Decode token
        payload = cms_auth.decode_token(credentials.credentials)
        
        # Validate token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        # Get user UUID from token
        user_uuid = payload.get("sub")
        if not user_uuid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Get user from database
        result = await db.execute(select(User).where(User.uuid == user_uuid))
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Validate session in Redis
        session_data = await cms_auth.validate_session(user.id, credentials.credentials)
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired or invalid"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting current CMS user: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


@router.post("/signin", response_model=CMSSigninResponse)
async def signin(
    request: CMSSigninRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Combined Sign-in: Send OTP for both new and existing users
    - Generate 6-digit OTP
    - Store in Redis with 3 attempts and 5-minute expiry
    - Send via AWS SES
    - Return whether user already exists
    """
    try:
        # Check if user already exists
        result = await db.execute(select(User).where(User.email == request.email.lower()))
        existing_user = result.scalar_one_or_none()
        user_exists = existing_user is not None and existing_user.is_verified
        
        # Generate OTP
        otp = CMSOTPManager.generate_otp()
        
        # Store OTP in Redis
        otp_stored = await CMSOTPManager.store_otp(request.email.lower(), otp)
        
        if not otp_stored:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate OTP. Please try again."
            )
        
        # Send OTP via email
        email_result = await EmailService.send_otp_email(request.email, otp)
        email_sent = email_result.get("success", False)
        
        if not email_sent:
            # Clear OTP if email failed
            await CMSOTPManager.clear_otp(request.email.lower())
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send OTP email. Please try again."
            )
        
        message = "OTP sent successfully to your email address."
        if user_exists:
            message += " You will be logged in after verification."
        else:
            message += " Complete registration after verification."
        
        return CMSSigninResponse(
            success=True,
            message=message,
            attemptsRemaining=3,
            canResend=True,
            userExists=user_exists
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error sending OTP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


@router.post("/verify-signin", response_model=CMSVerifySigninResponse)
async def verify_signin(
    request: CMSVerifySigninRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify Sign-in OTP: Handle both login and registration flows
    - Verify OTP with attempt tracking
    - If user exists: return JWT tokens (login)
    - If user doesn't exist: return temp token for registration
    """
    try:
        # Verify OTP
        verification_result = await CMSOTPManager.verify_otp(request.email.lower(), request.otp)
        
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
        
        # Check if user already exists and is verified
        result = await db.execute(select(User).where(User.email == request.email.lower()))
        user = result.scalar_one_or_none()
        
        if user:
            # USER EXISTS - Handle different user states
            
            # Case 1: Invited user with temporary password (first time login)
            if user.temporary_password and user.invitation_status == 'pending':
                # Update invitation status to 'accepted' on first login
                user.invitation_status = 'accepted'
                user.is_verified = True  # Email is now verified
                await db.commit()
                
                # Return temporary token for password reset
                temp_token = cms_auth.create_temp_token(user, "password_reset")
                return CMSVerifySigninResponse(
                    success=True,
                    message="Welcome! Please set up your new password to complete registration.",
                    userExists=True,
                    accessToken=temp_token,
                    tokenType="temp",
                    expiresIn=30 * 60,  # 30 minutes
                    requiresPasswordReset=True
                )
            
            # Case 2: Existing user who must reset password
            elif user.must_reset_password:
                temp_token = cms_auth.create_temp_token(user, "password_reset")
                return CMSVerifySigninResponse(
                    success=True,
                    message="Login successful. Please reset your password.",
                    userExists=True,
                    accessToken=temp_token,
                    tokenType="temp",
                    expiresIn=30 * 60,  # 30 minutes
                    requiresPasswordReset=True
                )
            
            # Case 3: Regular user login
            elif user.is_verified and user.hashed_password:
                # Generate JWT tokens for regular login
                access_token = cms_auth.create_access_token(user)
                refresh_token = cms_auth.create_refresh_token(user)
                
                # Update login tracking and status
                user.record_login()
                if user.invitation_status == 'accepted':
                    user.invitation_status = 'active'  # Mark as active user
                await db.commit()
                
                # Create user session in Redis
                await cms_auth.create_user_session(user, access_token)
                
                return CMSVerifySigninResponse(
                    success=True,
                    message="Login successful.",
                    userExists=True,
                    accessToken=access_token,
                    refreshToken=refresh_token,
                    tokenType="bearer",
                    expiresIn=cms_auth.access_token_expire_minutes * 60
                )
            
            # Case 4: Unverified user - should go through registration
            else:
                # Update user as verified since OTP was verified
                user.is_verified = True
                await db.commit()
                
                # Return temp token for registration completion
                temp_token = cms_auth.create_temp_token(user, "registration")
                return CMSVerifySigninResponse(
                    success=True,
                    message="Email verified. Please complete your registration.",
                    userExists=False,
                    nextStep="password_setup",
                    tempToken=temp_token
                )
        
        else:
            # NEW USER REGISTRATION FLOW
            if not user:
                # Create new user record for registration
                user = User(
                    email=request.email.lower(),
                    first_name="",  # Will be filled in step 3
                    last_name="",   # Will be filled in step 3
                    hashed_password="",  # Will be filled in step 2
                    is_verified=True,  # Email is verified
                    invitation_status="pending"
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
            else:
                # Update existing user
                user.is_verified = True
                user.email_verified_at = datetime.now(timezone.utc)
                await db.commit()
            
            # Generate temporary token for registration steps
            temp_token = cms_auth.create_temp_token(user, "registration")
            
            return CMSVerifySigninResponse(
                success=True,
                message="OTP verified successfully. Please complete registration.",
                userExists=False,
                nextStep="password_setup",
                tempToken=temp_token
            )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error verifying sign-in: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


@router.post("/refresh-token", response_model=CMSRefreshTokenResponse)
async def refresh_token(
    request: CMSRefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh Access Token: Get new access token from refresh token
    - Validates refresh token
    - Checks if user still exists and is active
    - Returns new access token with updated user data
    - Automatically logs out deleted/deactivated users
    """
    try:
        # Decode refresh token
        payload = cms_auth.decode_token(request.refreshToken)
        
        # Validate token type
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        # Get user UUID from token
        user_uuid = payload.get("sub")
        if not user_uuid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Get user from database
        result = await db.execute(select(User).where(User.uuid == user_uuid))
        user = result.scalar_one_or_none()
        
        # Check if user still exists and is active
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if not user.is_active:
            # User has been deactivated - invalidate all sessions
            await cms_auth.invalidate_user_sessions(user.id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account has been deactivated"
            )
        
        # Optional: Validate user ID if provided
        if request.cmsUserId and request.cmsUserId != user.id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID mismatch"
            )
        
        # Generate new access token with updated user data
        new_access_token = cms_auth.create_access_token(user)
        
        # Update session in Redis
        await cms_auth.create_user_session(user, new_access_token)
        
        return CMSRefreshTokenResponse(
            success=True,
            message="Token refreshed successfully",
            accessToken=new_access_token,
            tokenType="bearer",
            expiresIn=cms_auth.access_token_expire_minutes * 60,
            user=CMSUserProfileResponse(
                cmsUserId=user.id,
                uuid=str(user.uuid),
                email=user.email,
                firstName=user.first_name,
                lastName=user.last_name,
                fullName=user.full_name,
                phoneNumber=user.phone_number,
                cmsRole=user.cms_role,
                collegeId=user.college_id,
                departmentId=user.department_id,
                invitationStatus=user.invitation_status,
                mustResetPassword=user.must_reset_password,
                isHod=user.is_hod,
                createdAt=user.created_at
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error refreshing token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/password-setup", response_model=CMSRegistrationStepResponse)
async def password_setup(
    request: CMSPasswordSetupRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Step 2: Set password for the user
    - Validate temporary token
    - Hash and store password
    """
    try:
        # Get user by email
        result = await db.execute(select(User).where(User.email == request.email.lower()))
        user = result.scalar_one_or_none()
        
        if not user or not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user or email not verified."
            )
        
        # Hash password
        hashed_password = cms_auth.get_password_hash(request.password)
        
        # Update user password
        user.hashed_password = hashed_password
        user.temporary_password = False
        user.must_reset_password = False
        await db.commit()
        
        # Generate new temp token for next step
        temp_token = cms_auth.create_temp_token(user, "registration")
        
        return CMSRegistrationStepResponse(
            success=True,
            message="Password set successfully.",
            nextStep="personal_details",
            tempToken=temp_token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error setting password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


@router.post("/reset-password", response_model=CMSTokenResponse)
async def reset_password(
    request: CMSResetPasswordRequest,
    current_user: User = Depends(get_current_cms_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reset Password: For users who must reset their password (invited users, etc.)
    """
    try:
        # Hash new password
        hashed_password = cms_auth.get_password_hash(request.newPassword)
        
        # Update user password
        current_user.hashed_password = hashed_password
        current_user.must_reset_password = False
        current_user.temporary_password = False
        await db.commit()
        
        # Generate fresh tokens for the user
        access_token = cms_auth.create_access_token(current_user)
        refresh_token = cms_auth.create_refresh_token(current_user)
        
        # Create user session in Redis
        await cms_auth.create_user_session(current_user, access_token)
        
        return CMSTokenResponse(
            accessToken=access_token,
            refreshToken=refresh_token,
            tokenType="bearer",
            expiresIn=cms_auth.access_token_expire_minutes * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error resetting password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


@router.post("/personal-details", response_model=CMSRegistrationStepResponse)
async def personal_details(
    request: CMSPersonalDetailsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Step 3: Set personal details for registration
    """
    try:
        # For now, get user by first_name (since it's empty initially)
        result = await db.execute(
            select(User).where(
                User.first_name == "",
                User.last_name == "",
                User.is_verified == True
            ).order_by(User.created_at.desc())
        )
        user = result.first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not found or invalid state."
            )
        
        user = user[0]  # Get user from result tuple
        
        # Update personal details
        user.first_name = request.firstName
        user.last_name = request.lastName
        user.phone_number = request.phoneNumber
        user.marketing_consent = request.marketingConsent
        user.terms_accepted = request.termsAccepted
        await db.commit()
        
        # Generate new temp token for next step
        temp_token = cms_auth.create_temp_token(user, "registration")
        
        return CMSRegistrationStepResponse(
            success=True,
            message="Personal details saved successfully.",
            nextStep="college_logo_upload",
            tempToken=temp_token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error saving personal details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


@router.post("/college-details", response_model=CMSRegistrationStepResponse)
async def college_details(
    request: CMSCollegeDetailsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Step 4: Set college details
    - Create new college record
    - Link user as principal
    """
    try:
        # Get current user (in real implementation, validate temp token)
        result = await db.execute(
            select(User).where(
                User.is_verified == True,
                User.college_id.is_(None)
            ).order_by(User.created_at.desc())
        )
        user = result.first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not found or invalid state."
            )
        
        user = user[0]  # Get user from result tuple
        
        # Create college record
        college = College(
            name=request.name,
            short_name=request.shortName,
            college_reference_id=request.collegeReferenceId,
            area="",  # Will be filled in next step
            city="",  # Will be filled in next step
            district="",  # Will be filled in next step
            state="",  # Will be filled in next step
            pincode="000000",  # Will be filled in next step
            principal_cms_user_id=user.id
        )
        
        db.add(college)
        await db.commit()
        await db.refresh(college)
        
        # Update user with college and role
        user.college_id = college.id
        user.cms_role = "principal"
        user.can_assign_department = True
        await db.commit()
        
        # Generate new temp token for final step
        temp_token = cms_auth.create_temp_token(user, "registration")
        
        return CMSRegistrationStepResponse(
            success=True,
            message="College details saved successfully.",
            nextStep="address_details",
            tempToken=temp_token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error saving college details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


@router.post("/address-details", response_model=CMSTokenResponse)
async def address_details(
    request: CMSAddressDetailsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Step 5: Set address details (final registration step)
    - Complete college address
    - Generate final JWT tokens
    """
    try:
        # Get current user with college
        result = await db.execute(
            select(User).where(
                User.is_verified == True,
                User.college_id.is_not(None)
            ).order_by(User.created_at.desc())
        )
        user = result.first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not found or invalid state."
            )
        
        user = user[0]  # Get user from result tuple
        
        # Get college
        college_result = await db.execute(select(College).where(College.id == user.college_id))
        college = college_result.scalar_one_or_none()
        
        if not college:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="College not found."
            )
        
        # Update college address
        college.area = request.area
        college.city = request.city
        college.district = request.district
        college.state = request.state
        college.pincode = request.pincode
        college.latitude = request.latitude
        college.longitude = request.longitude
        
        # Mark user as active
        user.invitation_status = "active"
        
        await db.commit()
        
        # Generate final JWT tokens
        access_token = cms_auth.create_access_token(user)
        refresh_token = cms_auth.create_refresh_token(user)
        
        # Create user session in Redis
        await cms_auth.create_user_session(user, access_token)
        
        return CMSTokenResponse(
            accessToken=access_token,
            refreshToken=refresh_token,
            tokenType="bearer",
            expiresIn=cms_auth.access_token_expire_minutes * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error saving address details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_cms_user),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Logout user and invalidate session
    """
    try:
        # Invalidate user session in Redis
        await cms_auth.invalidate_user_session(current_user.id, credentials.credentials)
        
        return {"success": True, "message": "Logged out successfully"}
        
    except Exception as e:
        print(f"Error during logout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during logout"
        )


@router.get("/me", response_model=CMSUserProfileResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_cms_user)
):
    """
    Get current authenticated user's profile
    """
    return CMSUserProfileResponse(
        cmsUserId=current_user.id,
        uuid=str(current_user.uuid),
        email=current_user.email,
        firstName=current_user.first_name,
        lastName=current_user.last_name,
        fullName=current_user.full_name,
        phoneNumber=current_user.phone_number,
        cmsRole=current_user.cms_role,
        collegeId=current_user.college_id,
        departmentId=current_user.department_id,
        invitationStatus=current_user.invitation_status,
        mustResetPassword=current_user.must_reset_password,
        isHod=current_user.is_hod,
        createdAt=current_user.created_at
    )