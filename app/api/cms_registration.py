from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.database import get_db
from app.models.staff import Staff
from app.models.college import College
from app.core.cms_auth import cms_auth
from app.schemas.cms_auth import (
    CMSPersonalDetailsRequest,
    CMSCollegeDetailsRequest,
    CMSAddressDetailsRequest,
    CMSRegistrationStepResponse,
    CMSTokenResponse,
)

router = APIRouter(prefix="/cms/registration", tags=["CMS Registration Details"])

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


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
        # Validate temp token
        payload = await cms_auth.validate_temp_token(credentials.credentials, "registration")
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired temporary token",
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

        if not staff:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Staff not found",
            )

        return staff

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting current CMS staff from temp token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
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
    Step 1: Set personal details and college information
    - Update staff personal information
    - Create college record with provided details
    """
    try:
        # Update personal details
        current_staff.full_name = request.fullName

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
    current_staff: Staff = Depends(get_current_staff_from_temp_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Step 2: Upload college logo (optional)
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
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="College not found."
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
    current_staff: Staff = Depends(get_current_staff_from_temp_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Step 3: Complete registration with address details
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