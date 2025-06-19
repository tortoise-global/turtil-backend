from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi_pagination import Page, paginate
from fastapi_pagination.ext.sqlalchemy import paginate as sqlalchemy_paginate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import asyncio

from app.database import get_db
from app.models.user import User
from app.models.college import College
from app.models.department import Department
from app.core.cms_auth import cms_auth
from app.core.cms_otp import CMSOTPManager
from app.core.aws import EmailService
from app.core.utils import generate_temporary_password
from app.schemas.cms_auth import (
    CMSSigninRequest, CMSVerifySigninRequest, CMSPasswordSetupRequest,
    CMSPersonalDetailsRequest, CMSCollegeDetailsRequest, CMSAddressDetailsRequest,
    CMSResetPasswordRequest, CMSSigninResponse, CMSTokenResponse,
    CMSVerifySigninResponse, CMSRegistrationStepResponse, CMSUserProfileResponse, CMSErrorResponse
)
from app.schemas.user import UserActivityResponse
from app.schemas.user_management import (
    InviteUserRequest, InviteUserResponse, UserResponse, UserDetailsResponse,
    AssignDepartmentRequest, UpdateUserRoleRequest, UserActionResponse
)
from app.schemas.department import (
    CreateDepartmentRequest, UpdateDepartmentRequest, DepartmentResponse,
    DepartmentWithStatsResponse, DepartmentActionResponse
)

router = APIRouter(prefix="/cms/auth", tags=["CMS Authentication"])

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


async def get_current_cms_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated CMS user from JWT token
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
                await cms_auth.create_user_session(user, refresh_token)
                
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
                    accessToken=temp_token,
                    tokenType="temp",
                    expiresIn=30 * 60
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
        
        # Check if this is an invited user completing password reset
        is_invited_user = user.temporary_password and user.invitation_status == 'accepted'
        
        # Update user
        user.hashed_password = hashed_password
        user.temporary_password = False
        user.must_reset_password = False
        await db.commit()
        
        if is_invited_user:
            # Invited user - they only need password setup, then they're done
            return CMSRegistrationStepResponse(
                success=True,
                message="Password updated successfully. You can now sign in with your new password.",
                nextStep=None,  # No more steps needed for invited users
                tempToken=None
            )
        else:
            # Regular registration flow - continue to personal details
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


@router.post("/personal-details", response_model=CMSRegistrationStepResponse)
async def personal_details(
    request: CMSPersonalDetailsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Step 3: Set personal details
    - Update user personal information
    - Set marketing consent and terms acceptance
    """
    try:
        # This would validate temp token in real implementation
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
    Step 5: Complete registration with address details
    - Update college address
    - Generate final JWT tokens
    - Create user session in Redis
    """
    try:
        # Get current user and college
        result = await db.execute(
            select(User, College).join(College, User.college_id == College.id).where(
                User.cms_role == "principal",
                College.area == ""
            ).order_by(User.created_at.desc())
        )
        user_college = result.first()
        
        if not user_college:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User or college not found."
            )
        
        user, college = user_college
        
        # Update college address
        college.area = request.area
        college.city = request.city
        college.district = request.district
        college.state = request.state
        college.pincode = request.pincode
        college.latitude = request.latitude
        college.longitude = request.longitude
        
        # Complete user registration
        user.invitation_status = "active"
        user.is_active = True
        
        await db.commit()
        
        # Generate JWT tokens
        access_token = cms_auth.create_access_token(user)
        refresh_token = cms_auth.create_refresh_token(user)
        
        # Create user session in Redis
        session_created = await cms_auth.create_user_session(user, refresh_token)
        
        if not session_created:
            print("Warning: Failed to create user session in Redis")
        
        return CMSTokenResponse(
            accessToken=access_token,
            refreshToken=refresh_token,
            tokenType="bearer",
            expiresIn=cms_auth.access_token_expire_minutes * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error completing registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


# Login endpoint removed - now using combined sign-in flow


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_cms_user)
):
    """
    Logout user by clearing Redis session
    """
    try:
        success = await cms_auth.logout_user(current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to logout. Please try again."
            )
        
        return {"success": True, "message": "Logged out successfully."}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error during logout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


@router.get("/me", response_model=CMSUserProfileResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_cms_user)
):
    """
    Get current authenticated user profile
    """
    try:
        user_dict = current_user.to_dict()
        
        return CMSUserProfileResponse(
            cmsUserId=user_dict["cmsUserId"],
            uuid=user_dict["uuid"],
            email=user_dict["email"],
            firstName=user_dict["firstName"],
            lastName=user_dict["lastName"],
            fullName=user_dict["fullName"],
            phoneNumber=user_dict["phoneNumber"],
            cmsRole=user_dict["cmsRole"],
            collegeId=user_dict["collegeId"],
            departmentId=user_dict["departmentId"],
            invitationStatus=user_dict["invitationStatus"],
            mustResetPassword=user_dict["mustResetPassword"],
            createdAt=user_dict["createdAt"]
        )
        
    except Exception as e:
        print(f"Error getting user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


@router.get("/user/{cms_user_id}", response_model=CMSUserProfileResponse)
async def get_user_by_id(
    cms_user_id: int,
    current_user: User = Depends(get_current_cms_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user by CMS user ID (authenticated endpoint)
    Only Principal and College Admin can access other users
    """
    try:
        # Check permissions - only Principal and College Admin can access other users
        if current_user.cms_role not in ["principal", "college_admin"]:
            # Staff and HOD can only access their own profile
            if current_user.id != cms_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to access this user"
                )
        
        # Get user from database
        result = await db.execute(select(User).where(User.id == cms_user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if user belongs to same college (for Principal/College Admin)
        if current_user.cms_role in ["principal", "college_admin"]:
            if user.college_id != current_user.college_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User does not belong to your college"
                )
        
        user_dict = user.to_dict()
        
        return CMSUserProfileResponse(
            cmsUserId=user_dict["cmsUserId"],
            uuid=user_dict["uuid"],
            email=user_dict["email"],
            firstName=user_dict["firstName"],
            lastName=user_dict["lastName"],
            fullName=user_dict["fullName"],
            phoneNumber=user_dict["phoneNumber"],
            cmsRole=user_dict["cmsRole"],
            collegeId=user_dict["collegeId"],
            departmentId=user_dict["departmentId"],
            invitationStatus=user_dict["invitationStatus"],
            mustResetPassword=user_dict["mustResetPassword"],
            createdAt=user_dict["createdAt"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting user by ID: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


# =====================================
# USER INVITATION & MANAGEMENT ENDPOINTS
# =====================================

@router.post("/invite-user", response_model=InviteUserResponse)
async def invite_user(
    request: InviteUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_cms_user)
):
    """
    Invite a new user to the college. Only Principal and College Admin can invite users.
    
    - Creates user with temporary password
    - Sends invitation email with credentials
    - User status: invitation_status='pending'
    """
    try:
        # Check permissions - only Principal and College Admin can invite users
        if current_user.cms_role not in ['principal', 'college_admin']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can invite users"
            )
        
        # Check if user already exists
        result = await db.execute(select(User).where(User.email == request.email))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Generate temporary password
        temporary_password = generate_temporary_password(12)
        hashed_password = cms_auth.hash_password(temporary_password)
        
        # Create new user with invitation fields
        new_user = User(
            email=request.email,
            first_name="",  # Will be filled during onboarding
            last_name="",   # Will be filled during onboarding
            hashed_password=hashed_password,
            is_active=True,
            is_verified=False,  # Will be verified during first login
            college_id=current_user.college_id,
            cms_role='staff',  # Default role, can be changed later
            invitation_status='pending',
            temporary_password=True,
            must_reset_password=True,
            invited_by_cms_user_id=current_user.id
        )
        
        db.add(new_user)
        await db.flush()  # Get the ID without committing
        
        # Get college information for email
        college_result = await db.execute(select(College).where(College.id == current_user.college_id))
        college = college_result.scalar_one()
        
        # Send invitation email
        try:
            await EmailService.send_user_invitation_email(
                email=request.email,
                temporary_password=temporary_password,
                inviter_name=current_user.full_name,
                college_name=college.name
            )
        except Exception as email_error:
            # Rollback user creation if email fails
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send invitation email: {str(email_error)}"
            )
        
        await db.commit()
        await db.refresh(new_user)
        
        return InviteUserResponse(
            success=True,
            message="User invitation sent successfully",
            cmsUserId=new_user.id,
            email=request.email,
            temporaryPassword=temporary_password
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error inviting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while inviting user"
        )


@router.get("/users", response_model=Page[UserResponse])
async def get_users(
    status: Optional[str] = Query(None, description="Filter by approval status: 'approved' or 'unapproved'"),
    department_assigned: Optional[bool] = Query(None, description="Filter by department assignment"),
    department_id: Optional[int] = Query(None, description="Filter by specific department ID"),
    role: Optional[str] = Query(None, description="Filter by CMS role"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_cms_user)
):
    """
    Get paginated list of users with flexible filtering.
    
    Query Parameters:
    - status: 'approved' (accepted/active) or 'unapproved' (pending)
    - department_assigned: true (has department) or false (no department)
    - department_id: specific department ID
    - role: CMS role filter
    - page/size: pagination (handled automatically)
    
    Permissions:
    - Principal/College Admin: Can see all users in college
    - HOD: Can see users in their department
    - Staff: Cannot access this endpoint
    """
    try:
        # Check permissions
        if current_user.cms_role not in ['principal', 'college_admin', 'hod']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view users"
            )
        
        # Build base query - scope to current user's college
        query = select(User).where(User.college_id == current_user.college_id)
        
        # Apply role-based filtering
        if current_user.cms_role == 'hod':
            # HOD can only see users in their department
            query = query.where(User.department_id == current_user.department_id)
        
        # Apply status filter
        if status == 'approved':
            query = query.where(User.invitation_status.in_(['accepted', 'active']))
        elif status == 'unapproved':
            query = query.where(User.invitation_status == 'pending')
        
        # Apply department assignment filter
        if department_assigned is True:
            query = query.where(User.department_id.isnot(None))
        elif department_assigned is False:
            query = query.where(User.department_id.is_(None))
        
        # Apply specific department filter
        if department_id is not None:
            query = query.where(User.department_id == department_id)
        
        # Apply role filter
        if role:
            query = query.where(User.cms_role == role)
        
        # Order by creation date (newest first)
        query = query.order_by(User.created_at.desc())
        
        # Use SQLAlchemy pagination for efficient database queries
        paginated_result = await sqlalchemy_paginate(db, query)
        
        # Convert users to response format
        user_responses = []
        for user in paginated_result.items:
            user_dict = user.to_dict()
            user_responses.append(UserResponse(**user_dict))
        
        # Return paginated response
        return Page(
            items=user_responses,
            total=paginated_result.total,
            page=paginated_result.page,
            size=paginated_result.size,
            pages=paginated_result.pages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching users"
        )


@router.put("/user/{user_id}/assign-department", response_model=UserActionResponse)
async def assign_user_to_department(
    user_id: int,
    request: AssignDepartmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_cms_user)
):
    """
    Assign a user to a department. Only Principal and College Admin can assign departments.
    """
    try:
        # Check permissions
        if current_user.cms_role not in ['principal', 'college_admin']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can assign departments"
            )
        
        # Get user
        result = await db.execute(
            select(User).where(
                and_(User.id == user_id, User.college_id == current_user.college_id)
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Validate department exists and belongs to same college
        dept_result = await db.execute(
            select(Department).where(
                and_(Department.id == request.departmentId, Department.college_id == current_user.college_id)
            )
        )
        department = dept_result.scalar_one_or_none()
        
        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found"
            )
        
        # Update user's department
        user.department_id = request.departmentId
        await db.commit()
        
        return UserActionResponse(
            success=True,
            message=f"User assigned to {department.name} department successfully",
            cmsUserId=user_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error assigning user to department: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while assigning department"
        )


@router.put("/user/{user_id}/remove-department", response_model=UserActionResponse)
async def remove_user_from_department(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_cms_user)
):
    """
    Remove a user from their current department. Only Principal and College Admin can do this.
    """
    try:
        # Check permissions
        if current_user.cms_role not in ['principal', 'college_admin']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can remove department assignments"
            )
        
        # Get user
        result = await db.execute(
            select(User).where(
                and_(User.id == user_id, User.college_id == current_user.college_id)
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Remove department assignment
        user.department_id = None
        await db.commit()
        
        return UserActionResponse(
            success=True,
            message="User removed from department successfully",
            cmsUserId=user_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error removing user from department: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while removing department assignment"
        )


@router.put("/user/{user_id}/role", response_model=UserActionResponse)
async def update_user_role(
    user_id: int,
    request: UpdateUserRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_cms_user)
):
    """
    Update a user's CMS role. Only Principal and College Admin can update roles.
    """
    try:
        # Check permissions
        if current_user.cms_role not in ['principal', 'college_admin']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can update user roles"
            )
        
        # Get user
        result = await db.execute(
            select(User).where(
                and_(User.id == user_id, User.college_id == current_user.college_id)
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prevent changing principal role (only one principal per college)
        if user.cms_role == 'principal' and request.role != 'principal':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change principal role. Transfer principal role first."
            )
        
        # Prevent multiple principals
        if request.role == 'principal' and user.cms_role != 'principal':
            principal_result = await db.execute(
                select(User).where(
                    and_(User.college_id == current_user.college_id, User.cms_role == 'principal')
                )
            )
            existing_principal = principal_result.scalar_one_or_none()
            if existing_principal:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="College already has a principal. Transfer role from existing principal first."
                )
        
        # Update role
        old_role = user.cms_role
        user.cms_role = request.role
        await db.commit()
        
        return UserActionResponse(
            success=True,
            message=f"User role updated from {old_role} to {request.role}",
            cmsUserId=user_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error updating user role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating user role"
        )


@router.delete("/user/{user_id}", response_model=UserActionResponse)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_cms_user)
):
    """
    Delete a user. Only Principal and College Admin can delete users.
    Cannot delete the principal or yourself.
    """
    try:
        # Check permissions
        if current_user.cms_role not in ['principal', 'college_admin']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can delete users"
            )
        
        # Prevent self-deletion
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        # Get user
        result = await db.execute(
            select(User).where(
                and_(User.id == user_id, User.college_id == current_user.college_id)
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prevent deleting principal
        if user.cms_role == 'principal':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete principal account"
            )
        
        # Delete user
        await db.delete(user)
        await db.commit()
        
        return UserActionResponse(
            success=True,
            message="User deleted successfully",
            cmsUserId=user_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error deleting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting user"
        )


# =====================================
# DEPARTMENT MANAGEMENT ENDPOINTS
# =====================================

@router.get("/departments", response_model=Page[DepartmentWithStatsResponse])
async def get_departments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_cms_user)
):
    """
    Get paginated list of departments with user statistics.
    All authenticated users can view departments in their college.
    """
    try:
        # Build query for departments in current user's college
        query = select(Department).where(Department.college_id == current_user.college_id)
        query = query.order_by(Department.name)
        
        # Get paginated departments
        paginated_result = await sqlalchemy_paginate(db, query)
        
        # Add user statistics for each department
        department_responses = []
        for department in paginated_result.items:
            # Count total users in department
            total_users_result = await db.execute(
                select(func.count(User.id)).where(User.department_id == department.id)
            )
            total_users = total_users_result.scalar() or 0
            
            # Count active users in department
            active_users_result = await db.execute(
                select(func.count(User.id)).where(
                    and_(User.department_id == department.id, User.is_active == True)
                )
            )
            active_users = active_users_result.scalar() or 0
            
            dept_dict = department.to_dict()
            department_responses.append(DepartmentWithStatsResponse(
                **dept_dict,
                totalUsers=total_users,
                activeUsers=active_users
            ))
        
        return Page(
            items=department_responses,
            total=paginated_result.total,
            page=paginated_result.page,
            size=paginated_result.size,
            pages=paginated_result.pages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting departments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching departments"
        )


@router.post("/departments", response_model=DepartmentActionResponse)
async def create_department(
    request: CreateDepartmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_cms_user)
):
    """
    Create a new department. Only Principal and College Admin can create departments.
    """
    try:
        # Check permissions
        if current_user.cms_role not in ['principal', 'college_admin']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can create departments"
            )
        
        # Check if department with same code already exists in college
        existing_dept_result = await db.execute(
            select(Department).where(
                and_(Department.code == request.code, Department.college_id == current_user.college_id)
            )
        )
        existing_dept = existing_dept_result.scalar_one_or_none()
        
        if existing_dept:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Department with code '{request.code}' already exists"
            )
        
        # Create new department
        new_department = Department(
            name=request.name,
            code=request.code,
            description=request.description,
            college_id=current_user.college_id
        )
        
        db.add(new_department)
        await db.commit()
        await db.refresh(new_department)
        
        return DepartmentActionResponse(
            success=True,
            message=f"Department '{request.name}' created successfully",
            departmentId=new_department.id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error creating department: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating department"
        )


@router.put("/departments/{department_id}", response_model=DepartmentActionResponse)
async def update_department(
    department_id: int,
    request: UpdateDepartmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_cms_user)
):
    """
    Update a department. Only Principal and College Admin can update departments.
    """
    try:
        # Check permissions
        if current_user.cms_role not in ['principal', 'college_admin']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can update departments"
            )
        
        # Get department
        result = await db.execute(
            select(Department).where(
                and_(Department.id == department_id, Department.college_id == current_user.college_id)
            )
        )
        department = result.scalar_one_or_none()
        
        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found"
            )
        
        # Check if new code conflicts with existing department
        if request.code and request.code != department.code:
            existing_dept_result = await db.execute(
                select(Department).where(
                    and_(
                        Department.code == request.code,
                        Department.college_id == current_user.college_id,
                        Department.id != department_id
                    )
                )
            )
            existing_dept = existing_dept_result.scalar_one_or_none()
            
            if existing_dept:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Department with code '{request.code}' already exists"
                )
        
        # Validate HOD if provided
        if request.hodCmsUserId is not None:
            hod_result = await db.execute(
                select(User).where(
                    and_(
                        User.id == request.hodCmsUserId,
                        User.college_id == current_user.college_id,
                        User.is_active == True
                    )
                )
            )
            hod_user = hod_result.scalar_one_or_none()
            
            if not hod_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="HOD user not found or inactive"
                )
        
        # Update department fields
        if request.name is not None:
            department.name = request.name
        if request.code is not None:
            department.code = request.code
        if request.description is not None:
            department.description = request.description
        if request.hodCmsUserId is not None:
            department.hod_cms_user_id = request.hodCmsUserId
        
        await db.commit()
        
        return DepartmentActionResponse(
            success=True,
            message=f"Department '{department.name}' updated successfully",
            departmentId=department_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error updating department: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating department"
        )


@router.delete("/departments/{department_id}", response_model=DepartmentActionResponse)
async def delete_department(
    department_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_cms_user)
):
    """
    Delete a department. Only Principal and College Admin can delete departments.
    Cannot delete department if it has assigned users.
    """
    try:
        # Check permissions
        if current_user.cms_role not in ['principal', 'college_admin']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can delete departments"
            )
        
        # Get department
        result = await db.execute(
            select(Department).where(
                and_(Department.id == department_id, Department.college_id == current_user.college_id)
            )
        )
        department = result.scalar_one_or_none()
        
        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found"
            )
        
        # Check if department has assigned users
        users_result = await db.execute(
            select(func.count(User.id)).where(User.department_id == department_id)
        )
        user_count = users_result.scalar() or 0
        
        if user_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete department. {user_count} users are assigned to this department. Remove users first."
            )
        
        # Delete department
        department_name = department.name
        await db.delete(department)
        await db.commit()
        
        return DepartmentActionResponse(
            success=True,
            message=f"Department '{department_name}' deleted successfully",
            departmentId=department_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error deleting department: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting department"
        )