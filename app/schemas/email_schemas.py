from pydantic import EmailStr, Field
from typing import Optional
from app.core.utils import CamelCaseModel


# Email OTP Schemas - exactly matching your existing code structure


class SendEmailRequest(CamelCaseModel):
    """Request schema for sending email OTP - matches your existing code"""

    email: EmailStr = Field(..., description="Email address to send OTP to")


class EmailResponse(CamelCaseModel):
    """Response schema for email operations - matches your existing code"""

    message: str = Field(..., description="Response message")
    success: bool = Field(..., description="Operation success status")


class VerifyEmailOTPRequest(CamelCaseModel):
    """Request schema for verifying email OTP"""

    email: EmailStr = Field(..., description="Email address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")


class VerifyEmailOTPResponse(CamelCaseModel):
    """Response schema for OTP verification"""

    message: str = Field(..., description="Response message")
    success: bool = Field(..., description="Verification success status")
    email_verified: bool = Field(
        default=False, description="Whether email is now verified"
    )


# Email configuration and status schemas


class EmailConfigResponse(CamelCaseModel):
    """Response schema for email configuration status"""

    aws_ses_configured: bool = Field(..., description="Whether AWS SES is configured")
    gmail_configured: bool = Field(..., description="Whether Gmail is configured")
    primary_provider: str = Field(..., description="Primary email provider")
    fallback_available: bool = Field(..., description="Whether fallback is available")


class EmailHealthResponse(CamelCaseModel):
    """Response schema for email service health check"""

    status: str = Field(..., description="Overall email service status")
    providers: dict = Field(..., description="Status of each email provider")
    last_check: str = Field(..., description="Timestamp of last health check")


# General email template schemas


class EmailTemplate(CamelCaseModel):
    """Base email template schema"""

    subject: str = Field(..., description="Email subject")
    body_text: str = Field(..., description="Plain text email body")
    body_html: Optional[str] = Field(None, description="HTML email body")
    from_email: Optional[str] = Field(None, description="From email address")


class SendCustomEmailRequest(CamelCaseModel):
    """Request schema for sending custom emails"""

    to_email: EmailStr = Field(..., description="Recipient email address")
    template: EmailTemplate = Field(..., description="Email template")


class SendCustomEmailResponse(CamelCaseModel):
    """Response schema for custom email sending"""

    message: str = Field(..., description="Response message")
    success: bool = Field(..., description="Send success status")
    message_id: Optional[str] = Field(None, description="Email provider message ID")
    provider: str = Field(..., description="Email provider used")
