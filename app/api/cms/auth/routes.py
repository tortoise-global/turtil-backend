import logging
import time
from datetime import timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_admin_user, get_current_user, get_principal_user
from app.core.auth_manager import auth_manager
from app.core.security import (
    generate_user_id,
    get_password_hash,
    send_email_otp,
    verify_otp,
    verify_password,
)
from app.db.database import get_db
from app.models.cms.models import CMSUser
from app.schemas.cms.auth import (
    AdminActionResponse,
    AuthStatusResponse,
    CacheStatsResponse,
    ChangePasswordRequest,
    CMSUserResponse,
    CMSUserUpdate,
    CompleteProfileRequest,
    CompleteProfileResponse,
    CompleteSignupRequest,
    CompleteSignupResponse,
    EmailResponse,
    FetchCMSUserResponse,
    LoginRequest,
    LogoutResponse,
    SendSignupOTPRequest,
    Token,
    VerifyResponse,
    VerifySignupOTPRequest,
)
from app.schemas.shared.responses import MessageResponse
from app.services.cms.auth_service import auth_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/send-signup-otp", response_model=EmailResponse)
async def send_signup_otp(request: SendSignupOTPRequest, db: Session = Depends(get_db)):
    """
    Send OTP to email for new user signup (no existing user required)

    **Request Body:**
    - email (string, required): Email address for signup

    **Example Request:**
    ```json
    {
        "email": "newuser@example.com"
    }
    ```

    **Example Response:**
    ```json
    {
        "message": "OTP sent successfully to your email address",
        "success": true
    }
    ```

    **Status Codes:**
    - 200: OTP sent successfully
    - 400: Email already registered
    - 422: Validation error
    """
    response = auth_service.send_signup_otp(db, request)
    return EmailResponse(**response)


@router.post("/verify-signup-otp", response_model=VerifyResponse)
async def verify_signup_otp(request: VerifySignupOTPRequest):
    """
    Verify signup OTP (allows password setup if valid)

    **Request Body:**
    - email (string, required): Email address
    - otp (integer, required): 6-digit OTP received via email

    **Example Request:**
    ```json
    {
        "email": "newuser@example.com",
        "otp": 123456
    }
    ```

    **Example Response:**
    ```json
    {
        "message": "OTP verified successfully. You can now set your password.",
        "success": true,
        "verified": true
    }
    ```

    **Status Codes:**
    - 200: OTP verified successfully
    - 400: Invalid or expired OTP
    - 422: Validation error
    """
    response = auth_service.verify_signup_otp(request)
    return VerifyResponse(**response)


@router.post("/complete-signup", response_model=CompleteSignupResponse)
async def complete_signup(
    request: CompleteSignupRequest, db: Session = Depends(get_db)
):
    """
    Complete signup by setting password (creates minimal user record)

    **Request Body:**
    - email (string, required): Email address
    - otp (integer, required): 6-digit OTP for final verification
    - password (string, required): User password

    **Example Request:**
    ```json
    {
        "email": "newuser@example.com",
        "otp": 123456,
        "password": "SecurePass123!"
    }
    ```

    **Example Response:**
    ```json
    {
        "message": "Signup completed successfully. Please login to complete your profile.",
        "success": true,
        "userId": "usr_abc123xyz"
    }
    ```

    **Status Codes:**
    - 200: Signup completed successfully
    - 400: Invalid OTP or email already registered
    - 422: Validation error
    """
    # Verify OTP one final time
    if not verify_otp(request.email, str(request.otp)):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    # Check if user was created in the meantime
    existing_user = db.query(CMSUser).filter(CMSUser.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create minimal user record
    user_id = generate_user_id()
    db_user = CMSUser(
        id=user_id,
        email=request.email,
        password_hash=get_password_hash(request.password),
        email_verified=True,
        profile_completed=False,
        # All other fields remain null
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return CompleteSignupResponse(
        message="Signup completed successfully. Please login to complete your profile.",
        success=True,
        user_id=str(user_id),
    )


@router.post("/login", response_model=Token)
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """
    Login to CMS system

    **Request Body:**
    - userName (string, required): CMSUsername or email address
    - password (string, required): CMSUser password

    **Parameters:** None

    **Headers:**
    - Content-Type: application/json

    **Example Request:**
    ```json
    {
        "userName": "admin@rajivgandhi.edu",
        "password": "SecurePass123!"
    }
    ```

    **Example Response:**
    ```json
    {
        "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "tokenType": "bearer",
        "cmsUserId": "usr_abc123xyz",
        "role": "admin",
        "profileCompleted": false
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
    # Authenticate user with enhanced auth manager
    user = auth_manager.authenticate_user(
        credentials.userName, credentials.password, db
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
        cms_user_id=str(user.id),
        role=user.role,
        profile_completed=user.profile_completed or False,
    )


@router.post("/change-password", response_model=MessageResponse)
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

    return MessageResponse(message="Password changed successfully")


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


@router.delete("/admin/{admin_id}", response_model=AdminActionResponse)
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

    return AdminActionResponse(
        message="Admin access revoked immediately",
        user_id=admin_id,
        revoked_at=int(time.time()),
        reason=reason,
    )


@router.post("/admin/{admin_id}/restore", response_model=AdminActionResponse)
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

    return AdminActionResponse(
        message="Admin access restored",
        user_id=admin_id,
        restored_at=int(time.time()),
    )


@router.get("/auth/status", response_model=AuthStatusResponse)
async def get_auth_status(current_user: CMSUser = Depends(get_current_user)):
    # Get detailed authentication status
    auth_status = auth_manager.get_authentication_status(str(current_user.id))

    return AuthStatusResponse(
        user_id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        college_id=str(current_user.college_id),
        is_active=current_user.is_active,
        last_login=current_user.last_login,
        token_valid=True,
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(token: str = None, current_user: CMSUser = Depends(get_current_user)):
    # Get token from authorization header if not provided
    if not token:
        # This would need to be extracted from the request context
        # For now, we'll just invalidate the user cache
        pass

    # Invalidate user cache
    auth_manager.redis.invalidate_user_cache(str(current_user.id))

    logger.info(f"User {current_user.username} logged out")

    return LogoutResponse(
        message="Logged out successfully", user_id=str(current_user.id)
    )


@router.post("/complete-profile", response_model=CompleteProfileResponse)
async def complete_profile(
    profile_data: CompleteProfileRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Complete user profile after initial signup

    **Request Body:**
    - fullName (string, required): Full name of the user
    - phone (string, optional): Phone number
    - collegeId (string, required): College UUID
    - role (string, optional): User role (default: "student")
    - departmentId (string, optional): Department UUID
    - branchId (string, optional): Branch UUID
    - degreeId (string, optional): Degree UUID

    **Headers:**
    - Authorization: Bearer {access_token}

    **Example Request:**
    ```json
    {
        "fullName": "John Doe",
        "phone": "+91-9876543210",
        "collegeId": "123e4567-e89b-12d3-a456-426614174000",
        "role": "student",
        "departmentId": "123e4567-e89b-12d3-a456-426614174001",
        "branchId": "123e4567-e89b-12d3-a456-426614174002",
        "degreeId": "123e4567-e89b-12d3-a456-426614174003"
    }
    ```

    **Example Response:**
    ```json
    {
        "message": "Profile completed successfully",
        "profileCompleted": true
    }
    ```

    **Status Codes:**
    - 200: Profile completed successfully
    - 400: Profile already completed
    - 401: Unauthorized
    - 404: User not found
    - 422: Validation error
    """
    # Get user from database
    user = db.query(CMSUser).filter(CMSUser.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if profile is already completed
    if user.profile_completed:
        raise HTTPException(status_code=400, detail="Profile already completed")

    # Update user profile
    user.full_name = profile_data.full_name
    user.phone = profile_data.phone
    user.college_id = profile_data.college_id
    user.role = profile_data.role
    user.department_id = profile_data.department_id
    user.branch_id = profile_data.branch_id
    user.degree_id = profile_data.degree_id
    user.username = user.email  # Set username to email
    user.profile_completed = True

    db.commit()
    db.refresh(user)

    return CompleteProfileResponse(
        message="Profile completed successfully", profile_completed=True
    )


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats(current_user: CMSUser = Depends(get_principal_user)):
    cache_stats = auth_manager.redis.get_cache_stats()

    return CacheStatsResponse(
        cache_available=auth_manager.redis.is_available(),
        total_keys=cache_stats.get("total_keys"),
        memory_usage=cache_stats.get("memory_usage"),
        hit_rate=cache_stats.get("hit_rate"),
    )
