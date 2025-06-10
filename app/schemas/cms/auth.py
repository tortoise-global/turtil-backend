from pydantic import BaseModel, EmailStr
from typing import Optional, List


class SendEmailRequest(BaseModel):
    email: EmailStr


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    otp: int


class LoginRequest(BaseModel):
    userName: str
    Password: str


class ChangePasswordRequest(BaseModel):
    email: str
    oldPassword: str
    newPassword: str


class Token(BaseModel):
    access_token: str
    token_type: str
    cmsUserId: str
    role: str


class EmailResponse(BaseModel):
    message: str
    success: bool


class VerifyResponse(BaseModel):
    message: str
    success: bool
    verified: bool


class UserCreate(BaseModel):
    email: str
    password: Optional[str] = None
    fullName: Optional[str] = None
    phone: Optional[str] = None
    collegeName: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    parentId: Optional[str] = None
    modelAccess: Optional[List] = []
    logo: Optional[List] = []
    collegeDetails: Optional[List] = []
    affilliatedUnversity: Optional[List] = []
    address: Optional[List] = []
    resultFormat: Optional[List] = []


class UserUpdate(BaseModel):
    email: Optional[str] = None
    fullName: Optional[str] = None
    phone: Optional[str] = None
    collegeName: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    parentId: Optional[str] = None
    modelAccess: Optional[List] = []
    logo: Optional[List] = []
    collegeDetails: Optional[List] = []
    affilliatedUnversity: Optional[List] = []
    address: Optional[List] = []
    resultFormat: Optional[List] = []


class UserResponse(BaseModel):
    id: str
    email: str
    username: Optional[str] = None
    is_email_verified: bool = False
    is_active: bool = True
    fullName: Optional[str] = None
    phone: Optional[str] = None
    collegeName: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    parentId: Optional[str] = None
    modelAccess: Optional[List] = []
    logo: Optional[List] = []
    collegeDetails: Optional[List] = []
    affilliatedUnversity: Optional[List] = []
    address: Optional[List] = []
    resultFormat: Optional[List] = []
    created_at: int
    updated_at: Optional[int] = None

    class Config:
        from_attributes = True


class UserCreateResponse(BaseModel):
    message: str
    cmsUserId: str
    userName: str
    temparyPassword: str


class FetchUserResponse(UserResponse):
    pass