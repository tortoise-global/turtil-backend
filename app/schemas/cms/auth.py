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


from app.schemas.cms.users import CMSUserCreate, CMSUserUpdate, CMSUserResponse

CMSUserCreate = CMSUserCreate
CMSUserUpdate = CMSUserUpdate  
CMSUserResponse = CMSUserResponse

class CMSUserCreateResponse(BaseModel):
    message: str
    cmsUserId: str
    userName: str
    temparyPassword: str


class FetchCMSUserResponse(CMSUserResponse):
    pass