from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.database import get_db
from app.models.staff import Staff
from app.models.college import College
from app.core.cms_auth import cms_auth
from app.schemas.registration_schemas import (
    CollegeLogoRequest,
    CollegeDetailsRequest,
    AddressDetailsRequest,
    RegistrationStepResponse,
    TokenResponse,
)
from app.api.cms.deps import get_current_staff_from_temp_token

router = APIRouter(prefix="/registration", tags=["CMS Registration Details"])


@router.post(
    "/college-logo",
    response_model=RegistrationStepResponse,
)
async def college_logo(
    request: CollegeLogoRequest,
    current_staff: Staff = Depends(get_current_staff_from_temp_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Step 1: Upload college logo (optional)
    - Handle college logo file upload from S3 URL
    - Can be skipped
    """
    try:
        # If college doesn't exist yet, create it with minimal info
        # (This handles the case where user starts with logo upload)
        if not current_staff.college_id:
            college = College(
                name="",  # Will be filled in college-details step
                short_name="",  # Will be filled in college-details step
                college_reference_id="",  # Will be filled in college-details step
                area="",  # Will be filled in college-address step
                city="",  # Will be filled in college-address step
                district="",  # Will be filled in college-address step
                state="",  # Will be filled in college-address step
                pincode="000000",  # Will be filled in college-address step
                principal_staff_id=current_staff.staff_id,
            )

            db.add(college)
            await db.commit()
            await db.refresh(college)

            # Update staff with college and role
            current_staff.college_id = college.college_id
            current_staff.cms_role = "principal"
            current_staff.can_assign_department = True
            await db.commit()

        # Get current staff's college
        result = await db.execute(
            select(College).where(College.college_id == current_staff.college_id)
        )
        college = result.scalar_one_or_none()

        if not college:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="College not found."
            )

        # Update college logo if provided
        if request.logoUrl and not request.skipLogo:
            college.logo_url = request.logoUrl
            await db.commit()

        # Generate new temp token for next step
        temp_token = cms_auth.create_temp_token(current_staff, "registration")

        return RegistrationStepResponse(
            success=True,
            message="College logo uploaded successfully."
            if request.logoUrl
            else "College logo upload skipped.",
            nextStep="college_details",
            tempToken=temp_token,
        )

    except HTTPException:
        raise
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "College logo upload", {"staff_id": str(current_staff.staff_id), "logo_url": getattr(request, 'logoUrl', None), "skip_logo": getattr(request, 'skipLogo', False)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post(
    "/college-details",
    response_model=RegistrationStepResponse,
)
async def college_details(
    request: CollegeDetailsRequest,
    current_staff: Staff = Depends(get_current_staff_from_temp_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Step 2: Set college details and information
    - Update college record with provided details
    - Create college if it doesn't exist
    """
    try:
        # Get or create college
        if current_staff.college_id:
            # Get existing college
            result = await db.execute(
                select(College).where(College.college_id == current_staff.college_id)
            )
            college = result.scalar_one_or_none()
            
            if not college:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="College not found."
                )
        else:
            # Create new college if it doesn't exist
            college = College(
                name=request.name,
                short_name=request.shortName,
                college_reference_id=request.collegeReferenceId,
                area="",  # Will be filled in college-address step
                city="",  # Will be filled in college-address step
                district="",  # Will be filled in college-address step
                state="",  # Will be filled in college-address step
                pincode="000000",  # Will be filled in college-address step
                principal_staff_id=current_staff.staff_id,
            )

            db.add(college)
            await db.commit()
            await db.refresh(college)

            # Update staff with college and role
            current_staff.college_id = college.college_id
            current_staff.cms_role = "principal"
            current_staff.can_assign_department = True
            await db.commit()

        # Update college details
        college.name = request.name
        college.short_name = request.shortName
        college.college_reference_id = request.collegeReferenceId
        college.phone_number = request.phoneNumber
        await db.commit()

        # Generate new temp token for next step
        temp_token = cms_auth.create_temp_token(current_staff, "registration")

        return RegistrationStepResponse(
            success=True,
            message="College details saved successfully.",
            nextStep="college_address",
            tempToken=temp_token,
        )

    except HTTPException:
        raise
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "College details setup", {"staff_id": str(current_staff.staff_id), "college_name": request.name, "college_reference_id": request.collegeReferenceId}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post(
    "/college-address",
    response_model=TokenResponse,
)
async def college_address(
    request: AddressDetailsRequest,
    current_staff: Staff = Depends(get_current_staff_from_temp_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Step 3: Complete registration with college address details
    - Update college address
    - Generate final JWT tokens
    - Create staff session in Redis
    """
    try:
        # Get current staff's college
        result = await db.execute(
            select(College).where(College.college_id == current_staff.college_id)
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

        return TokenResponse(
            accessToken=access_token,
            refreshToken=refresh_token,
            tokenType="bearer",
            expiresIn=cms_auth.access_token_expire_minutes * 60,
        )

    except HTTPException:
        raise
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Complete college registration", {"staff_id": str(current_staff.staff_id), "college_id": str(current_staff.college_id) if current_staff.college_id else None}, status.HTTP_500_INTERNAL_SERVER_ERROR)