import logging
import time
from datetime import timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_admin_user, get_current_user, get_principal_user
from app.core.auth_manager import auth_manager
from app.core.security import (
    generate_temp_password,
    generate_user_id,
    get_password_hash,
    send_email_otp,
    verify_otp,
    verify_password,
)
from app.db.database import get_db
from app.models.cms.models import CMSUser
from app.schemas.cms.auth import (
    ChangePasswordRequest,
    CMSUserCreate,
    CMSUserCreateResponse,
    CMSUserResponse,
    CMSUserUpdate,
    EmailResponse,
    FetchCMSUserResponse,
    LoginRequest,
    SendEmailRequest,
    Token,
    VerifyEmailRequest,
    VerifyResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/send-email", response_model=EmailResponse)
async def send_email(request: SendEmailRequest, db: Session = Depends(get_db)):
    """
    Send OTP to email for verification

    **Request Body:**
    - email (string, required): Email address of the user

    **Parameters:** None

    **Headers:**
    - Content-Type: application/json

    **Example Request:**
    ```json
    {
        "email": "admin@rajivgandhi.edu"
    }
    ```

    **Example Response:**
    ```json
    {
        "message": "Mock OTP sent successfully. OTP: 123456",
        "success": true
    }
    ```

    **Status Codes:**
    - 200: OTP sent successfully
    - 404: CMSUser not found
    - 422: Validation error
    """
    user = db.query(CMSUser).filter(CMSUser.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="CMSUser not found")

    # Send real OTP via email
    try:
        otp = send_email_otp(request.email, user.college.name if user.college else None)
        return EmailResponse(
            message="OTP sent successfully to your email address", success=True
        )
    except HTTPException:
        # Re-raise HTTP exceptions (like email sending failures)
        raise
    except Exception as e:
        logger.error(f"Unexpected error sending OTP to {request.email}: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to send OTP. Please try again."
        )


@router.post("/verify-email", response_model=VerifyResponse)
async def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    """
    Verify email using OTP

    **Request Body:**
    - email (string, required): Email address to verify
    - otp (integer, required): 6-digit OTP received via email

    **Parameters:** None

    **Headers:**
    - Content-Type: application/json

    **Example Request:**
    ```json
    {
        "email": "admin@rajivgandhi.edu",
        "otp": 123456
    }
    ```

    **Example Response:**
    ```json
    {
        "message": "Email verified successfully",
        "success": true,
        "verified": true
    }
    ```

    **Status Codes:**
    - 200: Email verified successfully
    - 400: Invalid OTP
    - 404: CMSUser not found
    - 422: Validation error
    """
    user = db.query(CMSUser).filter(CMSUser.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="CMSUser not found")

    if not verify_otp(request.email, str(request.otp)):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    # Mark email as verified
    user.email_verified = True
    db.commit()

    return VerifyResponse(
        message="Email verified successfully", success=True, verified=True
    )


@router.post("/signup", response_model=CMSUserCreateResponse)
async def signup(user_data: CMSUserCreate, db: Session = Depends(get_db)):
    """
    Create a new CMS user account

    **Request Body:**
    - email (string, required): CMSUser's email address
    - password (string, optional): CMSUser password (if not provided, temp password generated)
    - fullName (string, optional): Full name of the user
    - phone (string, optional): Phone number with country code
    - collegeName (string, optional): Name of the college
    - role (string, optional): CMSUser role (default: "student")
    - status (string, optional): Account status (default: "active")
    - parentId (string, optional): Parent user ID for hierarchical access
    - modelAccess (array, optional): List of accessible modules
    - logo (array, optional): College logo information
    - collegeDetails (array, optional): College details like establishment year
    - affilliatedUnversity (array, optional): University affiliation details
    - address (array, optional): College address information
    - resultFormat (array, optional): Academic result format configuration

    **Parameters:** None

    **Headers:**
    - Content-Type: application/json

    **Example Request:**
    ```json
    {
        "email": "admin@rajivgandhi.edu",
        "password": "SecurePass123!",
        "fullName": "Dr. John Smith",
        "phone": "+91-9876543210",
        "collegeName": "Rajiv Gandhi Institute of Technology",
        "role": "admin",
        "status": "active",
        "parentId": null,
        "modelAccess": ["students", "placements", "reports"],
        "logo": [
            {
                "url": "https://example.com/logo.png",
                "alt": "College Logo"
            }
        ],
        "collegeDetails": [
            {
                "established": "1998",
                "type": "Engineering",
                "accreditation": "NAAC A+"
            }
        ],
        "affilliatedUnversity": [
            {
                "name": "Anna University",
                "code": "AU001"
            }
        ],
        "address": [
            {
                "street": "123 College Road",
                "city": "Chennai",
                "state": "Tamil Nadu",
                "pincode": "600001",
                "country": "India"
            }
        ],
        "resultFormat": [
            {
                "type": "percentage",
                "scale": "0-100"
            }
        ]
    }
    ```

    **Example Response:**
    ```json
    {
        "message": "CMSUser created successfully",
        "cmsCMSUserId": "usr_abc123xyz",
        "userName": "admin@rajivgandhi.edu",
        "temparyPassword": "Password set by user"
    }
    ```

    **Status Codes:**
    - 200: CMSUser created successfully
    - 400: Email already registered
    - 422: Validation error
    """
    # Check if user already exists
    existing_user = db.query(CMSUser).filter(CMSUser.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Generate user ID and temporary password
    user_id = generate_user_id()
    temp_password = generate_temp_password()

    # Create new user
    db_user = CMSUser(
        id=user_id,
        email=user_data.email,
        username=user_data.email,  # Use email as username initially
        hashed_password=get_password_hash(user_data.password or temp_password),
        full_name=user_data.fullName,
        phone=user_data.phone,
        college_name=user_data.collegeName,
        role=user_data.role or "student",
        status=user_data.status or "active",
        parent_id=user_data.parentId,
        model_access=user_data.modelAccess,
        logo=user_data.logo,
        college_details=user_data.collegeDetails,
        affiliated_university=user_data.affilliatedUnversity,
        address=user_data.address,
        result_format=user_data.resultFormat,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return CMSUserCreateResponse(
        message="CMSUser created successfully",
        cmsCMSUserId=user_id,
        userName=user_data.email,
        temparyPassword=temp_password
        if not user_data.password
        else "Password set by user",
    )


@router.post("/login", response_model=Token)
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """
    Login to CMS system

    **Request Body:**
    - userName (string, required): CMSUsername or email address
    - Password (string, required): CMSUser password

    **Parameters:** None

    **Headers:**
    - Content-Type: application/json

    **Example Request:**
    ```json
    {
        "userName": "admin@rajivgandhi.edu",
        "Password": "SecurePass123!"
    }
    ```

    **Example Response:**
    ```json
    {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer",
        "cmsCMSUserId": "usr_abc123xyz",
        "role": "admin"
    }
    ```

    **Status Codes:**
    - 200: Login successful
    - 400: Inactive user
    - 401: Incorrect username or password
    - 422: Validation error

    **Token Usage:**
    Include the access_token in subsequent requests:
    ```
    Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    ```
    """
    logger = logging.getLogger(__name__)

    # Authenticate user with enhanced auth manager
    user = auth_manager.authenticate_user(
        credentials.userName, credentials.Password, db
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create enhanced access token with Redis caching
    user_data = {
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role,
        "college_id": str(user.college_id),
        "username": user.username,
    }

    token_response = auth_manager.create_access_token(user_data)

    logger.info(f"User {user.username} logged in successfully")

    return Token(
        access_token=token_response["access_token"],
        token_type=token_response["token_type"],
        cmsUserId=str(user.id),
        role=user.role,
    )


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Change user password (requires authentication)

    **Request Body:**
    - email (string, required): Email address of the user
    - oldPassword (string, required): Current password
    - newPassword (string, required): New password

    **Parameters:** None

    **Headers:**
    - Content-Type: application/json
    - Authorization: Bearer {access_token}

    **Example Request:**
    ```json
    {
        "email": "admin@rajivgandhi.edu",
        "oldPassword": "OldPass123!",
        "newPassword": "NewSecurePass456!"
    }
    ```

    **Example Response:**
    ```json
    {
        "message": "Password changed successfully"
    }
    ```

    **Status Codes:**
    - 200: Password changed successfully
    - 400: Invalid current password
    - 401: Unauthorized (invalid token)
    - 404: CMSUser not found
    - 422: Validation error
    """
    # Find user by email
    user = db.query(CMSUser).filter(CMSUser.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="CMSUser not found")

    # Verify current password
    if not verify_password(request.oldPassword, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid current password")

    # Update password
    user.hashed_password = get_password_hash(request.newPassword)
    db.commit()

    return {"message": "Password changed successfully"}


@router.get("/users/{user_id}", response_model=CMSUserResponse)
async def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = db.query(CMSUser).filter(CMSUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="CMSUser not found")
    return user


@router.put("/users/{user_id}", response_model=CMSUserResponse)
async def update_user(
    user_id: str,
    user_data: CMSUserUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = db.query(CMSUser).filter(CMSUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="CMSUser not found")

    for field, value in user_data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = db.query(CMSUser).filter(CMSUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="CMSUser not found")

    db.delete(user)
    db.commit()


@router.get("/fetch-users", response_model=List[FetchCMSUserResponse])
async def fetch_users(
    user_id: str,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if page_size > 100:
        page_size = 100

    offset = (page - 1) * page_size
    users = db.query(CMSUser).offset(offset).limit(page_size).all()
    return users


@router.delete("/admin/{admin_id}")
async def revoke_admin_access(
    admin_id: str,
    reason: str = "admin_revoked",
    db: Session = Depends(get_db),
    current_user: CMSUser = Depends(get_principal_user),
):
    # Verify admin user exists
    admin_user = db.query(CMSUser).filter(CMSUser.id == admin_id).first()
    if not admin_user:
        raise HTTPException(status_code=404, detail="Admin user not found")

    # Only allow revoking admin roles
    if admin_user.role not in ["admin", "head", "staff"]:
        raise HTTPException(
            status_code=400, detail="Can only revoke admin/head/staff access"
        )

    # Immediately revoke access using Redis blacklist
    success = auth_manager.revoke_user_access(admin_id, reason)

    if not success:
        raise HTTPException(
            status_code=500, detail="Failed to revoke access - Redis unavailable"
        )

    # Optionally deactivate user in database
    admin_user.is_active = False
    db.commit()

    logger.info(f"Principal {current_user.id} revoked access for admin {admin_id}")

    return {
        "message": "Admin access revoked immediately",
        "user_id": admin_id,
        "revoked_at": int(time.time()),
        "reason": reason,
    }


@router.post("/admin/{admin_id}/restore")
async def restore_admin_access(
    admin_id: str,
    db: Session = Depends(get_db),
    current_user: CMSUser = Depends(get_principal_user),
):
    # Verify admin user exists
    admin_user = db.query(CMSUser).filter(CMSUser.id == admin_id).first()
    if not admin_user:
        raise HTTPException(status_code=404, detail="Admin user not found")

    # Restore access using Redis
    success = auth_manager.restore_user_access(admin_id)

    if not success:
        raise HTTPException(
            status_code=500, detail="Failed to restore access - Redis unavailable"
        )

    # Reactivate user in database
    admin_user.is_active = True
    db.commit()

    logger.info(f"Principal {current_user.id} restored access for admin {admin_id}")

    return {
        "message": "Admin access restored",
        "user_id": admin_id,
        "restored_at": int(time.time()),
    }


@router.get("/auth/status")
async def get_auth_status(current_user: CMSUser = Depends(get_current_user)):
    # Get detailed authentication status
    auth_status = auth_manager.get_authentication_status(str(current_user.id))

    return {
        "user_id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "college_id": str(current_user.college_id),
        "is_active": current_user.is_active,
        "last_login": current_user.last_login,
        "token_valid": True,
        **auth_status,
    }


@router.post("/logout")
async def logout(token: str = None, current_user: CMSUser = Depends(get_current_user)):
    # Get token from authorization header if not provided
    if not token:
        # This would need to be extracted from the request context
        # For now, we'll just invalidate the user cache
        pass

    # Invalidate user cache
    auth_manager.redis.invalidate_user_cache(str(current_user.id))

    logger.info(f"User {current_user.username} logged out")

    return {"message": "Logged out successfully", "user_id": str(current_user.id)}


@router.get("/cache/stats")
async def get_cache_stats(current_user: CMSUser = Depends(get_principal_user)):
    cache_stats = auth_manager.redis.get_cache_stats()
    cache_stats["cache_available"] = auth_manager.redis.is_available()

    return cache_stats
