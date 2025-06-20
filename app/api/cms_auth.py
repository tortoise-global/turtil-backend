from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate as sqlalchemy_paginate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import Optional
from datetime import datetime, timezone

from app.database import get_db
from app.models.staff import Staff
from app.models.college import College
from app.models.department import Department
from app.core.cms_auth import cms_auth
from app.core.cms_otp import CMSOTPManager
from app.core.aws import EmailService
from app.core.utils import generate_temporary_password
from app.schemas.cms_auth import (
    CMSSigninRequest,
    CMSVerifySigninRequest,
    CMSPasswordSetupRequest,
    CMSPersonalDetailsRequest,
    CMSCollegeDetailsRequest,
    CMSAddressDetailsRequest,
    CMSSigninResponse,
    CMSTokenResponse,
    CMSVerifySigninResponse,
    CMSRegistrationStepResponse,
    StaffProfileResponse,
)
from app.schemas.staff_management import (
    InviteStaffRequest,
    InviteStaffResponse,
    StaffResponse,
    AssignDepartmentRequest,
    UpdateStaffRoleRequest,
    StaffActionResponse,
)
from app.schemas.department import (
    CreateDepartmentRequest,
    UpdateDepartmentRequest,
    DepartmentWithStatsResponse,
    DepartmentActionResponse,
)

router = APIRouter(prefix="/cms/auth", tags=["CMS Authentication"])

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


async def get_current_staff(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Staff:
    """
    Get current authenticated CMS staff from JWT token
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


@router.post("/signin", response_model=CMSSigninResponse)
async def signin(request: CMSSigninRequest, db: AsyncSession = Depends(get_db)):
    """
    Combined Sign-in: Send OTP for both new and existing staff
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
            # STAFF EXISTS - Handle different staff states

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
                await cms_auth.create_staff_session(staff, refresh_token)

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
                    accessToken=temp_token,
                    tokenType="temp",
                    expiresIn=30 * 60,
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


@router.post("/password-setup", response_model=CMSRegistrationStepResponse)
async def password_setup(
    request: CMSPasswordSetupRequest, db: AsyncSession = Depends(get_db)
):
    """
    Step 2: Set password for the staff
    - Validate temporary token
    - Hash and store password
    """
    try:
        # Get staff by email
        result = await db.execute(
            select(Staff).where(Staff.email == request.email.lower())
        )
        staff = result.scalar_one_or_none()

        if not staff or not staff.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid staff or email not verified.",
            )

        # Hash password
        hashed_password = cms_auth.get_password_hash(request.password)

        # Check if this is an invited staff completing password reset
        is_invited_staff = (
            staff.temporary_password and staff.invitation_status == "accepted"
        )

        # Update staff
        staff.hashed_password = hashed_password
        staff.temporary_password = False
        staff.must_reset_password = False
        await db.commit()

        if is_invited_staff:
            # Invited staff - they only need password setup, then they're done
            return CMSRegistrationStepResponse(
                success=True,
                message="Password updated successfully. You can now sign in with your new password.",
                nextStep=None,  # No more steps needed for invited staff
                tempToken=None,
            )
        else:
            # Regular registration flow - continue to personal details
            temp_token = cms_auth.create_temp_token(staff, "registration")
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
    "/personal-details",
    response_model=CMSRegistrationStepResponse,
    dependencies=[Depends(security)],
)
async def personal_details(
    request: CMSPersonalDetailsRequest,
    current_staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Step 3: Set personal details and college information
    - Update staff personal information
    - Create college record with provided details
    """
    try:
        # Update personal details
        current_staff.first_name = request.firstName
        current_staff.last_name = request.lastName
        current_staff.phone_number = request.phoneNumber

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

        # Generate new temp token for next step
        temp_token = cms_auth.create_temp_token(current_staff, "registration")

        return CMSRegistrationStepResponse(
            success=True,
            message="Personal details and college information saved successfully.",
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
    current_staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Step 4: Upload college logo (optional)
    - Handle college logo file upload
    - Can be skipped
    """
    try:
        # Get current staff's college
        result = await db.execute(
            select(College).where(College.id == current_staff.college_id)
        )
        college = result.scalar_one_or_none()

        if not college:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="College not found."
            )

        # Update college logo if provided
        if request.logoFile and not request.skipLogo:
            college.logo_url = request.logoFile
            await db.commit()

        # Generate new temp token for final step
        temp_token = cms_auth.create_temp_token(current_staff, "registration")

        return CMSRegistrationStepResponse(
            success=True,
            message="College logo uploaded successfully."
            if request.logoFile
            else "College logo upload skipped.",
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
    current_staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Step 5: Complete registration with address details
    - Update college address
    - Generate final JWT tokens
    - Create staff session in Redis
    """
    try:
        # Get current staff's college
        result = await db.execute(
            select(College).where(College.id == current_staff.college_id)
        )
        college = result.scalar_one_or_none()

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

        # Complete staff registration
        current_staff.invitation_status = "active"
        current_staff.is_active = True

        await db.commit()

        # Generate JWT tokens
        access_token = cms_auth.create_access_token(current_staff)
        refresh_token = cms_auth.create_refresh_token(current_staff)

        # Create staff session in Redis
        session_created = await cms_auth.create_staff_session(
            current_staff, refresh_token
        )

        if not session_created:
            print("Warning: Failed to create staff session in Redis")

        return CMSTokenResponse(
            accessToken=access_token,
            refreshToken=refresh_token,
            tokenType="bearer",
            expiresIn=cms_auth.access_token_expire_minutes * 60,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error completing registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        )


# Login endpoint removed - now using combined sign-in flow


@router.post("/logout", dependencies=[Depends(security)])
async def logout(current_staff: Staff = Depends(get_current_staff)):
    """
    Logout staff by clearing Redis session
    """
    try:
        success = await cms_auth.logout_staff(current_staff.id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to logout. Please try again.",
            )

        return {"success": True, "message": "Logged out successfully."}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error during logout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        )


@router.get(
    "/me", response_model=StaffProfileResponse, dependencies=[Depends(security)]
)
async def get_current_staff_profile(current_staff: Staff = Depends(get_current_staff)):
    """
    Get current authenticated staff profile
    """
    try:
        staff_dict = current_staff.to_dict()

        return StaffProfileResponse(
            staffId=staff_dict["staffId"],
            uuid=staff_dict["uuid"],
            email=staff_dict["email"],
            firstName=staff_dict["firstName"],
            lastName=staff_dict["lastName"],
            fullName=staff_dict["fullName"],
            phoneNumber=staff_dict["phoneNumber"],
            cmsRole=staff_dict["cmsRole"],
            collegeId=staff_dict["collegeId"],
            departmentId=staff_dict["departmentId"],
            invitationStatus=staff_dict["invitationStatus"],
            mustResetPassword=staff_dict["mustResetPassword"],
            createdAt=staff_dict["createdAt"],
        )

    except Exception as e:
        print(f"Error getting staff profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        )


@router.get(
    "/staff/{staff_id}",
    response_model=StaffProfileResponse,
    dependencies=[Depends(security)],
)
async def get_staff_by_id(
    staff_id: int,
    current_staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get staff by CMS staff ID (authenticated endpoint)
    Only Principal and College Admin can access other staff
    """
    try:
        # Check permissions - only Principal and College Admin can access other staff
        if current_staff.cms_role not in ["principal", "college_admin"]:
            # Staff and HOD can only access their own profile
            if current_staff.id != staff_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to access this staff",
                )

        # Get staff from database
        result = await db.execute(select(Staff).where(Staff.id == staff_id))
        staff = result.scalar_one_or_none()

        if not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found"
            )

        # Check if staff belongs to same college (for Principal/College Admin)
        if current_staff.cms_role in ["principal", "college_admin"]:
            if staff.college_id != current_staff.college_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Staff does not belong to your college",
                )

        staff_dict = staff.to_dict()

        return StaffProfileResponse(
            staffId=staff_dict["staffId"],
            uuid=staff_dict["uuid"],
            email=staff_dict["email"],
            firstName=staff_dict["firstName"],
            lastName=staff_dict["lastName"],
            fullName=staff_dict["fullName"],
            phoneNumber=staff_dict["phoneNumber"],
            cmsRole=staff_dict["cmsRole"],
            collegeId=staff_dict["collegeId"],
            departmentId=staff_dict["departmentId"],
            invitationStatus=staff_dict["invitationStatus"],
            mustResetPassword=staff_dict["mustResetPassword"],
            createdAt=staff_dict["createdAt"],
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting staff by ID: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        )


# =====================================
# USER INVITATION & MANAGEMENT ENDPOINTS
# =====================================


@router.post(
    "/invite-staff", response_model=InviteStaffResponse, dependencies=[Depends(security)]
)
async def invite_staff(
    request: InviteStaffRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Invite a new staff to the college. Only Principal and College Admin can invite staff.

    - Creates staff with temporary password
    - Sends invitation email with credentials
    - Staff status: invitation_status='pending'
    """
    try:
        # Check permissions - only Principal and College Admin can invite staff
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can invite staff",
            )

        # Check if staff already exists
        result = await db.execute(select(Staff).where(Staff.email == request.email))
        existing_staff = result.scalar_one_or_none()

        if existing_staff:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Staff with this email already exists",
            )

        # Generate temporary password
        temporary_password = generate_temporary_password(12)
        hashed_password = cms_auth.hash_password(temporary_password)

        # Create new staff with invitation fields
        new_staff = Staff(
            email=request.email,
            first_name="",  # Will be filled during onboarding
            last_name="",  # Will be filled during onboarding
            hashed_password=hashed_password,
            is_active=True,
            is_verified=False,  # Will be verified during first login
            college_id=current_staff.college_id,
            cms_role="staff",  # Default role, can be changed later
            invitation_status="pending",
            temporary_password=True,
            must_reset_password=True,
            invited_by_staff_id=current_staff.id,
        )

        db.add(new_staff)
        await db.flush()  # Get the ID without committing

        # Get college information for email
        college_result = await db.execute(
            select(College).where(College.id == current_staff.college_id)
        )
        college = college_result.scalar_one()

        # Send invitation email
        try:
            await EmailService.send_staff_invitation_email(
                email=request.email,
                temporary_password=temporary_password,
                inviter_name=current_staff.full_name,
                college_name=college.name,
            )
        except Exception as email_error:
            # Rollback staff creation if email fails
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send invitation email: {str(email_error)}",
            )

        await db.commit()
        await db.refresh(new_staff)

        return InviteStaffResponse(
            success=True,
            message="Staff invitation sent successfully",
            staffId=new_staff.id,
            email=request.email,
            temporaryPassword=temporary_password,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error inviting staff: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while inviting staff",
        )


@router.get(
    "/staff", response_model=Page[StaffResponse], dependencies=[Depends(security)]
)
async def get_staff(
    status: Optional[str] = Query(
        None, description="Filter by approval status: 'approved' or 'unapproved'"
    ),
    department_assigned: Optional[bool] = Query(
        None, description="Filter by department assignment"
    ),
    department_id: Optional[int] = Query(
        None, description="Filter by specific department ID"
    ),
    role: Optional[str] = Query(None, description="Filter by CMS role"),
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Get paginated list of staff with flexible filtering.

    Query Parameters:
    - status: 'approved' (accepted/active) or 'unapproved' (pending)
    - department_assigned: true (has department) or false (no department)
    - department_id: specific department ID
    - role: CMS role filter
    - page/size: pagination (handled automatically)

    Permissions:
    - Principal/College Admin: Can see all staff in college
    - HOD: Can see staff in their department
    - Staff: Cannot access this endpoint
    """
    try:
        # Check permissions
        if current_staff.cms_role not in ["principal", "college_admin", "hod"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view staff",
            )

        # Build base query - scope to current staff's college
        query = select(Staff).where(Staff.college_id == current_staff.college_id)

        # Apply role-based filtering
        if current_staff.cms_role == "hod":
            # HOD can only see staff in their department
            query = query.where(Staff.department_id == current_staff.department_id)

        # Apply status filter
        if status == "approved":
            query = query.where(Staff.invitation_status.in_(["accepted", "active"]))
        elif status == "unapproved":
            query = query.where(Staff.invitation_status == "pending")

        # Apply department assignment filter
        if department_assigned is True:
            query = query.where(Staff.department_id.isnot(None))
        elif department_assigned is False:
            query = query.where(Staff.department_id.is_(None))

        # Apply specific department filter
        if department_id is not None:
            query = query.where(Staff.department_id == department_id)

        # Apply role filter
        if role:
            query = query.where(Staff.cms_role == role)

        # Order by creation date (newest first)
        query = query.order_by(Staff.created_at.desc())

        # Use SQLAlchemy pagination for efficient database queries
        paginated_result = await sqlalchemy_paginate(db, query)

        # Convert staff to response format
        staff_responses = []
        for staff in paginated_result.items:
            staff_dict = staff.to_dict()
            staff_responses.append(StaffResponse(**staff_dict))

        # Return paginated response
        return Page(
            items=staff_responses,
            total=paginated_result.total,
            page=paginated_result.page,
            size=paginated_result.size,
            pages=paginated_result.pages,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting staff: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching staff",
        )


@router.put(
    "/staff/{staff_id}/assign-department",
    response_model=StaffActionResponse,
    dependencies=[Depends(security)],
)
async def assign_staff_to_department(
    staff_id: int,
    request: AssignDepartmentRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Assign a staff to a department. Only Principal and College Admin can assign departments.
    """
    try:
        # Check permissions
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can assign departments",
            )

        # Get staff
        result = await db.execute(
            select(Staff).where(
                and_(Staff.id == staff_id, Staff.college_id == current_staff.college_id)
            )
        )
        staff = result.scalar_one_or_none()

        if not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found"
            )

        # Validate department exists and belongs to same college
        dept_result = await db.execute(
            select(Department).where(
                and_(
                    Department.id == request.departmentId,
                    Department.college_id == current_staff.college_id,
                )
            )
        )
        department = dept_result.scalar_one_or_none()

        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Department not found"
            )

        # Update staff's department
        staff.department_id = request.departmentId
        await db.commit()

        return StaffActionResponse(
            success=True,
            message=f"Staff assigned to {department.name} department successfully",
            staffId=staff_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error assigning staff to department: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while assigning department",
        )


@router.put(
    "/staff/{staff_id}/remove-department",
    response_model=StaffActionResponse,
    dependencies=[Depends(security)],
)
async def remove_staff_from_department(
    staff_id: int,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Remove a staff from their current department. Only Principal and College Admin can do this.
    """
    try:
        # Check permissions
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can remove department assignments",
            )

        # Get staff
        result = await db.execute(
            select(Staff).where(
                and_(Staff.id == staff_id, Staff.college_id == current_staff.college_id)
            )
        )
        staff = result.scalar_one_or_none()

        if not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found"
            )

        # Remove department assignment
        staff.department_id = None
        await db.commit()

        return StaffActionResponse(
            success=True,
            message="Staff removed from department successfully",
            staffId=staff_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error removing staff from department: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while removing department assignment",
        )


@router.put(
    "/staff/{staff_id}/role",
    response_model=StaffActionResponse,
    dependencies=[Depends(security)],
)
async def update_staff_role(
    staff_id: int,
    request: UpdateStaffRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Update a staff's CMS role. Only Principal and College Admin can update roles.
    """
    try:
        # Check permissions
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can update staff roles",
            )

        # Get staff
        result = await db.execute(
            select(Staff).where(
                and_(Staff.id == staff_id, Staff.college_id == current_staff.college_id)
            )
        )
        staff = result.scalar_one_or_none()

        if not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found"
            )

        # Prevent changing principal role (only one principal per college)
        if staff.cms_role == "principal" and request.role != "principal":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change principal role. Transfer principal role first.",
            )

        # Prevent multiple principals
        if request.role == "principal" and staff.cms_role != "principal":
            principal_result = await db.execute(
                select(Staff).where(
                    and_(
                        Staff.college_id == current_staff.college_id,
                        Staff.cms_role == "principal",
                    )
                )
            )
            existing_principal = principal_result.scalar_one_or_none()
            if existing_principal:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="College already has a principal. Transfer role from existing principal first.",
                )

        # Update role
        old_role = staff.cms_role
        staff.cms_role = request.role
        await db.commit()

        return StaffActionResponse(
            success=True,
            message=f"Staff role updated from {old_role} to {request.role}",
            staffId=staff_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error updating staff role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating staff role",
        )


@router.delete(
    "/staff/{staff_id}",
    response_model=StaffActionResponse,
    dependencies=[Depends(security)],
)
async def delete_staff(
    staff_id: int,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Delete a staff. Only Principal and College Admin can delete staff.
    Cannot delete the principal or yourself.
    """
    try:
        # Check permissions
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can delete staff",
            )

        # Prevent self-deletion
        if staff_id == current_staff.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account",
            )

        # Get staff
        result = await db.execute(
            select(Staff).where(
                and_(Staff.id == staff_id, Staff.college_id == current_staff.college_id)
            )
        )
        staff = result.scalar_one_or_none()

        if not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found"
            )

        # Prevent deleting principal
        if staff.cms_role == "principal":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete principal account",
            )

        # Delete staff
        await db.delete(staff)
        await db.commit()

        return StaffActionResponse(
            success=True, message="Staff deleted successfully", staffId=staff_id
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error deleting staff: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting staff",
        )


# =====================================
# DEPARTMENT MANAGEMENT ENDPOINTS
# =====================================


@router.get(
    "/departments",
    response_model=Page[DepartmentWithStatsResponse],
    dependencies=[Depends(security)],
)
async def get_departments(
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Get paginated list of departments with staff statistics.
    All authenticated staff can view departments in their college.
    """
    try:
        # Build query for departments in current staff's college
        query = select(Department).where(
            Department.college_id == current_staff.college_id
        )
        query = query.order_by(Department.name)

        # Get paginated departments
        paginated_result = await sqlalchemy_paginate(db, query)

        # Add staff statistics for each department
        department_responses = []
        for department in paginated_result.items:
            # Count total staff in department
            total_staff_result = await db.execute(
                select(func.count(Staff.id)).where(Staff.department_id == department.id)
            )
            total_staff = total_staff_result.scalar() or 0

            # Count active staff in department
            active_staff_result = await db.execute(
                select(func.count(Staff.id)).where(
                    and_(Staff.department_id == department.id, Staff.is_active)
                )
            )
            active_staff = active_staff_result.scalar() or 0

            dept_dict = department.to_dict()
            department_responses.append(
                DepartmentWithStatsResponse(
                    **dept_dict, totalStaffs=total_staff, activeStaffs=active_staff
                )
            )

        return Page(
            items=department_responses,
            total=paginated_result.total,
            page=paginated_result.page,
            size=paginated_result.size,
            pages=paginated_result.pages,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting departments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching departments",
        )


@router.post(
    "/departments",
    response_model=DepartmentActionResponse,
    dependencies=[Depends(security)],
)
async def create_department(
    request: CreateDepartmentRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Create a new department. Only Principal and College Admin can create departments.
    """
    try:
        # Check permissions
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can create departments",
            )

        # Check if department with same code already exists in college
        existing_dept_result = await db.execute(
            select(Department).where(
                and_(
                    Department.code == request.code,
                    Department.college_id == current_staff.college_id,
                )
            )
        )
        existing_dept = existing_dept_result.scalar_one_or_none()

        if existing_dept:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Department with code '{request.code}' already exists",
            )

        # Create new department
        new_department = Department(
            name=request.name,
            code=request.code,
            description=request.description,
            college_id=current_staff.college_id,
        )

        db.add(new_department)
        await db.commit()
        await db.refresh(new_department)

        return DepartmentActionResponse(
            success=True,
            message=f"Department '{request.name}' created successfully",
            departmentId=new_department.id,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error creating department: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating department",
        )


@router.put(
    "/departments/{department_id}",
    response_model=DepartmentActionResponse,
    dependencies=[Depends(security)],
)
async def update_department(
    department_id: int,
    request: UpdateDepartmentRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Update a department. Only Principal and College Admin can update departments.
    """
    try:
        # Check permissions
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can update departments",
            )

        # Get department
        result = await db.execute(
            select(Department).where(
                and_(
                    Department.id == department_id,
                    Department.college_id == current_staff.college_id,
                )
            )
        )
        department = result.scalar_one_or_none()

        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Department not found"
            )

        # Check if new code conflicts with existing department
        if request.code and request.code != department.code:
            existing_dept_result = await db.execute(
                select(Department).where(
                    and_(
                        Department.code == request.code,
                        Department.college_id == current_staff.college_id,
                        Department.id != department_id,
                    )
                )
            )
            existing_dept = existing_dept_result.scalar_one_or_none()

            if existing_dept:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Department with code '{request.code}' already exists",
                )

        # Validate HOD if provided
        if request.hodCmsStaffId is not None:
            hod_result = await db.execute(
                select(Staff).where(
                    and_(
                        Staff.id == request.hodCmsStaffId,
                        Staff.college_id == current_staff.college_id,
                        Staff.is_active,
                    )
                )
            )
            hod_staff = hod_result.scalar_one_or_none()

            if not hod_staff:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="HOD staff not found or inactive",
                )

        # Update department fields
        if request.name is not None:
            department.name = request.name
        if request.code is not None:
            department.code = request.code
        if request.description is not None:
            department.description = request.description
        if request.hodCmsStaffId is not None:
            department.hod_staff_id = request.hodCmsStaffId

        await db.commit()

        return DepartmentActionResponse(
            success=True,
            message=f"Department '{department.name}' updated successfully",
            departmentId=department_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error updating department: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating department",
        )


@router.delete(
    "/departments/{department_id}",
    response_model=DepartmentActionResponse,
    dependencies=[Depends(security)],
)
async def delete_department(
    department_id: int,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Delete a department. Only Principal and College Admin can delete departments.
    Cannot delete department if it has assigned staff.
    """
    try:
        # Check permissions
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can delete departments",
            )

        # Get department
        result = await db.execute(
            select(Department).where(
                and_(
                    Department.id == department_id,
                    Department.college_id == current_staff.college_id,
                )
            )
        )
        department = result.scalar_one_or_none()

        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Department not found"
            )

        # Check if department has assigned staff
        staff_result = await db.execute(
            select(func.count(Staff.id)).where(Staff.department_id == department_id)
        )
        staff_count = staff_result.scalar() or 0

        if staff_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete department. {staff_count} staff are assigned to this department. Remove staff first.",
            )

        # Delete department
        department_name = department.name
        await db.delete(department)
        await db.commit()

        return DepartmentActionResponse(
            success=True,
            message=f"Department '{department_name}' deleted successfully",
            departmentId=department_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error deleting department: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting department",
        )
