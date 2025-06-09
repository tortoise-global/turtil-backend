from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import timedelta

from app.core.auth import get_current_user
from app.core.security import (
    verify_password, get_password_hash, create_access_token, 
    generate_temp_password, generate_user_id, verify_otp
)
from app.db.database import get_db
from app.models.models import User
from app.schemas.auth import (
    SendEmailRequest, VerifyEmailRequest, LoginRequest, ChangePasswordRequest,
    Token, EmailResponse, VerifyResponse, UserCreate, UserUpdate, 
    UserResponse, UserCreateResponse, FetchUserResponse
)

router = APIRouter()


@router.post("/send-email", response_model=EmailResponse)
async def send_email(request: SendEmailRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # In a real implementation, you would send an actual email here
    # For now, we just return success since OTP is stored in env
    return EmailResponse(message="OTP sent successfully", success=True)


@router.post("/verify-email", response_model=VerifyResponse)
async def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not verify_otp(str(request.otp)):
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    # Mark email as verified
    user.is_email_verified = True
    db.commit()
    
    return VerifyResponse(message="Email verified successfully", success=True, verified=True)


@router.post("/signup", response_model=UserCreateResponse)
async def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Generate user ID and temporary password
    user_id = generate_user_id()
    temp_password = generate_temp_password()
    
    # Create new user
    db_user = User(
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
        result_format=user_data.resultFormat
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return UserCreateResponse(
        message="User created successfully",
        cmsUserId=user_id,
        userName=user_data.email,
        temparyPassword=temp_password if not user_data.password else "Password set by user"
    )


@router.post("/login", response_model=Token)
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    # Find user by username or email
    user = db.query(User).filter(
        (User.username == credentials.userName) | 
        (User.email == credentials.userName)
    ).first()
    
    if not user or not verify_password(credentials.Password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # Create access token
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        cmsUserId=user.id,
        role=user.role or "student"
    )


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify current password
    if not verify_password(request.oldPassword, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid current password")
    
    # Update password
    user.hashed_password = get_password_hash(request.newPassword)
    db.commit()
    
    return {"message": "Password changed successfully"}


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    for field, value in user_data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()


@router.get("/fetch-users", response_model=List[FetchUserResponse])
async def fetch_users(
    user_id: str,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if page_size > 100:
        page_size = 100
    
    offset = (page - 1) * page_size
    users = db.query(User).offset(offset).limit(page_size).all()
    return users